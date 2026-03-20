# reviewer/management/commands/import_images.py

import os
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from reviewer.models import ImageBatch, EndoscopyImage, Annotation

class Command(BaseCommand):
    """
    一個 Django 管理命令，用於從指定資料夾批次匯入影像和 YOLO 標記檔。
    """ 
    help = '從資料夾批次匯入原始影像、YOLO 輸出影像和標記檔'

    # 指令的參數定義 (add_arguments)
    def add_arguments(self, parser):
        """定義指令接收的參數"""
        parser.add_argument('batch_name', type=str, help='要建立或使用的批次名稱')
        parser.add_argument('originals_path', type=str, help='原始影像的資料夾路徑')
        parser.add_argument('yolo_outputs_path', type=str, help='YOLO 輸出 (影像和txt) 的資料夾路徑')
    
    # 核心處理邏輯 (handle 函式)
    @transaction.atomic # 使用資料庫事務，確保所有操作要麼全部成功，要麼全部失敗
    def handle(self, *args, **options):
        """指令的主要執行邏輯"""
        # 先接收傳入的三個參數
        batch_name = options['batch_name']
        originals_path = Path(options['originals_path'])
        yolo_outputs_path = Path(options['yolo_outputs_path'])

        # --- 1. 驗證路徑是否存在 ---
        if not originals_path.is_dir():
            raise CommandError(f"錯誤：原始影像路徑不存在或不是一個資料夾: {originals_path}")
        if not yolo_outputs_path.is_dir():
            raise CommandError(f"錯誤：YOLO 輸出路徑不存在或不是一個資料夾: {yolo_outputs_path}")

        self.stdout.write(self.style.SUCCESS(f"開始處理批次：'{batch_name}'"))

        # --- 2. 取得或建立 ImageBatch ---
        batch, created = ImageBatch.objects.get_or_create(      # get_or_create 避免重複匯入相同批次
            name=batch_name,
            defaults={'import_method': 'management_command'}
        )
        if created:
            self.stdout.write(f"已建立新的批次：'{batch_name}'")
        else:
            self.stdout.write(f"使用現有批次：'{batch_name}'")

        # --- 3. 掃描原始影像資料夾並處理檔案 ---
        processed_count = 0
        for original_file_path in originals_path.iterdir():
            if original_file_path.is_file() and original_file_path.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                file_stem = original_file_path.stem  # 取得其檔名主幹 (stem)，取得不含副檔名的檔名
                
                # --- 4. 尋找對應的 YOLO 輸出檔案 ---
                yolo_image_path = yolo_outputs_path / f"{file_stem}.jpg"
                yolo_txt_path = yolo_outputs_path / f"{file_stem}.txt"

                if not yolo_image_path.exists():
                    self.stdout.write(self.style.WARNING(f"警告：找不到對應的 YOLO 影像，跳過：{yolo_image_path}"))
                    continue
                if not yolo_txt_path.exists():
                    self.stdout.write(self.style.WARNING(f"警告：找不到對應的 YOLO 標記檔，跳過：{yolo_txt_path}"))
                    continue

                # --- 5. 建立 EndoscopyImage 紀錄 ---
                # 根據檔名是否包含 "NBI" 來推斷
                image_type = 'NBI' if 'NBI' in file_stem.upper() else 'WLI'
                
                image_instance, image_created = EndoscopyImage.objects.get_or_create(
                    batch=batch,
                    original_image=os.path.join('original_images', original_file_path.name), # 儲存相對路徑
                    defaults={
                        'image_type': image_type,
                        # 注意：此處僅儲存路徑，實際檔案需手動或透過另一腳本複製到 MEDIA_ROOT/original_images/
                        'yolo_output_image': os.path.join('yolo_output_images', yolo_image_path.name),
                    }
                )

                if not image_created:
                    self.stdout.write(f"影像 '{original_file_path.name}' 已存在於批次中，跳過。")
                    continue

                # --- 6. 讀取 .txt 檔並建立 Annotation 紀錄 ---
                with open(yolo_txt_path, 'r') as f:
                    lines = f.readlines()
                
                if not lines:
                    self.stdout.write(f"影像 '{original_file_path.name}' 的標記檔為空，無偵測到病兆。")
                else:
                    for line in lines:
                        parts = line.strip().split()
                        if len(parts) == 5:
                            class_id, x, y, w, h = map(float, parts)
                            Annotation.objects.create(
                                image=image_instance,
                                class_label=int(class_id),
                                source_type=Annotation.SourceTypes.MODEL,
                                model_box={
                                    'x_center': x,
                                    'y_center': y,
                                    'width': w,
                                    'height': h,
                                }
                            )
                processed_count += 1
                self.stdout.write(f"成功處理並匯入：{original_file_path.name}")

        self.stdout.write(self.style.SUCCESS(f"處理完成！共成功匯入 {processed_count} 張新影像。"))