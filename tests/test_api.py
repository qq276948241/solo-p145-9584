import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import httpx
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:8000"

admin_token = None
collector_token = None
resident_token = None
resident_user_id = None
collector_user_id = None
address_id = None
category_ids = {}
order_id = None
order_item_ids = []


async def test():
    global admin_token, collector_token, resident_token
    global resident_user_id, collector_user_id, address_id, category_ids
    global order_id, order_item_ids

    print("=" * 60)
    print("开始API测试")
    print("=" * 60)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        try:
            await client.get("/health")
            print("✓ 服务运行正常")
        except Exception as e:
            print(f"✗ 服务连接失败: {e}")
            print("请先启动服务: python -m uvicorn app.main:app --reload")
            return

        print("\n--- 1. 用户模块测试 ---")

        response = await client.post("/api/users/register", json={
            "phone": "13900139010",
            "username": "测试住户",
            "password": "123456",
            "role": "resident"
        })
        if response.status_code == 200:
            print("✓ 新用户注册成功")
        elif response.status_code == 400:
            print("✓ 用户已存在，跳过注册")
        else:
            print(f"✗ 注册失败: {response.json()}")

        response = await client.post("/api/users/login", json={
            "phone": "13800138001",
            "password": "admin123"
        })
        assert response.status_code == 200, f"管理员登录失败: {response.json()}"
        admin_token = response.json()["access_token"]
        print("✓ 管理员登录成功")

        response = await client.post("/api/users/login", json={
            "phone": "13800138002",
            "password": "123456"
        })
        assert response.status_code == 200, f"回收员登录失败: {response.json()}"
        collector_token = response.json()["access_token"]
        collector_user_id = response.json()["user"]["id"]
        print("✓ 回收员登录成功")

        response = await client.post("/api/users/login", json={
            "phone": "13900139001",
            "password": "123456"
        })
        assert response.status_code == 200, f"住户登录失败: {response.json()}"
        resident_token = response.json()["access_token"]
        resident_user_id = response.json()["user"]["id"]
        print("✓ 住户登录成功")

        headers = {"Authorization": f"Bearer {resident_token}"}
        response = await client.get("/api/users/me", headers=headers)
        assert response.status_code == 200
        print("✓ 获取当前用户信息成功")

        print("\n--- 2. 地址簿测试 ---")

        response = await client.post("/api/users/addresses", headers=headers, json={
            "name": "王先生",
            "phone": "13900139001",
            "address_detail": "阳光小区1号楼2单元301室",
            "is_default": True
        })
        assert response.status_code == 200, f"添加地址失败: {response.json()}"
        address_id = response.json()["id"]
        print("✓ 添加地址成功")

        response = await client.get("/api/users/addresses", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1
        print("✓ 获取地址列表成功")

        response = await client.put(f"/api/users/addresses/{address_id}", headers=headers, json={
            "address_detail": "阳光小区1号楼2单元301室（东门）"
        })
        assert response.status_code == 200
        print("✓ 更新地址成功")

        print("\n--- 3. 品类模块测试 ---")

        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        response = await client.post("/api/categories", headers=admin_headers, json={
            "name": "废纸",
            "unit_price": 1.0,
            "unit": "kg",
            "description": "各种废纸"
        })
        if response.status_code == 200:
            print("✓ 添加品类成功")
        elif response.status_code == 400:
            print("✓ 品类已存在，跳过添加")
        else:
            print(f"! 添加品类返回: {response.status_code}")

        response = await client.get("/api/categories", headers=headers)
        assert response.status_code == 200
        categories = response.json()
        assert len(categories) >= 6
        for cat in categories:
            category_ids[cat["name"]] = cat["id"]
        print(f"✓ 获取品类列表成功，共 {len(categories)} 个品类")
        for cat in categories[:3]:
            print(f"  - {cat['name']}: {cat['unit_price']}元/{cat['unit']}")

        print("\n--- 4. 订单模块测试 ---")

        appointment_time = (datetime.utcnow() + timedelta(days=1)).isoformat()
        response = await client.post("/api/orders", headers=headers, json={
            "address_id": address_id,
            "appointment_time": appointment_time,
            "remark": "上午9点以后上门",
            "order_items": [
                {"category_id": category_ids["纸壳"], "estimated_weight": 5.0},
                {"category_id": category_ids["塑料"], "estimated_weight": 3.0},
                {"category_id": category_ids["金属"], "estimated_weight": 2.0}
            ]
        })
        assert response.status_code == 200, f"下单失败: {response.json()}"
        order = response.json()
        order_id = order["id"]
        order_item_ids = [item["id"] for item in order["order_items"]]
        estimated_amount = order["estimated_amount"]
        expected_amount = 5 * 1.2 + 3 * 0.8 + 2 * 3.5
        assert abs(estimated_amount - expected_amount) < 0.01
        print(f"✓ 下单成功，订单号: {order['order_no']}")
        print(f"  预估金额: {estimated_amount}元 (纸壳5kg×1.2 + 塑料3kg×0.8 + 金属2kg×3.5 = {expected_amount}元)")

        response = await client.get("/api/orders", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1
        print("✓ 获取订单列表成功")

        response = await client.get(f"/api/orders/{order_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "pending"
        print("✓ 获取订单详情成功，状态: 待接单")

        collector_headers = {"Authorization": f"Bearer {collector_token}"}
        response = await client.put(f"/api/orders/{order_id}/accept", headers=collector_headers)
        assert response.status_code == 200, f"接单失败: {response.json()}"
        assert response.json()["status"] == "accepted"
        assert response.json()["collector_id"] == collector_user_id
        print("✓ 回收员接单成功，状态: 已接单")

        response = await client.put(f"/api/orders/{order_id}/status", headers=collector_headers,
                                    params={"new_status": "collecting"})
        assert response.status_code == 200
        assert response.json()["status"] == "collecting"
        print("✓ 更新订单状态成功，状态: 回收中")

        response = await client.put(f"/api/orders/{order_id}/actual-weight", headers=collector_headers, json=[
            {"order_item_id": order_item_ids[0], "actual_weight": 4.8},
            {"order_item_id": order_item_ids[1], "actual_weight": 3.2},
            {"order_item_id": order_item_ids[2], "actual_weight": 1.9}
        ])
        assert response.status_code == 200, f"录入实际重量失败: {response.json()}"
        final_amount = response.json()["final_amount"]
        expected_final = 4.8 * 1.2 + 3.2 * 0.8 + 1.9 * 3.5
        assert abs(final_amount - expected_final) < 0.01
        print(f"✓ 录入实际重量成功，最终金额: {final_amount}元")
        print(f"  计算: 纸壳4.8kg×1.2 + 塑料3.2kg×0.8 + 金属1.9kg×3.5 = {expected_final}元")

        response = await client.put(f"/api/orders/{order_id}/status", headers=collector_headers,
                                    params={"new_status": "completed"})
        assert response.status_code == 200
        assert response.json()["status"] == "completed"
        print("✓ 订单完成，状态: 已完成")

        print("\n--- 5. 评价模块测试 ---")

        response = await client.post("/api/reviews", headers=headers, json={
            "order_id": order_id,
            "rating": 5,
            "comment": "回收员服务很好，称重准确，价格公道！"
        })
        assert response.status_code == 200, f"发表评价失败: {response.json()}"
        review_id = response.json()["id"]
        print("✓ 发表评价成功")

        response = await client.get("/api/reviews", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1
        print("✓ 获取评价列表成功")

        response = await client.get(f"/api/reviews/{review_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["rating"] == 5
        print("✓ 获取评价详情成功")

        response = await client.get(f"/api/reviews/order/{order_id}", headers=headers)
        assert response.status_code == 200
        print("✓ 根据订单获取评价成功")

        print("\n" + "=" * 60)
        print("✓✓✓ 所有测试通过！")
        print("=" * 60)

        print("\n--- 测试账号 ---")
        print("管理员: 13800138001 / admin123")
        print("回收员: 13800138002 / 123456")
        print("住户: 13900139001 / 123456")
        print(f"\n测试订单ID: {order_id}")
        print(f"接口文档: {BASE_URL}/docs")


if __name__ == "__main__":
    asyncio.run(test())
