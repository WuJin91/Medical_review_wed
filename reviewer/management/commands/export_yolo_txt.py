# endoscopy-project/reviewer/management/commands/export_yolo_txt.py

import os
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from reviewer.models import EndoscopyImage, ImageBatch, Annotation

class Command(BaseCommand):
    """
    一個 Django 管理命令，用於匯出醫師審核過的 Ground Truth 標註資料，
    並產生 YOLOv8 訓練所需的 .txt 格式檔案。
    """
    help = '匯出醫師審核過的標註資料為 YOLO .txt 格式'

    def add_arguments(self, parser):
        """定義指令接收的參數"""
        parser.add_argument(
            'output_path',
            type=str,
            help='指定匯出的 .txt 檔案要存放的資料夾路徑'
        )
        parser.add_argument(
            '--batch-name',
            type=str,
            required=False,
            help='(可選) 只匯出特定批次名稱的標註資料'
        )

    def handle(self, *args, **options):
        """指令的主要執行邏輯"""
        output_path_str = options['output_path']
        batch_name = options['batch_name']

        # --- 1. 驗證並準備輸出路徑 ---
        output_path = Path(output_path_str)
        if not output_path.exists():
            self.stdout.write(self.style.WARNING(f"輸出路徑不存在，將自動建立資料夾: {output_path}"))
            output_path.mkdir(parents=True, exist_ok=True)
        elif not output_path.is_dir():
            raise CommandError(f"錯誤：指定的輸出路徑 '{output_path_str}' 已存在但不是一個資料夾。")

        # --- 2. 根據參數查詢要處理的影像 ---
        # 只處理醫師已經審核過的影像
        images_to_process = EndoscopyImage.objects.filter(
            review_status__in=[
                EndoscopyImage.ReviewStatus.APPROVED,
                EndoscopyImage.ReviewStatus.CORRECTED
            ]
        ).prefetch_related('annotations') # 優化查詢：預先載入相關的標註

        if batch_name:
            # 驗證批次是否存在
            if not ImageBatch.objects.filter(name=batch_name).exists():
                raise CommandError(f"錯誤：找不到名為 '{batch_name}' 的批次。")
            
            images_to_process = images_to_process.filter(batch__name=batch_name)
            self.stdout.write(f"已篩選批次：'{batch_name}'")

        if not images_to_process.exists():
            self.stdout.write(self.style.WARNING("找不到任何已審核的影像可供匯出。"))
            return

        self.stdout.write(f"找到 {images_to_process.count()} 張已審核影像，開始匯出...")

        # --- 3. 遍歷影像，生成標註檔 ---
        exported_count = 0
        for image in images_to_process:
            # 從預載入的 annotations 中進行篩選
            valid_annotations = [
                ann for ann in image.annotations.all()
                if ann.doctor_box is not None and not ann.is_deleted
            ]

            yolo_content_lines = []
            for ann in valid_annotations:
                # 組合 YOLO 格式字串: class_id x_center y_center width height
                line = (
                    f"{ann.class_label} "
                    f"{ann.doctor_box['x_center']} "
                    f"{ann.doctor_box['y_center']} "
                    f"{ann.doctor_box['width']} "
                    f"{ann.doctor_box['height']}"
                )
                yolo_content_lines.append(line)
            
            # 決定輸出檔名 (與原始影像檔名相同，副檔名改為 .txt)
            file_stem = Path(image.original_image.name).stem
            output_file_path = output_path / f"{file_stem}.txt"
            
            # 寫入檔案 (即使沒有有效標註，也會產生一個空檔案)
            try:
                with open(output_file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(yolo_content_lines))
                exported_count += 1
            except IOError as e:
                self.stderr.write(self.style.ERROR(f"寫入檔案失敗: {output_file_path}\n錯誤: {e}"))

        self.stdout.write(self.style.SUCCESS(f"\n處理完成！共成功匯出 {exported_count} 個標註檔案至 {output_path}"))