import base64
import hashlib
from Crypto.Cipher import AES

secret_key = 'seel-fetch-email-secret'

def process_key(key: str) -> bytes:
    # 直接处理为256位密钥（32字节）
    return hashlib.sha256(key.encode('utf-8')).digest()
def decode_base64(base64_data: str) -> bytes:
    """
    Decode URL-safe base64 string to bytes, handling padding.
    """
    base64_str = base64_data.replace('-', '+').replace('_', '/')
    padding = len(base64_str) % 4
    if padding == 2:
        base64_str += "=="
    elif padding == 3:
        base64_str += "="
    return base64.b64decode(base64_str)
def symmetric_decrypt_with_base64_decode(key: str, encrypted_value: str) -> str:
    """
    解密并Base64解码
    :param key: 加密密钥
    :param encrypted_value: 十六进制的AES加密字符串
    :return: 解密后的明文字符串
    """
    try:
        key_bytes = process_key(key)
        cipher = AES.new(key_bytes, AES.MODE_ECB)
        # 先将hex字符串转为字节
        encrypted_bytes = bytes.fromhex(encrypted_value)
        decrypted = cipher.decrypt(encrypted_bytes)
        # 去除PKCS7填充
        pad_len = decrypted[-1]
        decrypted = decrypted[:-pad_len]
        # base64解码得到原始内容
        decoded = decode_base64(decrypted.decode('utf-8'))
        return decoded.decode('utf-8')
    except Exception as e:
        # 这里可以用logging模块替换
        print(f"Error during symmetric decryption: {e}")
        return None