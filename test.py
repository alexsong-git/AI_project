import boto3
from botocore.config import Config

s3 = boto3.client('s3', config=Config(signature_version='s3v4'))
url = s3.generate_presigned_url(
    'get_object',
    Params={
        'Bucket': 'ecms-user-email-message-dev',
        'Key': '0000000000000000000000000/agent.dev2@seel.com/2025-07-30/19859582b8675ddd/htmlBody',
        'ResponseContentType': 'text/html'  # 强制浏览器渲染为HTML
    },
    ExpiresIn=3600
)



print(url)  # 输出可直接打开的临时链接

