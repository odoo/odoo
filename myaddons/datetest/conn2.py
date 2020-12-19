# -*- coding: utf-8 -*-
import pymssql,xlwt,xlrd
import pandas as pd
import time,datetime
#1、连接mysql
#2、执行sql语句
#3、获取到sql执行结果
#4、写入excel
def conn_mysql(sql):
    conn = pymssql.connect('192.168.88.174', 'sa', 'ad6e78dfj', 'erpdata')
    cur = conn.cursor()
    cur.execute(sql)
    res = cur.fetchall()
    # print(res)
    conn.commit()
    cur.close()
    conn.close()
    return res

def write_excel(file_name,content):
    book = xlwt.Workbook()
    sheet = book.add_sheet('sheet1')
    line_no = 0#控制行数
    style = xlwt.XFStyle()
    style.num_format_str = 'M/D/YY'
    for line in content:
        row = 0#控制列数

        for j in line:
            sheet.write(line_no, row, j)
            # if row == 5 or row == 7:
            #     print(row)
            #     sheet.write(line_no,row,j,style)
            # else:
            #     # print(row)
            #     sheet.write(line_no,row,j)
            row+=1
        line_no+=1
    book.save(file_name)

def ImportData():
    workBook = xlrd.open_workbook('../../test9.xls')
    # 打开文件

    # 1.获取sheet的名字
    # 1.1 获取所有sheet的名字(list类型)
    allSheetNames = workBook.sheet_names()
    # print(allSheetNames)

    # 1.2 按索引号获取sheet的名字（string类型）
    sheet1Name = workBook.sheet_names()[0]
    # print(sheet1Name)

    # 2. 获取sheet内容
    ## 2.1 法1：按索引号获取sheet内容
    sheet1_content1 = workBook.sheet_by_index(0) # sheet索引从0开始
    ## 2.2 法2：按sheet名字获取sheet内容
    sheet1_content2 = workBook.sheet_by_name(sheet1Name)

    # 3. sheet的名称，行数，列数
    # print(sheet1_content1.name, sheet1_content1.nrows, sheet1_content1.ncols)

    # 4. 获取整行和整列的值（数组）
    rows = sheet1_content1.row_values(10)  # 获取第四行内容
    print(rows[5])
    delta = datetime.timedelta(days=rows[5])
    print(delta)
    today = datetime.datetime.strptime('1899-12-30', '%Y-%m-%d') + delta
    rows[5] = datetime.datetime.strftime(today, '%Y-%m-%d %H:%M:%S')
    # 2015/9/22=42943
    print(today)
    # 将1899-12-30转化为可以计算的时间格式并加上要转化的日期戳
    # today = time.strptime('1899-12-30', '%Y-%m-%d') + delta
    # print(today)
    # today = time.strftime(today, '%Y-%m-%d %H:%M:%S')
    # print(today)
    # 制定输出日期的格式
    # if t == 1:
    #     return
    row = [{'order_numbers':rows[0],'customer_abbreviation':rows[1],'season_identification':rows[2],'po_number':rows[3],'customer_type_number':rows[4],
    }]
    # result = super(FactoryData, self).create(rows)
    # cols = sheet1_content1.col_values(2)  # 获取第三列内容

    # 5. 获取单元格内容(三种方式)
    # print(sheet1_content1.cell(1, 0).value)
    # print(sheet1_content1.cell_value(2, 2))
    # print(sheet1_content1.row(2)[2].value)
    # 6. 获取单元格内容的数据类型
    # Tips: python读取excel中单元格的内容返回的有5种类型 [0 empty,1 string, 2 number, 3 date, 4 boolean, 5 error]
    # print(sheet1_content1.cell(1, 0).ctype)
    # return result
# res = conn_mysql("select * from 销售订单明细;")
# # print(res)
# write_excel('test9.xls',res)
ImportData()