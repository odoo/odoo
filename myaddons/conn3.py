import pymssql
def sqlImportData(self):
    getData = ['�������', '�ͻ���д', '���ڱ�ʶ', '��PO��', '�ͻ����', '�µ�����', '�ͻ�Ҫ����', 'װ������', '�������',
               '������', '����', '��˫��', '����', 'somxid', 'mxid', 'soid']
    cols = {'�������': 'order_numbers', '�ͻ���д': 'customer_abbreviation', '���ڱ�ʶ': 'season_identification',
            '��PO��': 'po_number',
            '�ͻ����': 'customer_type_number', '�µ�����': 'order_date', '��������': 'Order_type', '�ͻ�Ҫ����': 'customer_date',
            'װ������': 'packing_code',
            '�������': 'factory_model_number', '������': 'order_number', '����': 'pieces_number',
            '��˫��': 'pieces_two_number',
            '����': 'total', 'somxid': 'somxid', 'soid': 'soid',
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
    sql = 'select TOP 3 ' + select + ' from ���۶�����ϸ'
    # sql = 'select TOP 3 * from ���۶�����ϸ'
    # sql = 'select * from ���۶�����ϸ'
    cursor = connect.cursor(as_dict=True)
    # sql = "select getData,�ͻ���д,���ڱ�ʶ from ���۶�����ϸ"
    cursor.execute(sql)  # ִ��sql���
    rows = cursor.fetchall()

    for get in getData:
        # print(get)
        for row in rows:
            # row['order_numbers'] = row.pop('�������')
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