# reviewer/serializers.py
# v1：審核進度未更新，上一張功能未實作

from rest_framework import serializers
from .models import Annotation, EndoscopyImage

class AnnotationSerializer(serializers.ModelSerializer):
    """
    序列化 Annotation 模型
    """
    # 取得選項的顯示名稱，而非數字/代碼
    # 這兩行是為了「增加」資料庫中沒有的欄位，提升前端開發的便利性
    # read_only=True 表示這個欄位只用於「序列化」（給前端看），不能被前端寫入
    class_label_display = serializers.CharField(source='get_class_label_display', read_only=True)
    source_type_display = serializers.CharField(source='get_source_type_display', read_only=True)

    class Meta:
        model = Annotation              # 將這個 Serializer 綁定到 Annotation Model
        fields = [                      # fields = [...] 用來列出欲序列化的欄位清單  
            'id', 
            'class_label',              # 原始資料 (0 或 1)
            'class_label_display',      # 翻譯後的資料 ("Polyp" 或 "Tumor")
            'source_type',
            'source_type_display',
            'model_box', 
            'doctor_box', 
            'is_deleted'
        ]

class EndoscopyImageSerializer(serializers.ModelSerializer):
    """
    序列化 EndoscopyImage 模型，並包含其所有的 Annotation
    """
    # 嵌套 AnnotationSerializer，一個 Image 會包含多個 Annotation
    annotations = AnnotationSerializer(many=True, read_only=True)

    # 取得選項的顯示名稱
    image_type_display = serializers.CharField(source='get_image_type_display', read_only=True)
    review_status_display = serializers.CharField(source='get_review_status_display', read_only=True)
    doctor_diagnosis_display = serializers.CharField(source='get_doctor_diagnosis_display', read_only=True)

    # 將檔案路徑轉換成前端可直接使用的完整 URL
    original_image_url = serializers.ImageField(source='original_image', read_only=True)
    yolo_output_image_url = serializers.ImageField(source='yolo_output_image', read_only=True)


    class Meta:
        model = EndoscopyImage
        fields = [
            'id', 
            'batch', 
            'image_type',
            'image_type_display',
            'original_image_url', 
            'yolo_output_image_url', 
            'review_status', 
            'review_status_display',
            'doctor_diagnosis',
            'doctor_diagnosis_display',
            'reviewed_at', 
            'created_at',
            'annotations' # 包含嵌套的標記資訊
        ]