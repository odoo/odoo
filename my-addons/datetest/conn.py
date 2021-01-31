# -*- coding: utf-8 -*-
import pymssql
import pandas as pd
def conn():
    connect = pymssql.connect('192.168.88.174', 'sa', 'ad6e78dfj', 'erpdata')
    if connect:
        print("111")
    return connect

def querydb():
    getData = ['订单编号', '客户缩写', '季节标识','客户要求交期']
    cols = {'订单编号':'order_numbers', '客户缩写':'customer_abbreviation', '季节标识':'season_identification', '总PO号':'po_number',
            '客户款号':'customer_type_number','下单日期': 'order_date','订单类型': 'Order_type', '客户要求交期':'customer_date','装箱配码':'packing_code',
            '工厂款号':'factory_model_number', '订单号':'order_number','件数': 'pieces_number','件双数':'pieces_two_number',
            '总数':'total', 'somxid':'somxid', 'soid':'soid'}
    select = ''
    for i,j in enumerate(getData):
        if i == len(getData)-1:
            select += j
        else:
            select += j+','

    print(select)
    sql = 'select '+select+' from 销售订单明细'
    # sql = 'select * from 销售订单明细'
    cursor = conn().cursor(as_dict=True)
    # sql = "select getData,客户缩写,季节标识 from 销售订单明细"
    cursor.execute(sql)  # 执行sql语句
    rows = cursor.fetchall()
    for get in getData:
        print(get)
        for row in rows:
            # row['order_numbers'] = row.pop('订单编号')
            row[cols[get]] = row.pop(get)
    # rows['order_numbers'] = rows.pop('订单编号')
    print(rows)

    cursor.close()
    conn().close()


if __name__ == '__main__':
    conn = querydb()