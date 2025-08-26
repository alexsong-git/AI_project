import requests


def test_post_api():
    # 接口地址（请替换为实际的接口URL）
    url = "http://order-email-parser:8080/parse-email"  # 根据实际情况修改，可能需要添加端口或修改协议

    # 请求体数据
    payload = {
        "subject": "Order #1095 confirmed",
        "sender": "store+73212199206@t.shopifyemail.com",
        "content": ""
    }

    try:
        # 发送 POST 请求，设置超时时间为10秒
        response = requests.post(url, json=payload, timeout=10)

        # 打印响应状态码
        print(f"状态码: {response.status_code}")

        # 打印响应内容
        print("响应内容:")
        try:
            # 尝试以 JSON 格式解析响应
            print(response.json())
        except:
            # 如果不是 JSON 格式，直接打印文本
            print(response.text)

    except requests.exceptions.RequestException as e:
        # 捕获所有请求相关的异常
        print(f"请求发生错误: {e}")
        # 特别处理 DNS 解析错误
        if "getaddrinfo" in str(e):
            print("提示: 域名无法解析，请检查域名正确性、网络连接或是否需要指定端口")
        elif "Connection refused" in str(e):
            print("提示: 连接被拒绝，可能是端口错误或服务未启动")


if __name__ == "__main__":
    test_post_api()
