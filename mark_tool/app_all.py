from flask import Flask, render_template, request, jsonify
import os
import json
import re
import boto3
from botocore.exceptions import ClientError
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

app = Flask(__name__)

# 配置 - 移除本地路径，使用S3路径
API_URL = "https://internal-api-dev.seel.com/order-email-parser/parse-email"  # 保留但不使用

# S3配置
S3_BUCKET = "seel-email-parsing"
S3_BASE_PATH = "expect/all"
S3_RESPONSE_PATH = "response/all"  # response存储路径
S3_HTML_BODY_PATH = "html_body/all"  # html body存储路径

# 初始化S3客户端
s3 = boto3.client('s3')

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 存储请求数据
requests_data = []

# 增加线程锁保护全局变量
requests_lock = threading.Lock()


def extract_request_number(filename):
    """从文件名中提取数字用于排序"""
    match = re.search(r'(\d+)', filename)
    return int(match.group(1)) if match else 0


def extract_base_identifier(filename):
    """从文件名中提取基础标识符用于匹配response和htmlbody"""
    # 匹配模式: 提取类似"all_row2"的基础标识符
    match = re.search(r'(all_row\d+)', filename)
    return match.group(1) if match else None


"""def clean_filtered_data(data):
    if isinstance(data, dict):
        cleaned = {}
        for key, value in data.items():
            if isinstance(value, str) and (
                    '[图片数据已隐藏]' in value or
                    '[Base64图片数据已隐藏]' in value or
                    '[图片已隐藏]' in value
            ):
                # 跳过被过滤的字段，让它们从原始数据中获取
                continue
            elif isinstance(value, (dict, list)):
                cleaned_value = clean_filtered_data(value)
                if cleaned_value is not None:  # 只有在清理后有内容时才添加
                    cleaned[key] = cleaned_value
            else:
                cleaned[key] = value
        return cleaned if cleaned else None
    elif isinstance(data, list):
        cleaned = []
        for item in data:
            cleaned_item = clean_filtered_data(item)
            if cleaned_item is not None:
                cleaned.append(cleaned_item)
        return cleaned if cleaned else None
    else:
        return data"""


def merge_data_with_original(original, filtered):
    """将清理后的数据与原始数据合并，保持修改但恢复被过滤的字段"""
    if isinstance(original, dict) and isinstance(filtered, dict):
        merged = original.copy()
        for key, value in filtered.items():
            if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
                merged[key] = merge_data_with_original(merged[key], value)
            elif isinstance(value, list) and key in merged and isinstance(merged[key], list):
                # 对于列表，尝试按索引合并
                merged_list = merged[key].copy()
                for i, item in enumerate(value):
                    if i < len(merged_list):
                        if isinstance(item, dict) and isinstance(merged_list[i], dict):
                            merged_list[i] = merge_data_with_original(merged_list[i], item)
                        else:
                            merged_list[i] = item
                merged[key] = merged_list
            else:
                merged[key] = value
        return merged
    else:
        return filtered if filtered is not None else original

def process_response_file(key, html_files_by_identifier, expectation_keys):
    """处理单个response文件的线程任务"""
    try:
        filename = os.path.basename(key)
        base_identifier = extract_base_identifier(filename)
        if not base_identifier:
            logger.warning(f"无法从文件名 {filename} 中提取基础标识符，跳过处理")
            return None

        # 下载response内容
        s3_response = s3.get_object(Bucket=S3_BUCKET, Key=key)
        request_content = json.loads(s3_response['Body'].read().decode('utf-8'))

        # 匹配html文件
        matched_html_files = html_files_by_identifier.get(base_identifier, [])
        html_count = len(matched_html_files)
        main_html_path = matched_html_files[0] if html_count > 0 else None

        # 处理expectation文件
        expect_data = request_content
        has_expectation_file = False
        expect_key = f"{S3_BASE_PATH}/expectation_{os.path.splitext(filename)[0]}.json"

        if expect_key in expectation_keys:
            try:
                s3_expect = s3.get_object(Bucket=S3_BUCKET, Key=expect_key)
                raw_expect_data = json.loads(s3_expect['Body'].read().decode('utf-8'))
                has_expectation_file = True
                expect_data = raw_expect_data
                logger.info(f"已加载 {filename} 的expectation文件")
            except Exception as e:
                logger.error(f"处理 {filename} 的expectation文件错误: {str(e)}")

        return {
            'number': extract_request_number(filename),
            'identifier': base_identifier,
            'name': filename,
            'base_name': os.path.splitext(filename)[0],
            'request': request_content,
            'response': request_content,
            'expect': expect_data,
            'html_body': main_html_path,
            'has_html': html_count > 0,
            'html_count': html_count,
            'html_files': matched_html_files,
            'has_expectation_file': has_expectation_file
        }
    except Exception as e:
        logger.error(f"加载S3文件 {key} 错误: {str(e)}")
        return None

