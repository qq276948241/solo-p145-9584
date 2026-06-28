import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import engine, Base, SessionLocal
from app.models import Category, User
import bcrypt


def hash_password(password: str) -> str:
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    print("开始初始化数据...")

    default_categories = [
        {"name": "纸壳", "unit_price": 1.2, "unit": "kg", "description": "纸箱、纸板等"},
        {"name": "塑料", "unit_price": 0.8, "unit": "kg", "description": "塑料瓶、塑料盒等"},
        {"name": "金属", "unit_price": 3.5, "unit": "kg", "description": "易拉罐、铁皮等"},
        {"name": "旧家电", "unit_price": 50.0, "unit": "件", "description": "电视、冰箱、洗衣机等"},
        {"name": "旧衣物", "unit_price": 0.5, "unit": "kg", "description": "旧衣服、床上用品等"},
        {"name": "玻璃", "unit_price": 0.3, "unit": "kg", "description": "玻璃瓶、玻璃制品等"},
    ]

    for cat_data in default_categories:
        existing = db.query(Category).filter(Category.name == cat_data["name"]).first()
        if not existing:
            category = Category(**cat_data)
            db.add(category)
            print(f"添加品类: {cat_data['name']}")

    default_users = [
        {
            "phone": "13800138001",
            "username": "管理员",
            "password": "admin123",
            "role": "admin"
        },
        {
            "phone": "13800138002",
            "username": "张回收",
            "password": "123456",
            "role": "collector"
        },
        {
            "phone": "13800138003",
            "username": "李回收",
            "password": "123456",
            "role": "collector"
        },
        {
            "phone": "13900139001",
            "username": "王住户",
            "password": "123456",
            "role": "resident"
        },
        {
            "phone": "13900139002",
            "username": "赵住户",
            "password": "123456",
            "role": "resident"
        },
    ]

    for user_data in default_users:
        existing = db.query(User).filter(User.phone == user_data["phone"]).first()
        if not existing:
            hashed_pw = hash_password(user_data["password"])
            user = User(
                phone=user_data["phone"],
                username=user_data["username"],
                password_hash=hashed_pw,
                role=user_data["role"]
            )
            db.add(user)
            print(f"添加用户: {user_data['username']} ({user_data['role']}) - 账号: {user_data['phone']} 密码: {user_data['password']}")

    db.commit()
    print("数据初始化完成!")

except Exception as e:
    db.rollback()
    print(f"初始化失败: {e}")
finally:
    db.close()
