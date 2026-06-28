from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List


class UserBase(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11, description="手机号")
    username: str = Field(..., min_length=2, max_length=50, description="用户名")


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=50, description="密码")
    role: Optional[str] = Field(default="resident", description="角色：resident/collector/admin")


class UserLogin(BaseModel):
    phone: str = Field(..., description="手机号")
    password: str = Field(..., description="密码")


class UserResponse(UserBase):
    id: int
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class AddressBase(BaseModel):
    name: str = Field(..., description="收货人姓名")
    phone: str = Field(..., description="收货人电话")
    address_detail: str = Field(..., description="详细地址")
    is_default: Optional[bool] = False


class AddressCreate(AddressBase):
    pass


class AddressUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address_detail: Optional[str] = None
    is_default: Optional[bool] = None


class AddressResponse(AddressBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class CategoryBase(BaseModel):
    name: str = Field(..., description="品类名称")
    unit_price: float = Field(..., gt=0, description="单价")
    unit: Optional[str] = "kg"
    description: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    unit_price: Optional[float] = Field(None, gt=0)
    unit: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class CategoryResponse(CategoryBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class OrderItemBase(BaseModel):
    category_id: int = Field(..., description="品类ID")
    estimated_weight: float = Field(..., gt=0, description="预估重量")


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemActualWeight(BaseModel):
    order_item_id: int = Field(..., description="订单项ID")
    actual_weight: float = Field(..., gt=0, description="实际重量")


class OrderItemResponse(BaseModel):
    id: int
    category_id: int
    category_name: Optional[str] = None
    estimated_weight: float
    actual_weight: Optional[float] = None
    unit_price: float
    estimated_price: float
    actual_price: Optional[float] = None
    unit: Optional[str] = None

    class Config:
        from_attributes = True


class OrderBase(BaseModel):
    address_id: int = Field(..., description="地址ID")
    appointment_time: Optional[datetime] = None
    remark: Optional[str] = None
    order_items: List[OrderItemCreate] = Field(..., description="品类列表")


class OrderCreate(OrderBase):
    pass


class OrderUpdateStatus(BaseModel):
    status: str = Field(..., description="订单状态")
    cancel_reason: Optional[str] = None


class OrderResponse(BaseModel):
    id: int
    order_no: str
    user_id: int
    collector_id: Optional[int] = None
    address_id: int
    address: Optional[AddressResponse] = None
    status: str
    estimated_amount: float
    final_amount: float
    remark: Optional[str] = None
    appointment_time: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancel_reason: Optional[str] = None
    order_items: List[OrderItemResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewBase(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="评分1-5")
    comment: Optional[str] = None


class ReviewCreate(ReviewBase):
    order_id: int = Field(..., description="订单ID")


class ReviewResponse(ReviewBase):
    id: int
    order_id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True
