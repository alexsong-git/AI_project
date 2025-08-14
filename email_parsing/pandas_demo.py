import pandas
alex = ['a','b','c','d']
path = '/Users/alex/PythonExcelTest.xlsx'
result = pandas.read_excel(path,header=0,sheet_name='Sheet1')

for i, value in enumerate(alex):
    print({value: result['name_1'][i]})