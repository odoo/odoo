import pymysql,xlwt

#1������mysql
#2��ִ��sql���
#3����ȡ��sqlִ�н��
#4��д��excel
def conn_mysql(sql):
    conn = pymysql.connect(host='211.149.218.16',user='jxz',password='123456',db='jxz',charset='utf8')
    cur = conn.cursor(cursor=pymysql.cursors.DictCursor)
    cur.execute(sql)
    res = cur.fetchone()
    print(res)
    conn.commit()
    cur.close()
    conn.close()
    return res

def write_excel(file_name,content):
    book = xlwt.Workbook()
    sheet = book.add_sheet('sheet1')
    line_no = 0#��������
    for line in content:
        row = 0#��������
        for j in line:
            sheet.write(line_no,row,j)
            row+=1
        line_no+=1
    book.save(file_name)
res = conn_mysql("insert into jxz_stu  (name,cl,c2,c3) values ('ţ����','��','��','��');")
write_excel('lanxia.xls',res)