from spire.xls import Workbook
from spire.xls.common import ExcelVersion
from spire.xls.core import OleLinkType
from PIL import Image
from io import BytesIO

# 创建一个Workbook对象
workbook = Workbook()
# 通过Workbook.Worksheets(index)属性获取第一个工作表
sheet = workbook.Worksheets[0]
# 使用流将图像保存为PNG格式并获取流对象
img = Image.open('path/to/attachment.png')
buffer = BytesIO()
img.save(buffer, format='PNG')
stream = buffer.getvalue()

# 插入链接型的OLE对象
oleObject = sheet.OleObjects.Add("附件名称.docx", stream, OleLinkType.Link)
# 或者插入嵌入型的OLE对象
# oleObject = sheet.OleObjects.Add("附件名称.docx", stream, OleLinkType.Embed)

# 指定OLE对象的位置
oleObject.Location = "A1"
# 指定OLE对象的类型
oleObject.ObjectType = "Word.Document.12"

# 将更改后的工作簿保存为文件，使用ExcelVersion.Version2016格式
workbook.SaveToFile("Ole对象.xlsx", ExcelVersion.Version2016)