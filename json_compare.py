import pandas as pd
import json
import sys
from typing import Dict, Any, List


def load_excel_file(file_path: str, sheet_name: str = 'Sheet1') -> pd.DataFrame:
    """加载Excel文件并返回指定工作表的数据"""
    try:
        return pd.read_excel(file_path, sheet_name=sheet_name)
    except FileNotFoundError:
        print(f"错误: 文件 '{file_path}' 不存在")
        sys.exit(1)
    except Exception as e:
        print(f"加载Excel文件时出错: {str(e)}")
        sys.exit(1)


def parse_json_safely(json_str: str) -> Dict[str, Any]:
    """安全地解析JSON字符串，处理可能的解析错误"""
    try:
        # 移除可能导致解析错误的多余空白字符
        json_str = json_str.strip()
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {str(e)}")
        print(f"有问题的JSON字符串: {json_str[:100]}...")  # 只显示前100个字符
        return {}
    except Exception as e:
        print(f"处理JSON时出错: {str(e)}")
        return {}


def find_json_differences(json1: Dict[str, Any], json2: Dict[str, Any]) -> List[str]:
    """找出两个JSON对象之间不同的字段名"""
    differences = []

    # 检查所有在第一个JSON中存在的键
    for key in json1:
        if key not in json2:
            differences.append(f"字段 '{key}' 仅存在于response中")
        else:
            # 如果值都是字典，递归检查
            if isinstance(json1[key], dict) and isinstance(json2[key], dict):
                sub_diff = find_json_differences(json1[key], json2[key])
                # 为子字段添加父字段前缀
                differences.extend([f"{key}.{sub}" for sub in sub_diff])
            elif json1[key] != json2[key]:
                differences.append(f"字段 '{key}' 值不同")

    # 检查所有在第二个JSON中存在但第一个中不存在的键
    for key in json2:
        if key not in json1:
            differences.append(f"字段 '{key}' 仅存在于expect中")

    return differences


def compare_columns(file_path: str) -> None:
    """对比Excel文件中的第五列和第六列，并输出差异"""
    # 加载Excel数据
    df = load_excel_file(file_path)

    # 检查列数是否足够
    if len(df.columns) < 6:
        print("错误: Excel文件至少需要包含6列数据")
        sys.exit(1)

    # 获取第五列和第六列（索引从0开始，所以是4和5）
    col5_name = df.columns[4]  # response列
    col6_name = df.columns[5]  # expect列

    print(f"开始对比 {col5_name} 列和 {col6_name} 列...\n")

    # 遍历每一行进行对比
    for index, row in df.iterrows():
        print(f"第 {index + 1} 行:")

        # 解析JSON数据
        json1 = parse_json_safely(str(row[col5_name]))
        json2 = parse_json_safely(str(row[col6_name]))

        # 查找差异
        differences = find_json_differences(json1, json2)

        if not differences:
            print("  两列内容完全相同，没有差异")
        else:
            print(f"  发现 {len(differences)} 处差异:")
            for diff in differences:
                print(f"  - {diff}")

        print()  # 空行分隔不同行的结果


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python compare_excel_columns.py <Excel文件路径>")
        print("示例: python compare_excel_columns.py /mnt/AI邮件解析自动化.xlsx")
        sys.exit(1)

    excel_path = sys.argv[1]
    compare_columns(excel_path)
