import pymssql
def sqlImportData(self):
    getData = ['订单编号', '客户缩写', '季节标识', '总PO号', '客户款号', '下单日期', '客户要求交期', '装箱配码', '工厂款号',
               '订单号', '件数', '件双数', '总数', 'somxid', 'mxid', 'soid']
    cols = {'订单编号': 'order_numbers', '客户缩写': 'customer_abbreviation', '季节标识': 'season_identification',
            '总PO号': 'po_number',
            '客户款号': 'customer_type_number', '下单日期': 'order_date', '订单类型': 'Order_type', '客户要求交期': 'customer_date',
            '装箱配码': 'packing_code',
            '工厂款号': 'factory_model_number', '订单号': 'order_number', '件数': 'pieces_number',
            '件双数': 'pieces_two_number',
            '总数': 'total', 'somxid': 'somxid', 'soid': 'soid',
            'mxid': 'miid'}

    mainCols = ['order_numbers', 'customer_abbreviation', 'season_identification', 'po_number',
                'customer_type_number', 'order_date', 'customer_date', 'soid']

    salveCols = ['packing_code', 'factory_model_number', 'order_number', 'pieces_number', 'pieces_two_number',
                 'total', 'somxid']

    select = ''
    for i, j in enumerate(getData):
        if i == len(getData) - 1:
            select += j
        else:
            select += j + ','
    print(select)
    connect = pymssql.connect('192.168.88.174', 'sa', 'ad6e78dfj', 'erpdata')
    sql = 'select TOP 3 ' + select + ' from 销售订单明细'
    # sql = 'select TOP 3 * from 销售订单明细'
    # sql = 'select * from 销售订单明细'
    cursor = connect.cursor(as_dict=True)
    # sql = "select getData,客户缩写,季节标识 from 销售订单明细"
    cursor.execute(sql)  # 执行sql语句
    rows = cursor.fetchall()

    for get in getData:
        # print(get)
        for row in rows:
            # row['order_numbers'] = row.pop('订单编号')
            row[cols[get]] = row.pop(get)
    # print(rows)

    salveVals = []
    for i in rows:
        dataRows = {}
        for j in mainCols:
            dataRows[j] = i[j]
        dataRow = {}
        for k in salveCols:
            dataRow[k] = i[k]
        dataRows['factory_data_from_ids'] = [(0, 0, dataRow)]
        # print(dataRows)
        salveVals.append(dataRows)
    print(salveVals)

    print(salveVals[0])