def load_requests_from_files():
    """从S3加载所有response并匹配对应的html文件，使用多线程优化加载速度"""
    global requests_data
    requests_data = []

    try:
        # 1. 批量获取所有expectation文件的key（使用分页）
        expectation_keys = set()
        try:
            paginator = s3.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=f"{S3_BASE_PATH}/expectation_")
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        if obj['Key'].endswith('.json'):
                            expectation_keys.add(obj['Key'])
            logger.info(f"成功加载 {len(expectation_keys)} 个expectation文件路径")
        except Exception as e:
            logger.error(f"获取expectation文件列表错误: {str(e)}")

        # 2. 获取所有response文件（使用分页查询）
        response_files = []
        continuation_token = None

        while True:
            # 构建请求参数，包含分页令牌（如果有的话）
            list_kwargs = {
                'Bucket': S3_BUCKET,
                'Prefix': S3_RESPONSE_PATH
            }
            if continuation_token:
                list_kwargs['ContinuationToken'] = continuation_token

            # 调用S3 API
            response = s3.list_objects_v2(**list_kwargs)

            # 处理当前页的文件
            if 'Contents' in response:
                page_files = [obj['Key'] for obj in response['Contents'] if obj['Key'].endswith('.json')]
                response_files.extend(page_files)
                logger.info(f"已加载 {len(response_files)} 个response文件（当前页: {len(page_files)}）")

            # 检查是否有更多数据
            if not response.get('IsTruncated', False):
                break

            # 获取下一页的令牌
            continuation_token = response.get('NextContinuationToken')
            if not continuation_token:
                break

        # 对所有获取到的文件按编号排序
        response_files.sort(key=lambda x: extract_request_number(os.path.basename(x)))
        logger.info(f"共加载 {len(response_files)} 个response文件")

        # 3. 获取所有html文件（使用分页查询）
        html_files_by_identifier = {}
        continuation_token = None

        while True:
            list_kwargs = {
                'Bucket': S3_BUCKET,
                'Prefix': S3_HTML_BODY_PATH
            }
            if continuation_token:
                list_kwargs['ContinuationToken'] = continuation_token

            html_response = s3.list_objects_v2(**list_kwargs)

            if 'Contents' in html_response:
                page_html_files = [obj['Key'] for obj in html_response['Contents'] if obj['Key'].endswith('.html')]
                for html_key in page_html_files:
                    html_filename = os.path.basename(html_key)
                    identifier = extract_base_identifier(html_filename)
                    if identifier:
                        html_files_by_identifier[identifier] = html_files_by_identifier.get(identifier, []) + [html_key]
                logger.info(f"已加载 {len(html_files_by_identifier)} 个html文件组（当前页: {len(page_html_files)}）")

            if not html_response.get('IsTruncated', False):
                break

            continuation_token = html_response.get('NextContinuationToken')
            if not continuation_token:
                break

        # 4. 多线程处理response文件（保持不变）
        max_workers = min(32, len(response_files))  # 限制最大线程数，避免请求过于密集
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            futures = [
                executor.submit(
                    process_response_file,
                    key,
                    html_files_by_identifier,
                    expectation_keys
                ) for key in response_files
            ]

            # 收集结果
            results = []
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)

            # 按number排序并添加id
            results.sort(key=lambda x: x['number'])
            with requests_lock:
                requests_data = [
                    {**item, 'id': i + 1}
                    for i, item in enumerate(results)
                ]

    except ClientError as e:
        logger.error(f"S3访问错误: {str(e)}")
    except Exception as e:
        logger.error(f"加载S3文件列表错误: {str(e)}")


def upload_to_s3(data, request_id, request_name):
    """将数据上传到S3（保持不变）"""
    try:
        base_name = os.path.splitext(request_name)[0]
        s3_key = f"{S3_BASE_PATH}/expectation_{base_name}.json"

        json_data = json.dumps(data, indent=2)

        s3.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=json_data,
            ContentType='application/json'
        )

        logger.info(f"成功上传到S3: {s3_key}")
        return True, s3_key
    except ClientError as e:
        logger.error(f"S3上传错误: {str(e)}")
        return False, str(e)
    except Exception as e:
        logger.error(f"上传过程错误: {str(e)}")
        return False, str(e)


@app.route('/')
def index():
    return render_template('index.html')


def has_content_differences(response_data, expectation_data):
    """比较response和expectation的内容是否有差异"""
    try:
        # 使用深度比较
        return response_data != expectation_data
    except Exception as e:
        logger.error(f"比较JSON内容错误: {str(e)}")
        return False


@app.route('/api/requests')
def get_requests():
    load_requests_from_files()
    return jsonify([{
        'id': req['id'],
        'number': req['number'],  # 恢复返回编号
        'identifier': req['identifier'],
        'name': req['name'],
        'base_name': req['base_name'],
        'has_html': req['has_html'],
        'html_count': req['html_count'],
        'has_expectation_file': req['has_expectation_file'],  # 添加expectation文件存在标识
        'has_modifications': req['has_expectation_file'] and has_content_differences(req['response'], req['expect'])
        # 有expectation文件且内容有差异
    } for req in requests_data])


