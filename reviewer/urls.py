# reviewer/urls.py
# v1：審核進度未更新，上一張功能未實作

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EndoscopyImageViewSet

# 建立一個 router 物件
router = DefaultRouter()
# 註冊的 ViewSet，'images' 是 URL 的前綴
router.register(r'images', EndoscopyImageViewSet, basename='endoscopyimage')

# urlpatterns 會包含 router 自動生成的所有 URL
urlpatterns = [
    path('', include(router.urls)),
]