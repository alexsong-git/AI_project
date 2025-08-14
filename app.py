from flask import Flask, render_template, request, jsonify
import os
import json
import requests
import re
import boto3
from botocore.exceptions import ClientError
import logging

app = Flask(__name__)

# 配置
REQUEST_DIR = "/Users/alex/AI邮件解析/request_cancel"
HTML_BODY_DIR = "/Users/alex/AI邮件解析/html_body"
API_URL = "https://internal-api-dev.seel.com/order-email-parser/parse-email"

# S3配置
S3_BUCKET = "ecms-user-email-message-dev"
S3_BASE_PATH = "expect"

# 初始化S3客户端
s3 = boto3.client('s3')

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 存储请求数据
requests_data = []


def extract_request_number(filename):
    """从文件名中提取数字用于排序"""
    match = re.search(r'(\d+)', filename)
    return int(match.group(1)) if match else 0


def get_html_body_path(request_number):
    """获取HTML body文件路径"""
    html_file = f"request_row_{request_number}_cancel.html"
    html_path = os.path.join(HTML_BODY_DIR, html_file)
    return html_path if os.path.exists(html_path) else None


def load_requests_from_files():
    """从文件系统加载所有请求JSON文件并按编号排序"""
    global requests_data
    requests_data = []

    if not os.path.exists(REQUEST_DIR):
        logger.warning(f"请求目录不存在: {REQUEST_DIR}")
        return

    # 获取所有JSON文件并按编号排序
    files = [f for f in os.listdir(REQUEST_DIR) if f.endswith('.json')]
    files.sort(key=extract_request_number)

    for filename in files:
        filepath = os.path.join(REQUEST_DIR, filename)
        try:
            with open(filepath, 'r') as f:
                request_content = json.load(f)
                request_number = extract_request_number(filename)
                html_body_path = get_html_body_path(request_number)

                # 计算HTML文件数量
                html_count = 0
                base_name = os.path.splitext(filename)[0]
                if os.path.exists(HTML_BODY_DIR):
                    html_files = [f for f in os.listdir(HTML_BODY_DIR) if
                                  f.startswith(base_name) and f.endswith('.html')]
                    html_count = len(html_files)

                requests_data.append({
                    'id': len(requests_data) + 1,
                    'number': request_number,
                    'name': filename,
                    'base_name': base_name,
                    'request': request_content,
                    'response': None,
                    'expect': None,
                    'html_body': html_body_path,
                    'has_html': html_count > 0,
                    'html_count': html_count
                })
        except Exception as e:
            logger.error(f"加载文件 {filename} 错误: {str(e)}")


def send_api_request(request_data):
    """发送请求到API端点并获取响应"""
    try:
        response = requests.post(
            API_URL,
            json=request_data,
            headers={'Content-Type': 'application/json'}
        )
        return {
            'status': response.status_code,
            'data': response.json() if response.content else None
        }
    except Exception as e:
        logger.error(f"API请求错误: {str(e)}")
        return {
            'status': 500,
            'error': str(e)
        }


def upload_to_s3(data, request_id, request_name):
    """将数据上传到S3"""
    try:
        # 创建S3键 - 使用请求ID和名称确保唯一性
        base_name = os.path.splitext(request_name)[0]
        s3_key = f"{S3_BASE_PATH}/{base_name}_expectation.json"

        # 转换数据为JSON字符串
        json_data = json.dumps(data, indent=2)

        # 上传到S3
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


@app.route('/api/requests')
def get_requests():
    load_requests_from_files()
    return jsonify([{
        'id': req['id'],
        'number': req['number'],
        'name': req['name'],
        'base_name': req['base_name'],
        'has_html': req['has_html'],
        'html_count': req['html_count']
    } for req in requests_data])


@app.route('/api/request/<int:request_id>')
def get_request_details(request_id):
    for req in requests_data:
        if req['id'] == request_id:
            # 如果还没有获取过响应，则发送请求
            if req['response'] is None:
                api_response = send_api_request(req['request'])
                req['response'] = api_response
                req['expect'] = api_response  # 设置expect与response相同

            return jsonify({
                'id': req['id'],
                'number': req['number'],
                'name': req['name'],
                'request': req['request'],
                'response': req['response'],
                'expect': req['expect'],
                'html_body': req['html_body']
            })
    return jsonify({'error': 'Request not found'}), 404


@app.route('/api/html_body/<int:request_id>')
def get_html_body(request_id):
    for req in requests_data:
        if req['id'] == request_id and req['html_body']:
            try:
                with open(req['html_body'], 'r') as f:
                    return f.read(), 200, {'Content-Type': 'text/html'}
            except Exception as e:
                logger.error(f"读取HTML文件错误: {str(e)}")
                return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'HTML body not found'}), 404


@app.route('/api/html_files/<int:request_id>')
def get_html_files(request_id):
    """获取指定请求对应的所有HTML文件列表"""
    for req in requests_data:
        if req['id'] == request_id:
            base_name = req['base_name']
            # 查找所有匹配的HTML文件
            html_files = []
            if os.path.exists(HTML_BODY_DIR):
                html_files = [f for f in os.listdir(HTML_BODY_DIR)
                              if f.startswith(base_name) and f.endswith('.html')]

            return jsonify({
                'html_files': html_files,
                'base_name': base_name,
                'html_dir': HTML_BODY_DIR
            })
    return jsonify({'error': 'Request not found'}), 404


@app.route('/api/html_body_file/<int:request_id>')
def get_specific_html_file(request_id):
    """获取指定的HTML文件内容"""
    file_name = request.args.get('file')
    if not file_name:
        return jsonify({'error': 'File name required'}), 400

    file_path = os.path.join(HTML_BODY_DIR, file_name)
    # 安全检查，防止路径遍历攻击
    if os.path.exists(file_path) and file_path.startswith(HTML_BODY_DIR):
        try:
            with open(file_path, 'r') as f:
                return f.read(), 200, {'Content-Type': 'text/html'}
        except Exception as e:
            logger.error(f"读取HTML文件错误: {str(e)}")
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'HTML file not found'}), 404


@app.route('/api/update_expect/<int:request_id>', methods=['POST'])
def update_expect(request_id):
    new_expect = request.json.get('expect')

    # 查找请求信息
    request_info = None
    for req in requests_data:
        if req['id'] == request_id:
            request_info = req
            req['expect'] = new_expect
            break

    if not request_info:
        return jsonify({'error': 'Request not found'}), 404

    # 上传到S3
    success, message = upload_to_s3(new_expect, request_id, request_info['name'])

    if success:
        return jsonify({
            'status': 'success',
            'message': f'Saved to S3: {message}'
        })
    else:
        return jsonify({
            'status': 'partial_success',
            'message': f'Saved locally but failed to upload to S3: {message}'
        }), 500


if __name__ == '__main__':
    # 检查S3连接
    try:
        s3.head_bucket(Bucket=S3_BUCKET)
        logger.info(f"成功连接到S3存储桶: {S3_BUCKET}")
    except ClientError as e:
        logger.warning(f"S3存储桶访问检查失败: {str(e)}. 程序将继续运行，但保存到S3可能失败。")
    except Exception as e:
        logger.warning(f"S3初始化错误: {str(e)}. 程序将继续运行，但保存到S3可能失败。")

    app.run(host='0.0.0.0', port=5000, debug=True)
