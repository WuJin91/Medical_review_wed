# reviewer/models.py
# 每一個 class (類別) 都代表了資料庫中的一張資料表 (Table)

from django.db import models

class ImageBatch(models.Model):
    """影像批次模型"""
    name = models.CharField(max_length=200, unique=True, verbose_name="批次名稱")
    notes = models.TextField(blank=True, null=True, verbose_name="備註")
    import_method = models.CharField(max_length=50, default="manual_upload", verbose_name="匯入方式")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "影像批次"
        verbose_name_plural = "影像批次"
        ordering = ['-created_at']

class EndoscopyImage(models.Model):
    """內視鏡影像模型"""
    class ImageTypes(models.TextChoices):
        WLI = 'WLI', '白光影像'
        NBI = 'NBI', '窄頻影像'

    class ReviewStatus(models.TextChoices):
        PENDING = 'pending_review', '待審核'
        APPROVED = 'reviewed_approved', '已審核(正確)'
        CORRECTED = 'reviewed_corrected', '已審核(修正)'

    class DoctorDiagnosis(models.TextChoices):
        POLYP_ONLY = 'polyp_only', '只有瘜肉'
        TUMOR_ONLY = 'tumor_only', '只有腫瘤'
        BOTH = 'polyp_and_tumor', '有瘜肉和腫瘤'
        NEGATIVE = 'negative', '無病兆'
        # 增加一個未定義的狀態，避免醫師漏選
        UNDEFINED = 'undefined', '未定義'

    batch = models.ForeignKey(ImageBatch, on_delete=models.CASCADE, related_name='images', verbose_name="所屬批次")
    image_type = models.CharField(max_length=3, choices=ImageTypes.choices, verbose_name="影像類型")
    original_image = models.FileField(upload_to='original_images/%Y/%m/%d/', verbose_name="原始影像檔案")
    yolo_output_image = models.FileField(upload_to='yolo_output_images/%Y/%m/%d/', blank=True, null=True, verbose_name="YOLO輸出影像")
    review_status = models.CharField(max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.PENDING, verbose_name="審核狀態")
    
    doctor_diagnosis = models.CharField(
        max_length=20, 
        choices=DoctorDiagnosis.choices, 
        default=DoctorDiagnosis.UNDEFINED, 
        verbose_name="醫師最終診斷"
    )
    
    reviewed_at = models.DateTimeField(blank=True, null=True, verbose_name="審核時間")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")

    def __str__(self):
        # 確保 self.original_image.name 存在
        image_name = self.original_image.name if self.original_image else "No Image"
        return f"{self.batch.name} - {image_name}"

    class Meta:
        verbose_name = "內視鏡影像"
        verbose_name_plural = "內視鏡影像"
        ordering = ['created_at']

class Annotation(models.Model):
    """標記資訊模型"""
    class ClassLabels(models.IntegerChoices):
        POLYP = 0, '瘜肉'
        TUMOR = 1, '腫瘤'

    class SourceTypes(models.TextChoices):
        MODEL = 'model_generated', '模型產生'
        DOCTOR = 'doctor_added', '醫師新增'

    image = models.ForeignKey(EndoscopyImage, on_delete=models.CASCADE, related_name='annotations', verbose_name="所屬影像")
    class_label = models.IntegerField(choices=ClassLabels.choices, verbose_name="病兆類別")
    source_type = models.CharField(max_length=20, choices=SourceTypes.choices, verbose_name="標記來源")
    model_box = models.JSONField(blank=True, null=True, verbose_name="模型標記框 (AI)")
    doctor_box = models.JSONField(blank=True, null=True, verbose_name="醫師標記框 (Ground Truth)")
    is_deleted = models.BooleanField(default=False, verbose_name="是否已由醫師刪除")

    def __str__(self):
        return f"Annotation for image {self.image.id} - Label: {self.get_class_label_display()}"

    class Meta:
        verbose_name = "標記資訊"
        verbose_name_plural = "標記資訊"