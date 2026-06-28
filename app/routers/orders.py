from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
import uuid

from ..database import get_db
from ..models import User, Order, OrderItem, Category, Address
from ..schemas import (
    OrderCreate, OrderItemActualWeight,
    OrderResponse
)
from ..auth import get_current_user, require_role

router = APIRouter(prefix="/api/orders", tags=["订单模块"])

STATUS_FLOW = {
    "pending": ["accepted", "cancelled"],
    "accepted": ["collecting", "cancelled"],
    "collecting": ["completed", "cancelled"],
    "completed": [],
    "cancelled": []
}


def generate_order_no():
    return f"RC{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"


def enrich_order_items(db, order_items):
    enriched = []
    for item in order_items:
        item_dict = item.__dict__ if hasattr(item, '__dict__') else item
        category = db.query(Category).filter(Category.id == item_dict['category_id']).first()
        if not category or not category.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"品类ID {item_dict['category_id']} 不存在或已下架"
            )
        unit_price = category.unit_price
        estimated_price = item_dict['estimated_weight'] * unit_price

        enriched_item = {
            "category_id": item_dict['category_id'],
            "estimated_weight": item_dict['estimated_weight'],
            "unit_price": unit_price,
            "estimated_price": estimated_price,
            "category_name": category.name,
            "unit": category.unit
        }
        enriched.append(enriched_item)
    return enriched


@router.post("", response_model=OrderResponse, summary="用户下单")
def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(require_role(["resident"])),
    db: Session = Depends(get_db)
):
    address = db.query(Address).filter(
        Address.id == order_data.address_id,
        Address.user_id == current_user.id
    ).first()
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="地址不存在"
        )

    enriched_items = enrich_order_items(db, order_data.order_items)
    estimated_amount = sum(item['estimated_price'] for item in enriched_items)

    order_no = generate_order_no()
    new_order = Order(
        order_no=order_no,
        user_id=current_user.id,
        address_id=order_data.address_id,
        estimated_amount=estimated_amount,
        appointment_time=order_data.appointment_time,
        remark=order_data.remark,
        status="pending"
    )

    db.add(new_order)
    db.flush()

    for item in enriched_items:
        order_item = OrderItem(
            order_id=new_order.id,
            category_id=item['category_id'],
            estimated_weight=item['estimated_weight'],
            unit_price=item['unit_price'],
            estimated_price=item['estimated_price']
        )
        db.add(order_item)

    db.commit()
    db.refresh(new_order)

    for item in new_order.order_items:
        category = db.query(Category).filter(Category.id == item.category_id).first()
        item.category_name = category.name
        item.unit = category.unit

    return new_order


@router.get("", response_model=List[OrderResponse], summary="获取订单列表")
def get_orders(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Order)

    if current_user.role == "resident":
        query = query.filter(Order.user_id == current_user.id)
    elif current_user.role == "collector":
        query = query.filter(
            (Order.collector_id == current_user.id) |
            (Order.status == "pending")
        )

    if status:
        query = query.filter(Order.status == status)

    orders = query.order_by(Order.created_at.desc()).all()

    for order in orders:
        for item in order.order_items:
            category = db.query(Category).filter(Category.id == item.category_id).first()
            item.category_name = category.name
            item.unit = category.unit

    return orders


@router.get("/{order_id}", response_model=OrderResponse, summary="获取订单详情")
def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )

    if current_user.role == "resident" and order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限查看此订单"
        )

    if current_user.role == "collector" and order.collector_id != current_user.id and order.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限查看此订单"
        )

    for item in order.order_items:
        category = db.query(Category).filter(Category.id == item.category_id).first()
        item.category_name = category.name
        item.unit = category.unit

    return order


@router.put("/{order_id}/accept", response_model=OrderResponse, summary="回收员接单")
def accept_order(
    order_id: int,
    current_user: User = Depends(require_role(["collector"])),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )

    if order.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="订单状态不允许接单"
        )

    order.collector_id = current_user.id
    order.status = "accepted"
    order.accepted_at = datetime.utcnow()

    db.commit()
    db.refresh(order)

    for item in order.order_items:
        category = db.query(Category).filter(Category.id == item.category_id).first()
        item.category_name = category.name
        item.unit = category.unit

    return order


@router.put("/{order_id}/status", response_model=OrderResponse, summary="更新订单状态")
def update_order_status(
    order_id: int,
    new_status: str,
    cancel_reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )

    if new_status not in ["pending", "accepted", "collecting", "completed", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的订单状态"
        )

    if new_status not in STATUS_FLOW[order.status]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无法从 {order.status} 状态流转到 {new_status}"
        )

    if new_status == "cancelled":
        if current_user.role == "resident" and order.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限取消此订单"
            )
        if current_user.role == "collector" and order.collector_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限取消此订单"
            )
        if not cancel_reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="取消订单需要填写原因"
            )
        order.cancel_reason = cancel_reason
        order.cancelled_at = datetime.utcnow()
    elif new_status == "collecting":
        if current_user.role != "collector" or order.collector_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有接单回收员可以开始回收"
            )
    elif new_status == "completed":
        if current_user.role != "collector" or order.collector_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有接单回收员可以完成订单"
            )
        if any(item.actual_weight is None for item in order.order_items):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请先录入所有品类的实际重量"
            )
        order.completed_at = datetime.utcnow()

    order.status = new_status
    db.commit()
    db.refresh(order)

    for item in order.order_items:
        category = db.query(Category).filter(Category.id == item.category_id).first()
        item.category_name = category.name
        item.unit = category.unit

    return order


@router.put("/{order_id}/actual-weight", response_model=OrderResponse, summary="回收员录入实际重量")
def update_actual_weight(
    order_id: int,
    items_data: List[OrderItemActualWeight],
    current_user: User = Depends(require_role(["collector"])),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )

    if order.collector_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有接单回收员可以录入实际重量"
        )

    if order.status not in ["accepted", "collecting"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="订单状态不允许录入实际重量"
        )

    order_item_ids = [item.id for item in order.order_items]
    for item_data in items_data:
        if item_data.order_item_id not in order_item_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"订单项 {item_data.order_item_id} 不存在"
            )

        order_item = db.query(OrderItem).filter(
            OrderItem.id == item_data.order_item_id
        ).first()

        order_item.actual_weight = item_data.actual_weight
        order_item.actual_price = item_data.actual_weight * order_item.unit_price

    final_amount = sum(
        item.actual_price for item in order.order_items
        if item.actual_price is not None
    )
    order.final_amount = final_amount

    db.commit()
    db.refresh(order)

    for item in order.order_items:
        category = db.query(Category).filter(Category.id == item.category_id).first()
        item.category_name = category.name
        item.unit = category.unit

    return order
