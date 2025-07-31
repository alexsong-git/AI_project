import requests
import json
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed


def call_chat_api(url, payload):
    """调用聊天接口并返回响应结果（复用原函数）"""
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        return {
            "success": True,
            "data": response.json(),
            "payload": payload  # 携带原始请求参数，方便定位问题
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "payload": payload  # 携带原始请求参数，方便定位问题
        }


def process_row(row, api_url):
    """处理单行数据，生成请求参数并调用接口"""
    try:
        # 从行数据中提取字段（根据Excel实际列名调整）
        question = row['question']
        order_number = row['order_number']
        product_title = row['product_title']
        email = row['email']

        # 构造请求参数（复用原payload结构）
        payload = {
            "questionId": f"q-{order_number}",  # 用订单号区分不同请求
            "question": question,
            "conversationHistory": [
                {
                    "question": "I want to return this item...",  # 可根据需求调整
                    "answer": "To assist you with returning..."
                }
            ],
            "orderList": [
                {
                    "order": {
                        "order_number": order_number,
                        "line_items": [{"product_title": product_title}],
                        "customer": {"email": email},
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
        return call_chat_api(api_url, payload)
    except Exception as e:
        return {
            "success": False,
            "error": f"处理行数据失败: {str(e)}",
            "payload": row.to_dict()
        }


if __name__ == "__main__":
    # 配置
    excel_file = "/Users/alex/AI自动化用例.xlsx"  # 你的Excel文件路径
    api_url = "http://localhost:8000/chat"
    max_workers = 5  # 并发线程数（根据接口承受能力调整）

    # 读取Excel所有数据
    df = pd.read_excel(excel_file)
    print(f"共读取到 {len(df)} 条数据，开始批量调用接口...")

    # 使用线程池批量处理
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 为每行数据提交一个任务
        futures = [executor.submit(process_row, row, api_url) for _, row in df.iterrows()]

        # 等待所有任务完成并收集结果
        for future in as_completed(futures):
            results.append(future.result())

    # 处理结果（可根据需求保存到文件或数据库）
    success_count = 0
    fail_count = 0
    for res in results:
        if res["success"]:
            success_count += 1
            print(f"成功 - questionId: {res['payload']['questionId']}")
        else:
            fail_count += 1
            print(f"失败 - 原因: {res['error']}, 数据: {res['payload']}")

    print(f"\n批量调用完成 - 成功: {success_count}, 失败: {fail_count}, 总计: {len(results)}")
