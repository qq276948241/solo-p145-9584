from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import User, Category
from ..schemas import CategoryCreate, CategoryUpdate, CategoryResponse
from ..auth import get_current_user, require_role

router = APIRouter(prefix="/api/categories", tags=["品类模块"])


@router.get("", response_model=List[CategoryResponse], summary="获取品类列表")
def get_categories(
    is_active: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Category)
    if is_active is not None:
        query = query.filter(Category.is_active == is_active)
    categories = query.order_by(Category.id).all()
    return categories


@router.get("/{category_id}", response_model=CategoryResponse, summary="获取品类详情")
def get_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="品类不存在"
        )
    return category


@router.post("", response_model=CategoryResponse, summary="新增品类")
def create_category(
    category_data: CategoryCreate,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    db_category = db.query(Category).filter(Category.name == category_data.name).first()
    if db_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该品类已存在"
        )

    new_category = Category(**category_data.model_dump())
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category


@router.put("/{category_id}", response_model=CategoryResponse, summary="更新品类")
def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="品类不存在"
        )

    if category_data.name and category_data.name != category.name:
        db_category = db.query(Category).filter(Category.name == category_data.name).first()
        if db_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该品类名称已存在"
            )

    update_data = category_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)

    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", summary="删除品类")
def delete_category(
    category_id: int,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="品类不存在"
        )

    category.is_active = False
    db.commit()
    return {"message": "删除成功"}
