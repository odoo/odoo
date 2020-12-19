# -*- coding: utf-8 -*-

from odoo import models, fields, api
import pymssql, xlwt, xlrd, datetime
from functools import total_ordering
from functools import reduce


@total_ordering
class FactoryData(models.Model):
    _name = 'factory.data'
    _description = 'factory data'
    _rec_name = 'order_numbers'

    # def __eq__(self, other):
    #     print("__eq__")
    #     return ((self.order_numbers) == (other.order_numbers))
    #
    # def __gt__(self, other):
    #     print("__gt__")
    #     return ((self.order_numbers) > (other.order_numbers))
    # def  __and__(self, other):
    #     print('__and__')
    #     super(FactoryData, self).__and__(other)
    #
    # def default_name(self):
    #     super(FactoryData, self).default_name()

    order_numbers = fields.Char(string="订单编号", required=True, index=True)
    customer_abbreviation = fields.Char(string="客户缩写")
    season_identification = fields.Char(string="季节标识")
    po_number = fields.Text(string="总PO号")
    customer_type_number = fields.Char(string="客户款号")
    order_date = fields.Date(string="下单日期")
    # Order_type = fields.Char(string="订单类型")
    customer_date = fields.Date(string="客户要求交期")
    status = fields.Char(string="比对状态")
    soid = fields.Char(string="soid")
    factory_data_from_ids = fields.One2many('factory.data.from', 'factory_data_id', '订单明细')

    # @api.constrains('somxid')
    # def _check_description(self):
    #     for record in self:
    #         if record.somxid == record.description:
    #             raise ValidationError("Fields name and description must be different")
    @api.constrains('status')
    def _check_description(self):
        for record in self:
            if record.status == '更新':
                pass

                # raise ValidationError("Fields name and description must be different")

    def down_ex(self):
        print(self)
        file_name = '100' + '.xls'
        print(file_name)
        print(file_name)
        sql = "select * from 销售订单明细"
        conn = pymssql.connect('192.168.88.174', 'sa', 'ad6e78dfj', 'erpdata')
        cur = conn.cursor()
        cur.execute(sql)
        res = cur.fetchall()
        print(res)
        conn.commit()
        cur.close()
        conn.close()
        book = xlwt.Workbook()
        sheet = book.add_sheet('sheet1')
        line_no = 0  # 控制行数
        for line in res:
            row = 0  # 控制列数
            for j in line:
                sheet.write(line_no, row, j)
                row += 1
            line_no += 1
        book.save(file_name)

    @api.model
    def ImportData(self):
        workBook = xlrd.open_workbook('test9.xls')
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
        sheet1_content1 = workBook.sheet_by_index(0)  # sheet索引从0开始
        ## 2.2 法2：按sheet名字获取sheet内容
        sheet1_content2 = workBook.sheet_by_name(sheet1Name)
        # 3. sheet的名称，行数，列数
        print(sheet1_content1.name, sheet1_content1.nrows, sheet1_content1.ncols)
        # column = sheet1_content1.nrows
        # data = sheet1_content1.row_values(sheet1_content1.nrows, start_colx=0, end_colx=None)
        # print(data)
        # 4. 获取整行和整列的值（数组）
        row1 = sheet1_content1.row_values(0)
        rowDict = {}
        for i, j in enumerate(row1):
            rowDict[j] = i
            # print(i,j)
        # print(rowDict['order_numbers'])
        # print(row1)
        # cols = ['order_numbers','customer_abbreviation','season_identification','po_number',
        #         'customer_type_number','order_date','Order_type','customer_date','packing_code',
        #         'factory_model_number','order_number','pieces_number','pieces_two_number',
        #         'total','somxid','soid']

        mainCols = ['order_numbers', 'customer_abbreviation', 'season_identification', 'po_number',
                    'customer_type_number', 'order_date', 'customer_date', 'soid']

        salveCols = ['packing_code', 'factory_model_number', 'order_number', 'pieces_number', 'pieces_two_number',
                     'total', 'somxid']

        dateCols = ['order_date', 'customer_date']

        dataRows = []
        salveVals = []
        for rows in range(1, sheet1_content1.nrows):
            # print(rows)
            row = sheet1_content1.row_values(rows)
            # print(row[5])
            for i in dateCols:
                index = rowDict[i]
                delta = datetime.timedelta(days=row[index])
                today = datetime.datetime.strptime('1899-12-30', '%Y-%m-%d') + delta
                row[index] = datetime.datetime.strftime(today, '%Y-%m-%d %H:%M:%S')
            dataRow = {}
            for i in mainCols:
                dataRow[i] = row[rowDict[i]]
            dataRows.append(dataRow)

            mxRow = {}
            for i in salveCols:
                mxRow[i] = row[rowDict[i]]
            dataRow['factory_data_from_ids'] = [(0, 0, mxRow)]

            # many2many
            #
            # (0, 0, {values})
            # 根据values里面的信息新建一个记录。
            #
            # (1, ID, {values})
            # 更新id = ID的记录（写入values里面的数据）
            #
            # (2, ID)
            # 删除id = ID的数据（调用unlink方法，删除数据以及整个主从数据链接关系）
            #
            # (3, ID)
            # 切断主从数据的链接关系但是不删除这个数据
            #
            # (4, ID)
            # 为id = ID的数据添加主从链接关系。
            #
            # (5)
            # 删除所有的从数据的链接关系就是向所有的从数据调用(3, ID)
            #
            # (6, 0, [IDs])
            # 用IDs里面的记录替换原来的记录（就是先执行(5)
            # 再执行循环IDs执行（4, ID））
            #
            # 例子[(6, 0, [8, 5, 6, 4])]
            # 设置
            # many2many
            # to
            # ids[8, 5, 6, 4]
            #
            # one2many
            #
            # (0, 0, {values})
            # 根据values里面的信息新建一个记录。
            #
            # (1, ID, {values})
            # 更新id = ID的记录（对id = ID的执行write
            # 写入values里面的数据）
            #
            # (2, ID)
            # 删除id = ID的数据（调用unlink方法，删除数据以及整个主从数据链接关系）
            # row = [{"order_numbers":row[rowDict['order_numbers']],row1[1]:row[1],row1[2]:row[2],row1[3]:row[3],row1[0]:row[4],
            #         'order_date':row[5]
            # }]
            # result = super(FactoryData, self).create(rows)
        # dataRows['factory_data_from_ids'] = (0, 0, salveVals)
        super(FactoryData, self).create(dataRows)

        # cols = sheet1_content1.col_values(2)  # 获取第三列内容

        # 5. 获取单元格内容(三种方式)
        # print(sheet1_content1.cell(1, 0).value)
        # print(sheet1_content1.cell_value(2, 2))
        # print(sheet1_content1.row(2)[2].value)
        # 6. 获取单元格内容的数据类型
        # Tips: python读取excel中单元格的内容返回的有5种类型 [0 empty,1 string, 2 number, 3 date, 4 boolean, 5 error]
        # print(sheet1_content1.cell(1, 0).ctype)

    @api.model
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
                'mxid': 'mxid'}


        mainCols = ['order_numbers', 'customer_abbreviation', 'season_identification', 'po_number',
                    'customer_type_number', 'order_date', 'customer_date', 'soid']

        salveCols = ['packing_code', 'factory_model_number', 'order_number', 'pieces_number', 'pieces_two_number',
                     'total', 'somxid', 'mxid']

        select = ''
        #转换成查询数据库语句需要的格式
        for i, j in enumerate(getData):
            if i == len(getData) - 1:
                select += j
            else:
                select += j + ','

        connect = pymssql.connect('192.168.88.174', 'sa', 'ad6e78dfj', 'erpdata')
        sql = 'select TOP 5000 * from 销售订单明细'
        # sql = "select  * from 销售订单明细 where 订单编号  = '211707280089'"

        cursor = connect.cursor(as_dict=True)

        cursor.execute(sql)  # 执行sql语句
        rows = cursor.fetchall()
        # 获取需要操作的数据
        order_numbers_list = []
        # 将数据库中，中文字段更改为英文字段
        for row in rows:
            # print(row)
            order_numbers_list.append(row['订单编号'])
            for col in cols:
                # print(col)
                row[cols[col]] =  row.pop(col)
        mainOrderList = []
        # 主表模型数据插入
        for i in rows:
            mainorderDict = {}
            for j in mainCols:
                mainorderDict[j] = i[j]
            mainorderDict['factory_data_from_ids'] = []
            mainOrderList.append(mainorderDict)

        # 需要存入主表的order_numbers数据
        sql = "select order_numbers from factory_data"
        self.env.cr.execute(sql)  # 执行SQL语句
        dicts = self.env.cr.fetchall()  # 获取SQL的查询结果
        # 获取数据库中已存在的number

        dicts_list = [i[0] for i in dicts ]

        # 需要更新的订单编号
        updateOrderNumbers = set(order_numbers_list) & set(dicts_list)
        #直接插入的订单编号
        insertOrderNumbers = set(order_numbers_list) | set(dicts_list)
        #主表数据去重
        filter_function = lambda x, y: x if y in x else x + [y]
        mainOrderList = reduce(filter_function, [[], ] + mainOrderList)

        # importRowDict = {}
        #
        # for row in rows:
        #     orderNo = row['订单编号']
        #     if orderNo in importRowDict.keys():
        #         orderItems = importRowDict[orderNo]
        #         orderItems.append(row)
        #     else:
        #         importRowDict[orderNo] = [row]
        #
        # rows2list = list(importRowDict.keys())
        # existRows = self.env['factory.data'].search([('order_numbers', 'in', rows2list)])
        # orderNumbers = existRows.mapped('order_numbers')
        # updateOrderNumbers = set(rows2list) & set(orderNumbers)
        #
        # dataRows = []
        # for key in rows2list:
        #     if key in orderNumbers:
        #         continue
        #     dataRow = {}
        #     rs = importRowDict[key][0]
        #     for col in mainCols:
        #         dataRow[col] = rs[reversedCols[col]]
        #
        #     mxItems = []
        #     for importRow in importRowDict[key]:
        #         mxRow = {}
        #         for col in salveCols:
        #             mxRow[col] = importRow[salveColMap[col]]
        #         mxItems.append((0, 0, mxRow))
        #     dataRow['factory_data_from_ids'] = mxItems
        #     dataRows.append(dataRow)
        #
        # super(FactoryData, self).create(dataRows)



        # updDataRows = []
        # for orderNo in updateOrderNumbers:
        #     updDataRow = {}
        #     rs = importRowDict[orderNo][0]
        #     for col in mainCols:
        #         updDataRow[col] = rs[reversedCols[col]]
        #     updDataRows.append(updDataRow)
        #     super(FactoryData, self).write(updDataRow)

        # 增加从表数据字段
        for i in rows:
            ciOrderList = {}
            for k in salveCols:

                ciOrderList[k] = i[k]

            for j in mainOrderList:

                if j['order_numbers'] == i['order_numbers']:
                    j['factory_data_from_ids'].append((0, 0, ciOrderList))
        # 开始更新，新增，删除操作
        for i in mainOrderList:
            # 2
            if i['order_numbers'] in updateOrderNumbers:
                existRows = self.env['factory.data'].search([('order_numbers', '=', i['order_numbers'])])
                id = existRows.id
                # 明细数量
                orderNumbers = existRows.mapped('factory_data_from_ids')
                # print(orderNumbers)
                mxid_list = []
                factory_mxid_list = []
                for orderNumber in orderNumbers:
                    # 数据库查询出来两条明细
                    mxid = orderNumber.mxid
                    mxid_list.append(mxid)
                for factory_data_from_id in i['factory_data_from_ids']:
                    factory_mxid_list.append(factory_data_from_id[2]['mxid'])


                inserts = list(set(factory_mxid_list) - set(mxid_list))
                updates = list(set(mxid_list) & set(factory_mxid_list))
                deletes = list(set(mxid_list) - set(factory_mxid_list))

                for factory_data_from_id in i['factory_data_from_ids']:
                    if factory_data_from_id[2]['mxid'] in updates:
                        factory_data_from_id[2]['factory_data_id'] = id
                        factory_data_from_id[2]['mxstatus'] = '更新'
                        from_update = self.env['factory.data.from'].search(
                            [('mxid', '=', factory_data_from_id[2]['mxid'])])
                        from_update.write(factory_data_from_id[2])
                    if factory_data_from_id[2]['mxid'] in inserts:
                        factory_data_from_id[2]['factory_data_id'] = id
                        factory_data_from_id[2]['mxstatus'] = '新增'
                        self.env['factory.data.from'].sudo().create(factory_data_from_id[2])
                #删除
                if deletes:
                    from_deletes = self.env['factory.data.from'].search([('mxid', 'in', deletes)])
                    for from_delete in from_deletes:
                        from_delete.mxstatus = '删除'
                        # from_delete.unlink()

            else:
                super(FactoryData, self).create(i)
                print('直接插入')
    def test(self):
        print(111)
    def test2(self):
        print(222)


class FactoryDataFrom(models.Model):
    _name = 'factory.data.from'
    _description = 'factory data from'

    packing_code = fields.Char(string="装箱配码")
    factory_model_number = fields.Char(string="工厂款号")
    order_number = fields.Char(string="订单号")
    pieces_number = fields.Integer(string="件数")
    pieces_two_number = fields.Integer(string="件双数")
    total = fields.Integer(string="总数")
    somxid = fields.Integer(string="源订单明细ID")
    mxstatus = fields.Char(string="明细比对状态")
    mxid = fields.Char(string="明细ID")
    factory_data_id = fields.Many2one('factory.data')
