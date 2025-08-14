import requests
import json
import pandas as pd


def call_chat_api(url, payload):
    """
    调用聊天接口并返回响应结果

    参数:
        url (str): 接口URL
        payload (dict): 请求负载数据

    返回:
        dict: 接口响应的JSON数据，如果请求失败则返回None
    """
    try:
        # 设置请求头
        headers = {
            'Content-Type': 'application/json'
        }

        # 发送POST请求
        response = requests.post(url, headers=headers, data=json.dumps(payload))

        # 检查响应状态码
        response.raise_for_status()  # 如果状态码不是200，会抛出HTTPError异常

        # 返回解析后的JSON数据
        return response.json()

    except requests.exceptions.HTTPError as e:
        print(f"HTTP错误: {e}")
    except requests.exceptions.ConnectionError:
        print("连接错误: 无法连接到服务器")
    except requests.exceptions.Timeout:
        print("超时错误: 连接服务器超时")
    except requests.exceptions.RequestException as e:
        print(f"请求异常: {e}")
    except json.JSONDecodeError:
        print("解析错误: 无法解析响应为JSON")

    return None


if __name__ == "__main__":
    # 从Excel文件读取数据
    # 请将此处的文件名替换为你的Excel文件路径
    excel_file = "/Users/alex/AI自动化用例.xlsx"
    df = pd.read_excel(excel_file)

    # 从Excel中获取变量值（取第一行数据）
    question = df.iloc[0]['question']
    order_number = df.iloc[0]['order_number']
    product_title = df.iloc[0]['product_title']
    email = df.iloc[0]['email']

    # 接口URL
    api_url = "http://localhost:8000/chat"

    # 请求数据
    payload = {
        "questionId": "q-0000",
        "question": question,  # 使用从Excel读取的question
        "conversationHistory": [
            {
                "question": "I want to return this item, its condition is great,but I just don't like it. I don't have any specified request for return process.",
                "answer": "To assist you with returning the Women's adidas GRAND COURT 2.0 SHOES, I'll guide you through the return process based on Shop Simon's return policy.\n\n### Return Process Overview:\n1. **Eligibility**: The item must be unused and in its original packaging. Since you mentioned the condition is great, it should be eligible for return.\n2. **Return Window**: Ensure the return is initiated within 30 days of receipt.\n3. **Return Shipping Fee**: A $4.95 return shipping fee will be deducted from your refund.\n4. **Return Method**: Returns are processed through Shop Simon's return portal.\n\n### Next Steps:\nWould you like me to submit the return request for you through Shop Simon's return portal? If you confirm, I'll proceed with the submission."
            }
        ],
        "orderList": [
            {
                "order": {
                    "order_number": order_number,  # 使用从Excel读取的order_number
                    "line_items": [
                        {
                            "product_title": product_title  # 使用从Excel读取的product_title
                        }
                    ],
                    "customer": {
                        "email": email  # 使用从Excel读取的email
                    },
                    "shipping_address": {
                        "address_1": "555 West 42nd Street",
                        "city": "New York",
                        "state": "NY",
                        "zipcode": "10001",
                        "country": "US"
                    }
                },
                "store": {
                    "domain": "s-fashionicon.myshopify.com",
                    "storeName": "s-fashionicon",
                    "returnPolicyUrl": "https://sfashionicon.aftership.com/returns/return-policy",
                    "returnPortalUrl": "https://sfashionicon.aftership.com/returns?returns_page_access=granted",
                    "returnEmail": "songyuchen.alex@gmail.com",
                    "returnPolicy": "",
                    "isReturnViaEmail": False
                }
            }
        ]
    }

    # 调用接口
    print("正在调用聊天接口...")
    result = call_chat_api(api_url, payload)

    # 处理响应结果
    if result:
        print("\n接口调用成功，响应结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("\n接口调用失败")
