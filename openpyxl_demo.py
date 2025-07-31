from openpyxl import load_workbook
path = '/Users/alex/PythonExcelTest.xlsx'
alex = ['a','b','c','d']
# 加载 Excel 文件
result = load_workbook(path)


dada = result.active


a = [i.value for i in dada[1]]
print(a)
