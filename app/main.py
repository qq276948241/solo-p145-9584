from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base
from .routers import users, categories, orders, reviews

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="小区废旧物品上门回收API",
    description="住户在线预约回收员上门称重结算系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(categories.router)
app.include_router(orders.router)
app.include_router(reviews.router)


@app.get("/", tags=["根路径"])
def root():
    return {
        "message": "欢迎使用小区废旧物品上门回收API",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health", tags=["健康检查"])
def health_check():
    return {"status": "healthy"}
