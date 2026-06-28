from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import User, Order, Review
from ..schemas import ReviewCreate, ReviewResponse
from ..auth import get_current_user, require_role

router = APIRouter(prefix="/api/reviews", tags=["评价模块"])


@router.post("", response_model=ReviewResponse, summary="发表评价")
def create_review(
    review_data: ReviewCreate,
    current_user: User = Depends(require_role(["resident"])),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == review_data.order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )

    if order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能评价自己的订单"
        )

    if order.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只有已完成的订单才能评价"
        )

    existing_review = db.query(Review).filter(Review.order_id == review_data.order_id).first()
    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该订单已评价"
        )

    new_review = Review(
        order_id=review_data.order_id,
        user_id=current_user.id,
        rating=review_data.rating,
        comment=review_data.comment
    )

    db.add(new_review)
    db.commit()
    db.refresh(new_review)
    return new_review


@router.get("", response_model=List[ReviewResponse], summary="获取评价列表")
def get_reviews(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Review)

    if current_user.role == "resident":
        query = query.filter(Review.user_id == current_user.id)

    reviews = query.order_by(Review.created_at.desc()).all()
    return reviews


@router.get("/{review_id}", response_model=ReviewResponse, summary="获取评价详情")
def get_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="评价不存在"
        )

    if current_user.role == "resident" and review.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限查看此评价"
        )

    return review


@router.get("/order/{order_id}", response_model=ReviewResponse, summary="根据订单获取评价")
def get_review_by_order(
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
            detail="无权限查看此评价"
        )

    review = db.query(Review).filter(Review.order_id == order_id).first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该订单暂无评价"
        )

    return review