@app.route('/api/request/<int:request_id>')
def get_request_details(request_id):
    for req in requests_data:
        if req['id'] == request_id:
            return jsonify({
                'id': req['id'],
                'response': req['response'],  # 直接返回原始数据
                'expect': req['expect']  # 直接返回原始数据
            })
    return jsonify({'error': 'Request not found'}), 404


@app.route('/api/html_body/<int:request_id>')
def get_html_body(request_id):
    for req in requests_data:
        if req['id'] == request_id and req['html_body']:
            try:
                # 从S3获取HTML内容
                s3_response = s3.get_object(Bucket=S3_BUCKET, Key=req['html_body'])
                html_content = s3_response['Body'].read().decode('utf-8')
                return html_content, 200, {'Content-Type': 'text/html'}
            except ClientError as e:
                logger.error(f"S3读取HTML错误: {str(e)}")
                return jsonify({'error': str(e)}), 500
            except Exception as e:
                logger.error(f"读取HTML内容错误: {str(e)}")
                return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'HTML body not found'}), 404


@app.route('/api/html_files/<int:request_id>')
def get_html_files(request_id):
    """获取指定请求对应的所有HTML文件列表"""
    for req in requests_data:
        if req['id'] == request_id:
            # 返回所有匹配的HTML文件名
            html_files = [os.path.basename(path) for path in req['html_files']]

            return jsonify({
                'html_files': html_files,
                'base_name': req['base_name'],
                'html_dir': S3_HTML_BODY_PATH
            })
    return jsonify({'error': 'Request not found'}), 404


@app.route('/api/html_body_file/<int:request_id>')
def get_specific_html_file(request_id):
    """获取指定的HTML文件内容"""
    file_name = request.args.get('file')
    if not file_name:
        return jsonify({'error': 'File name required'}), 400

    # 构造S3键
    s3_key = f"{S3_HTML_BODY_PATH}/{file_name}"
    try:
        # 从S3获取文件
        s3_response = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
        html_content = s3_response['Body'].read().decode('utf-8')
        return html_content, 200, {'Content-Type': 'text/html'}
    except ClientError as e:
        logger.error(f"S3读取指定HTML错误: {str(e)}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        logger.error(f"读取指定HTML内容错误: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/reset_expect/<int:request_id>', methods=['POST'])
def reset_expect(request_id):
    """删除expectation文件，恢复为未标注状态"""
    request_info = None
    for req in requests_data:
        if req['id'] == request_id:
            request_info = req
            break

    if not request_info:
        return jsonify({'error': 'Request not found'}), 404

    try:
        # 删除S3中的expectation文件
        expect_key = f"{S3_BASE_PATH}/expectation_{request_info['base_name']}.json"
        s3.delete_object(Bucket=S3_BUCKET, Key=expect_key)

        # 更新内存中的数据
        original_data = request_info['response']
        request_info['expect'] = original_data
        request_info['has_expectation_file'] = False

        logger.info(f"已删除expectation文件: {expect_key}")

        return jsonify({
            'status': 'success',
            'message': f'已删除expectation文件，恢复为未标注状态',
            'expect': original_data
        })

    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            # 文件本来就不存在
            original_data = request_info['response']
            request_info['expect'] = original_data
            request_info['has_expectation_file'] = False

            return jsonify({
                'status': 'success',
                'message': 'expectation文件本来就不存在，已恢复为未标注状态',
                'expect': original_data
            })
        else:
            logger.error(f"删除expectation文件错误: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'删除expectation文件失败: {str(e)}'
            }), 500
    except Exception as e:
        logger.error(f"重置expectation错误: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'重置失败: {str(e)}'
        }), 500


@app.route('/api/update_expect/<int:request_id>', methods=['POST'])
def update_expect(request_id):
    # 保持原有逻辑不变
    new_expect = request.json.get('expect')

    request_info = None
    for req in requests_data:
        if req['id'] == request_id:
            request_info = req
            req['expect'] = new_expect
            break

    if not request_info:
        return jsonify({'error': 'Request not found'}), 404

    success, message = upload_to_s3(new_expect, request_id, request_info['name'])

    if success:
        # 保存成功后，标记为有expectation文件
        request_info['has_expectation_file'] = True
        return jsonify({
            'status': 'success',
            'message': f'Saved to S3: {message}'
        })
    else:
        # 即使S3保存失败，本地已保存，也标记为有expectation文件
        request_info['has_expectation_file'] = True
        return jsonify({
            'status': 'partial_success',
            'message': f'Saved locally but failed to upload to S3: {message}'
        }), 500


if __name__ == '__main__':
    # 检查S3连接（保持不变）
    try:
        s3.head_bucket(Bucket=S3_BUCKET)
        logger.info(f"成功连接到S3存储桶: {S3_BUCKET}")
    except ClientError as e:
        logger.warning(f"S3存储桶访问检查失败: {str(e)}. 程序将继续运行，但保存到S3可能失败。")
    except Exception as e:
        logger.warning(f"S3初始化错误: {str(e)}. 程序将继续运行，但保存到S3可能失败。")

    app.run(host='0.0.0.0', port=5000, debug=True)
