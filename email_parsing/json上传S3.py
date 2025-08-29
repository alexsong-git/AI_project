import boto3
from botocore.config import Config
import os
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed


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


def upload_all_json_to_s3(local_dir, bucket_name, s3_base_path="", max_workers=5):
    """
    批量上传指定目录下所有JSON和HTML文件到S3存储桶（多线程版）

    参数:
        local_dir: 本地目录路径
        bucket_name: S3存储桶名称
        s3_base_path: S3上的基础路径，所有文件会上传到该路径下
        max_workers: 最大线程数，默认5个
    """
    # 检查本地目录是否存在
    if not os.path.isdir(local_dir):
        print(f"❌ 错误: 本地目录不存在 {local_dir}")
        return

    # 获取目录下所有JSON和HTML文件
    json_files = glob.glob(os.path.join(local_dir, "*.json"))
    html_files = glob.glob(os.path.join(local_dir, "*.html"))
    all_files = json_files + html_files

    if not all_files:
        print(f"ℹ️ 提示: 目录 {local_dir} 下没有找到文件")
        return

    # 准备上传任务
    tasks = []
    for file_path in all_files:
        file_name = os.path.basename(file_path)
        if s3_base_path:
            s3_key = os.path.join(s3_base_path, file_name).replace("\\", "/")
        else:
            s3_key = file_name
        tasks.append((file_path, bucket_name, s3_key))

    # 输出文件数量信息
    if json_files and html_files:
        print(f"📁 发现 {len(json_files)} 个JSON文件和 {len(html_files)} 个HTML文件，开始上传...")
    elif json_files:
        print(f"📁 发现 {len(json_files)} 个JSON文件，开始上传...")
    else:
        print(f"📁 发现 {len(html_files)} 个HTML文件，开始上传...")

    # 多线程上传
    success_count = 0
    fail_count = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(upload_file_to_s3, *task): task for task in tasks}
        for future in as_completed(futures):
            if future.result():
                success_count += 1
            else:
                fail_count += 1

    # 输出上传总结
    print("\n📊 上传完成")
    print(f"✅ 成功: {success_count} 个文件")
    print(f"❌ 失败: {fail_count} 个文件")


if __name__ == "__main__":
    # 配置参数
    sheet = input("1、request_order 2、request_ship 3、request_all 4、html_body_order 5、html_body_ship 6、html_body_all 7、response_order 8、response_ship 9、response_all: ")
    if sheet == "1":
        print(1)
        local_json_dir = "/Users/alex/AI邮件解析/request_order"  # 本地JSON文件目录
        bucket = "seel-email-parsing"  # S3存储桶名称
        s3_base_path = "request/order"  # S3基础路径，所有文件会传到这个路径下
        upload_all_json_to_s3(local_json_dir, bucket, s3_base_path)
    elif sheet == "2":
        local_json_dir = "/Users/alex/AI邮件解析/request_ship"  # 本地JSON文件目录
        bucket = "seel-email-parsing"  # S3存储桶名称
        s3_base_path = "request/ship"  # S3基础路径，所有文件会传到这个路径下
        upload_all_json_to_s3(local_json_dir, bucket, s3_base_path)
    elif sheet == "3":
        local_json_dir = "/Users/alex/AI邮件解析/request_all"  # 本地JSON文件目录
        bucket = "seel-email-parsing"  # S3存储桶名称
        s3_base_path = "request/all"  # S3基础路径，所有文件会传到这个路径下
        upload_all_json_to_s3(local_json_dir, bucket, s3_base_path)
    elif sheet == "4":
        local_json_dir = "/Users/alex/AI邮件解析/html_body_order/"  # 本地JSON文件目录
        bucket = "seel-email-parsing"  # S3存储桶名称
        s3_base_path = "html_body/order"  # S3基础路径，所有文件会传到这个路径下
        upload_all_json_to_s3(local_json_dir, bucket, s3_base_path)
    elif sheet == "5":
        local_json_dir = "/Users/alex/AI邮件解析/html_body_ship"  # 本地JSON文件目录
        bucket = "seel-email-parsing"  # S3存储桶名称
        s3_base_path = "html_body/ship"  # S3基础路径，所有文件会传到这个路径下
        upload_all_json_to_s3(local_json_dir, bucket, s3_base_path)
    elif sheet == "6":
        local_json_dir = "/Users/alex/AI邮件解析/html_body_all"  # 本地JSON文件目录
        bucket = "seel-email-parsing"  # S3存储桶名称
        s3_base_path = "html_body/all"  # S3基础路径，所有文件会传到这个路径下
        upload_all_json_to_s3(local_json_dir, bucket, s3_base_path)
    elif sheet == "7":
        local_json_dir = "/Users/alex/AI邮件解析/response_order"  # 本地JSON文件目录
        bucket = "seel-email-parsing"  # S3存储桶名称
        s3_base_path = "response/order"  # S3基础路径，所有文件会传到这个路径下
        upload_all_json_to_s3(local_json_dir, bucket, s3_base_path)
    elif sheet == "8":
        local_json_dir = "/Users/alex/AI邮件解析/response_ship"  # 本地JSON文件目录
        bucket = "seel-email-parsing"  # S3存储桶名称
        s3_base_path = "response/ship"  # S3基础路径，所有文件会传到这个路径下
        upload_all_json_to_s3(local_json_dir, bucket, s3_base_path)
    elif sheet == "9":
        local_json_dir = "/Users/alex/AI邮件解析/response_all"  # 本地JSON文件目录
        bucket = "seel-email-parsing"  # S3存储桶名称
        s3_base_path = "response/all"  # S3基础路径，所有文件会传到这个路径下
        upload_all_json_to_s3(local_json_dir, bucket, s3_base_path)