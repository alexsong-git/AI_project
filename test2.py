import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime

# API请求配置 - 基于最新curl参数
API_URL = "https://api-dev.seel.com/controller/resolution-center/orderservice/morningstar/cash/withdraw"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Referer': 'https://morning-star-dev.seel.com/',
    'Content-Type': 'application/json',
    'Authorization': 'Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIyMDI1MDcyOTE0MDg3ODIwNjM0MDMyOTEiLCJpYXQiOjE3NTc2NTQxNTUsImV4cCI6MTc1NzY1Nzc1NX0.CQUlPI_0dnq6Xh7CBnilL5bam_zQMr_Ksol26Xlg8yk',
    'X-Device-Type': 'web',
    'X-Device-Id': 'd687e08b-ad04-4494-90cb-ffbc12003943',
    'Origin': 'https://morning-star-dev.seel.com',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site'
}


# 请求数据
def get_payload(amount):
    return {
        "currency": "USD",
        "amount": amount,
        "payAccountDTO": {
            "paymentMethod": "paypal",
            "payPalAccountDTO": {
                "email": "sb-43tqjq22158798@personal.example.com"
            }
        }
    }


# 发送单个请求
def send_request(index, amount):
    try:
        payload = get_payload(amount)
        # 记录请求发起时间
        start_datetime = datetime.now()
        start_time = time.time()
        # 打印发起信息
        print(f"请求 {index} (金额: {amount}) 发起于: {start_datetime.strftime('%H:%M:%S.%f')[:-3]}")

        response = requests.post(
            API_URL,
            headers=HEADERS,
            data=json.dumps(payload),
            timeout=10
        )

        end_time = time.time()
        return {
            "index": index,
            "amount": amount,
            "status": "success",
            "status_code": response.status_code,
            "start_time": start_datetime.strftime('%H:%M:%S.%f')[:-3],
            "response_time": end_time - start_time,
            "response_text": response.text
        }
    except Exception as e:
        return {
            "index": index,
            "amount": amount,
            "status": "failed",
            "start_time": datetime.now().strftime('%H:%M:%S.%f')[:-3],
            "error": str(e)
        }


# 多线程发送请求 - 发送5个不同金额的请求
def send_concurrent_requests():
    MAX_WORKERS = 5  # 固定线程数为5
    amounts = [10, 20, 30, 40, 50]  # 指定的金额列表
    num_requests = len(amounts)

    print(f"===== 开始执行 =====")
    print(f"总请求数: {num_requests}, 并发线程数: {MAX_WORKERS}")
    print(f"请求金额分别为: {amounts}")
    print(f"开始时间: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}\n")

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 提交所有任务，每个任务使用不同的金额
        futures = [executor.submit(send_request, i, amounts[i]) for i in range(num_requests)]

        # 处理结果
        results = []
        print("\n===== 响应结果 =====")
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            if result["status"] == "success":
                print(f"请求 {result['index']} (金额: {result['amount']}) 完成 - 状态码: {result['status_code']}, "
                      f"发起于: {result['start_time']}, "
                      f"耗时: {result['response_time']:.2f}秒")
            else:
                print(
                    f"请求 {result['index']} (金额: {result['amount']}) 失败 - 发起于: {result['start_time']}, 错误: {result['error']}")

    end_time = time.time()
    total_time = end_time - start_time

    # 统计结果
    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = num_requests - success_count

    print("\n===== 执行结果统计 =====")
    print(f"总请求数: {num_requests}")
    print(f"成功数: {success_count}")
    print(f"失败数: {failed_count}")
    print(f"总耗时: {total_time:.2f}秒")
    if success_count > 0:
        print(
            f"平均响应时间: {sum(r['response_time'] for r in results if r['status'] == 'success') / success_count:.2f}秒")

    return results


if __name__ == "__main__":
    results = send_concurrent_requests()

    with open("amounts_requests_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n详细结果已保存到 amounts_requests_results.json 文件")
