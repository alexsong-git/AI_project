import boto3
from botocore.config import Config
import os
import glob


def upload_file_to_s3(local_file_path, bucket_name, s3_key=None):
    """
    将单个本地文件上传到S3存储桶

    参数:
        local_file_path: 本地文件的完整路径
        bucket_name: S3存储桶名称
        s3_key: 上传到S3后的文件路径和名称，默认为本地文件名
    """
    try:
        # 配置S3客户端
        s3 = boto3.client('s3', config=Config(signature_version='s3v4'))

        # 如果未指定S3键，则使用本地文件名作为键
        if not s3_key:
            s3_key = os.path.basename(local_file_path)

        # 上传文件
        s3.upload_file(local_file_path, bucket_name, s3_key)

        print(f"✅ 成功: {local_file_path} -> s3://{bucket_name}/{s3_key}")
        return True

    except FileNotFoundError:
        print(f"❌ 错误: 找不到本地文件 {local_file_path}")
    except Exception as e:
        print(f"❌ 失败 {local_file_path}: {str(e)}")
    return False


def upload_all_json_to_s3(local_dir, bucket_name, s3_base_path=""):
    """
    批量上传指定目录下所有JSON文件到S3存储桶

    参数:
        local_dir: 本地目录路径
        bucket_name: S3存储桶名称
        s3_base_path: S3上的基础路径，所有文件会上传到该路径下
    """
    # 检查本地目录是否存在
    if not os.path.isdir(local_dir):
        print(f"❌ 错误: 本地目录不存在 {local_dir}")
        return

    # 获取目录下所有JSON文件
    json_files = glob.glob(os.path.join(local_dir, "*.json"))

    if not json_files:
        print(f"ℹ️ 提示: 目录 {local_dir} 下没有找到JSON文件")
        return

    print(f"📁 发现 {len(json_files)} 个JSON文件，开始上传...")

    # 统计上传结果
    success_count = 0
    fail_count = 0

    # 逐个上传文件
    for json_file in json_files:
        # 构建S3路径：基础路径 + 文件名
        file_name = os.path.basename(json_file)
        if s3_base_path:
            s3_key = os.path.join(s3_base_path, file_name).replace("\\", "/")  # 处理Windows路径分隔符
        else:
            s3_key = file_name

        # 上传文件
        if upload_file_to_s3(json_file, bucket_name, s3_key):
            success_count += 1
        else:
            fail_count += 1

    # 输出上传总结
    print("\n📊 上传完成")
    print(f"✅ 成功: {success_count} 个文件")
    print(f"❌ 失败: {fail_count} 个文件")


if __name__ == "__main__":
    # 配置参数
    sheet = input("which sheet do you want to upload: 1、order 2、ship 3、cancle 4、return : ")
    if sheet == "1":
        print(1)
        local_json_dir = "/Users/alex/AI邮件解析/request_order"  # 本地JSON文件目录
        bucket = "ecms-user-email-message-dev"  # S3存储桶名称
        s3_base_path = "request/order"  # S3基础路径，所有文件会传到这个路径下
        upload_all_json_to_s3(local_json_dir, bucket, s3_base_path)
    elif sheet == "2":
        local_json_dir = "/Users/alex/AI邮件解析/request_ship"  # 本地JSON文件目录
        bucket = "ecms-user-email-message-dev"  # S3存储桶名称
        s3_base_path = "request/ship"  # S3基础路径，所有文件会传到这个路径下
        upload_all_json_to_s3(local_json_dir, bucket, s3_base_path)
    elif sheet == "3":
        local_json_dir = "/Users/alex/AI邮件解析/request_cancel"  # 本地JSON文件目录
        bucket = "ecms-user-email-message-dev"  # S3存储桶名称
        s3_base_path = "request/cancel"  # S3基础路径，所有文件会传到这个路径下
        upload_all_json_to_s3(local_json_dir, bucket, s3_base_path)
    elif sheet == "4":
        local_json_dir = "/Users/alex/AI邮件解析/request_return"  # 本地JSON文件目录
        bucket = "ecms-user-email-message-dev"  # S3存储桶名称
        s3_base_path = "request/return"  # S3基础路径，所有文件会传到这个路径下
        upload_all_json_to_s3(local_json_dir, bucket, s3_base_path)
    # 执行批量上传
    #upload_all_json_to_s3(local_json_dir, bucket, s3_base_path)