# reviewer/admin.py

from django.contrib import admin
from .models import ImageBatch, EndoscopyImage, Annotation

class AnnotationInline(admin.TabularInline):
    """讓 Annotation可以直接在 EndoscopyImage 頁面中編輯"""
    model = Annotation
    extra = 0  # 預設不顯示額外的新增欄位
    fields = ('class_label', 'source_type', 'model_box', 'doctor_box', 'is_deleted')
    readonly_fields = ('model_box', 'source_type') # 模型的原始標記和來源不應在後台被修改

# 註冊模型 (@admin.register)

@admin.register(ImageBatch)
class ImageBatchAdmin(admin.ModelAdmin):
    list_display = ('name', 'import_method', 'created_at')
    search_fields = ('name',)

@admin.register(EndoscopyImage)
class EndoscopyImageAdmin(admin.ModelAdmin):
    # 將 doctor_diagnosis 加入顯示列表
    list_display = ('id', 'batch', 'image_type', 'review_status', 'doctor_diagnosis', 'reviewed_at')
    # 將 doctor_diagnosis 加入篩選器
    list_filter = ('review_status', 'doctor_diagnosis', 'image_type', 'batch')
    search_fields = ('original_image__icontains',)  # 可透過原始檔名搜尋
    date_hierarchy = 'created_at'   # 增加日期快速篩選
    inlines = [AnnotationInline]    # 嵌入 Annotation 編輯區

@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ('id', 'image', 'class_label', 'source_type', 'is_deleted')
    list_filter = ('class_label', 'source_type', 'is_deleted')
    search_fields = ('image__original_image__icontains',)