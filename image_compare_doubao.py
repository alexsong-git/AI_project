import os
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageChops
import torch
import clip
from sklearn.metrics.pairwise import cosine_similarity

# 改进中文显示设置
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC", "Arial Unicode MS"]
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题


def highlight_differences(img1, img2, output_path="difference.png"):
    """生成并保存差异高亮图"""
    # 确保图片尺寸相同
    if img1.size != img2.size:
        img2 = img2.resize(img1.size, Image.Resampling.LANCZOS)  # 使用高质量缩放

    # 统一图片模式为RGB
    img1 = img1.convert("RGB")
    img2 = img2.convert("RGB")

    # 计算差异
    diff = ImageChops.difference(img1, img2)

    # 转换为灰度并增强差异
    diff = diff.convert("L")
    diff = diff.point(lambda x: 255 if x > 30 else 0)  # 阈值可调整

    # 在原图上标记差异区域（红色半透明）
    overlay = Image.new("RGBA", img1.size, (255, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # 使用numpy处理差异区域，提高效率
    diff_np = np.array(diff)
    y_indices, x_indices = np.where(diff_np > 0)

    # 修复：检查是否有差异点，避免空列表导致的错误
    if len(x_indices) > 0 and len(y_indices) > 0:
        for x, y in zip(x_indices[::5], y_indices[::5]):
            draw.rectangle([x - 2, y - 2, x + 2, y + 2], fill=(255, 0, 0, 100))

    # 合成最终图像
    result = img1.convert("RGBA").copy()
    result.alpha_composite(overlay)
    result.save(output_path)
    return output_path


def compare_images_with_visualization(image_path1, image_path2, similarity_threshold=0.85):
    """带可视化功能的图片比较"""
    # 检查文件是否存在
    for path in [image_path1, image_path2]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"图片文件不存在: {path}")

    device = "cuda" if torch.cuda.is_available() else "cpu"

    # 加载图片
    try:
        img1 = Image.open(image_path1)
        img2 = Image.open(image_path2)
    except Exception as e:
        raise IOError(f"图片加载失败: {str(e)}")

    # 生成差异图
    diff_path = highlight_differences(img1, img2)

    # 加载CLIP模型
    try:
        model, preprocess = clip.load("ViT-B/32", device=device)
    except Exception as e:
        raise RuntimeError(f"CLIP模型加载失败: {str(e)}")

    # 计算全局相似度
    try:
        inputs = torch.stack([preprocess(img) for img in [img1, img2]]).to(device)
        with torch.no_grad():
            features = model.encode_image(inputs)
        similarity = cosine_similarity(
            features[0].cpu().numpy().reshape(1, -1),
            features[1].cpu().numpy().reshape(1, -1)
        )[0][0]
    except Exception as e:
        raise RuntimeError(f"相似度计算失败: {str(e)}")

    # 识别差异区域内容
    diff_regions = []
    if similarity < similarity_threshold:
        # 修复：确保裁剪尺寸合理，避免过小图片导致的问题
        min_crop_size = 32  # 最小裁剪尺寸，避免小于模型要求的输入尺寸
        crop_width = max(min_crop_size, img1.width // 2)
        crop_height = max(min_crop_size, img1.height // 2)
        crop_size = (crop_width, crop_height)

        # 计算安全的裁剪坐标，确保不会越界
        x_coords = [0, max(0, img1.width - crop_width)]
        y_coords = [0, max(0, img1.height - crop_height)]

        # 生成裁剪区域，确保列表不为空
        crops1 = []
        crops2 = []
        for x in x_coords:
            for y in y_coords:
                # 确保裁剪区域在图片范围内
                if x + crop_width <= img1.width and y + crop_height <= img1.height:
                    crops1.append(img1.crop((x, y, x + crop_width, y + crop_height)))
                    crops2.append(img2.crop((x, y, x + crop_width, y + crop_height)))

        # 修复：检查裁剪列表长度是否一致，避免索引错误
        if len(crops1) == len(crops2) and len(crops1) > 0:
            # 比较每个局部区域
            for i, (c1, c2) in enumerate(zip(crops1, crops2)):
                # 修复：确保裁剪区域足够大
                if c1.size[0] < min_crop_size or c1.size[1] < min_crop_size:
                    continue

                inputs = torch.stack([preprocess(c) for c in [c1, c2]]).to(device)
                with torch.no_grad():
                    crop_features = model.encode_image(inputs)
                crop_sim = cosine_similarity(
                    crop_features[0].cpu().numpy().reshape(1, -1),
                    crop_features[1].cpu().numpy().reshape(1, -1)
                )[0][0]

                if crop_sim < similarity_threshold:
                    # 获取区域描述
                    with torch.no_grad():
                        # 修复：确保文本列表和描述列表长度一致
                        texts = ["整体场景", "物体", "人物", "文字", "背景"]
                        text_tokens = clip.tokenize(texts).to(device)
                        text_features = model.encode_text(text_tokens)
                        probs = (crop_features @ text_features.T).softmax(dim=-1)
                    # 修复：确保索引在有效范围内
                    max_prob_idx = min(probs.argmax().item(), len(texts) - 1)
                    desc = texts[max_prob_idx]
                    diff_regions.append(f"区域{i + 1}({desc})")

    # 可视化结果
    plt.figure(figsize=(15, 5))

    plt.subplot(1, 3, 1)
    plt.imshow(img1)
    plt.title("图片1")
    plt.axis('off')

    plt.subplot(1, 3, 2)
    plt.imshow(img2)
    plt.title("图片2")
    plt.axis('off')

    plt.subplot(1, 3, 3)
    plt.imshow(Image.open(diff_path))
    plt.title(f"差异区域\n相似度: {similarity:.2f}")
    if diff_regions:
        plt.xlabel("主要差异:\n" + "\n".join(diff_regions))
    plt.axis('off')

    plt.tight_layout()
    plt.savefig("comparison_result.png", dpi=300, bbox_inches="tight")
    plt.show()

    return similarity, diff_path, diff_regions


if __name__ == "__main__":
    # 请替换为你的图片路径
    image1_path = "/Users/alex/image/wechat_2025-08-11_180934_700.png"
    image2_path = "/Users/alex/image/wechat_2025-08-13_131908_809.png"

    try:
        similarity, diff_path, diff_regions = compare_images_with_visualization(image1_path, image2_path)

        print(f"全局相似度: {similarity:.4f}")
        print(f"差异区域描述: {diff_regions}")
        print(f"差异图已保存到: {diff_path}")
        print(f"完整比较结果已保存到: comparison_result.png")
    except Exception as e:
        print(f"执行出错: {str(e)}")
