# reviewer/views.py
# v3: 修正 review_status 邏輯 & 實作軟刪除 (soft delete)

from django.utils import timezone
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import EndoscopyImage, Annotation
from .serializers import EndoscopyImageSerializer

class EndoscopyImageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EndoscopyImage.objects.all().order_by('created_at')
    serializer_class = EndoscopyImageSerializer

    @action(detail=False, methods=['get'], url_path='next-to-review')
    def next_to_review(self, request):
        next_image = EndoscopyImage.objects.filter(
            review_status=EndoscopyImage.ReviewStatus.PENDING
        ).order_by('created_at').first()
        if not next_image:
            return Response({"detail": "所有影像皆已審核完成。"}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(next_image)
        return Response(serializer.data)

    # --- ★★★ 核心修改 START ★★★ ---
    @action(detail=True, methods=['post'], url_path='submit-review')
    @transaction.atomic
    def submit_review(self, request, pk=None):
        image = self.get_object()
        annotations_data = request.data.get('annotations', [])
        is_modified = request.data.get('is_modified', True)

        # 1. 修正審核狀態的判斷
        if is_modified:
            image.review_status = EndoscopyImage.ReviewStatus.CORRECTED
        else:
            image.review_status = EndoscopyImage.ReviewStatus.APPROVED

        # 計算醫師最終診斷
        class_labels_present = {ann.get('class_label') for ann in annotations_data}
        final_diagnosis = EndoscopyImage.DoctorDiagnosis.NEGATIVE
        if class_labels_present:
            if class_labels_present == {0}: final_diagnosis = EndoscopyImage.DoctorDiagnosis.POLYP_ONLY
            elif class_labels_present == {1}: final_diagnosis = EndoscopyImage.DoctorDiagnosis.TUMOR_ONLY
            elif class_labels_present == {0, 1}: final_diagnosis = EndoscopyImage.DoctorDiagnosis.BOTH
            else: final_diagnosis = EndoscopyImage.DoctorDiagnosis.UNDEFINED
        
        # 更新影像的診斷、時間戳並儲存
        # 移除之前會強制覆蓋狀態的錯誤程式碼
        image.doctor_diagnosis = final_diagnosis
        image.reviewed_at = timezone.now()
        image.save()

        # 2. 重寫標記處理邏輯：改為比對更新，而非先刪後建
        existing_annotations = {str(ann.id): ann for ann in image.annotations.all()}
        processed_db_ids = set()

        # 遍歷前端提交的標記
        for ann_data in annotations_data:
            db_id = ann_data.get('db_id')
            
            # 情況 A: 更新現有標記
            if db_id and str(db_id) in existing_annotations:
                ann_obj = existing_annotations[str(db_id)]
                ann_obj.class_label = ann_data.get('class_label')
                ann_obj.doctor_box = ann_data.get('doctor_box')
                ann_obj.is_deleted = False # 如果之前被標記為刪除，現在被恢復了
                ann_obj.save()
                processed_db_ids.add(str(db_id))
            # 情況 B: 新增醫師標記
            else:
                Annotation.objects.create(
                    image=image,
                    class_label=ann_data.get('class_label'),
                    source_type=Annotation.SourceTypes.DOCTOR, # 新增的必為醫師來源
                    model_box=None, # 醫師新增的沒有模型框
                    doctor_box=ann_data.get('doctor_box')
                )
        
        # 情況 C: 處理被刪除的標記
        deleted_db_ids = set(existing_annotations.keys()) - processed_db_ids
        for del_id in deleted_db_ids:
            ann_to_process = existing_annotations[del_id]
            
            # 如果是 AI 產生的標記被刪除 -> 軟刪除 (soft delete)
            if ann_to_process.source_type == Annotation.SourceTypes.MODEL:
                ann_to_process.is_deleted = True
                ann_to_process.doctor_box = None # 被刪除的 AI 標記沒有醫師的 ground truth
                ann_to_process.save()
            # 如果是醫師自己新增的標記又被刪除 -> 直接刪除
            elif ann_to_process.source_type == Annotation.SourceTypes.DOCTOR:
                ann_to_process.delete()

        serializer = self.get_serializer(image)
        return Response(serializer.data, status=status.HTTP_200_OK)
    # --- ★★★ 核心修改 END ★★★ ---

    @action(detail=False, methods=['get'], url_path='progress-stats')
    def progress_stats(self, request):
        total_count = EndoscopyImage.objects.count()
        reviewed_count = EndoscopyImage.objects.filter(
            review_status__in=[
                EndoscopyImage.ReviewStatus.APPROVED,
                EndoscopyImage.ReviewStatus.CORRECTED
            ]
        ).count()
        return Response({"total": total_count, "reviewed": reviewed_count})

    @action(detail=True, methods=['get'], url_path='previous')
    def previous(self, request, pk=None):
        current_image = self.get_object()
        reviewed_images_in_batch = EndoscopyImage.objects.filter(
            batch=current_image.batch,
            review_status__in=[
                EndoscopyImage.ReviewStatus.APPROVED,
                EndoscopyImage.ReviewStatus.CORRECTED
            ]
        )
        if current_image.review_status in [EndoscopyImage.ReviewStatus.APPROVED, EndoscopyImage.ReviewStatus.CORRECTED] and current_image.reviewed_at:
            previous_image = reviewed_images_in_batch.filter(
                reviewed_at__lt=current_image.reviewed_at
            ).order_by('-reviewed_at').first()
        else:
            previous_image = reviewed_images_in_batch.order_by('-reviewed_at').first()

        if not previous_image:
            return Response(
                {"detail": "此批次中沒有更早的已審核影像。"},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.get_serializer(previous_image)
        return Response(serializer.data)