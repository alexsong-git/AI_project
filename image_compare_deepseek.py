import pytesseract
from PIL import Image
import subprocess
import platform
import os

class OCRComparator:
    def __init__(self, keywords=["Order date", "Total", "Invoice"], lang="eng+chi_sim"):
        self.keywords = [k.lower() for k in keywords]  # 统一转为小写
        self.lang = lang
        self._setup_tesseract()

    def _setup_tesseract(self):
        """自动配置Tesseract路径"""
        try:
            path = '/opt/homebrew/bin/tesseract'
            pytesseract.pytesseract.tesseract_cmd = path

        except Exception as e:
            raise Exception(
                "Tesseract未安装或路径配置失败，请按以下步骤操作：\n"
                "1. macOS: 运行 `brew install tesseract tesseract-lang`\n"
                "2. Windows: 从 https://github.com/UB-Mannheim/tesseract/wiki 下载安装\n"
                "3. 手动设置路径: pytesseract.pytesseract.tesseract_cmd = '/your/path/tesseract'"
            ) from e

    def extract_text(self, image_path):
        """提取图片文字（自动预处理图片）"""
        try:
            img = Image.open(image_path)
            # 图像预处理（提高OCR精度）
            img = img.convert("L")  # 转灰度
            text = pytesseract.image_to_string(img, lang=self.lang)
            return text.lower()
        except Exception as e:
            print(f"OCR处理失败: {e}")
            return ""

    def compare(self, img_path1, img_path2):
        """执行关键元素对比"""
        text1 = self.extract_text(img_path1)
        text2 = self.extract_text(img_path2)

        if not text1 or not text2:
            return False, "OCR提取失败"

        # 检查关键词
        missing_in_1 = [k for k in self.keywords if k not in text1]
        missing_in_2 = [k for k in self.keywords if k not in text2]

        # 生成报告
        report = []
        if missing_in_1:
            report.append(f"图片1缺少: {', '.join(missing_in_1)}")
        if missing_in_2:
            report.append(f"图片2缺少: {', '.join(missing_in_2)}")

        is_same = not (missing_in_1 or missing_in_2)
        return is_same, " | ".join(report) if report else "所有关键元素一致"

# 使用示例
if __name__ == "__main__":
    # 初始化（可自定义关键词和语言）
    comparator = OCRComparator(
        keywords=["Order date", "Total", "Invoice", "日期", "金额"],  # 中英文关键词
        lang="eng+chi_sim"  # 英文+中文
    )

    # 输入图片路径
    img1 = "/Users/alex/image/wechat_2025-08-11_180934_700.png"
    img2 = "/Users/alex/image/wechat_2025-08-11_180943_074.png"

    # 执行比较
    result, detail = comparator.compare(img1, img2)

    # 打印结果
    print("\n🔍 关键元素比对报告：")
    print(f"- 结果: {'一致 ✅' if result else '不一致 ❌'}")
    print(f"- 详情: {detail}")
    print("\n💡 提示: 修改 keywords 参数可检查其他关键元素")