 # endoscopy-project/backend/urls.py
 # 使用 Django REST Framework 建立 API
 # v1：審核進度未更新，上一張功能未實作

from django.contrib import admin
# 記得匯入 include
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # 所有 /api/ 開頭的網址都交給 reviewer.urls 處理
    path('api/', include('reviewer.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)