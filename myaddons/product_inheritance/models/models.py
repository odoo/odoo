# -*- coding: utf-8 -*-

from odoo import models, fields, api
import datetime,copy,random,time
#
class stock_month(models.Model):
    _name = 'stock_month.stock_month'
    _description = 'stock_month.stock_month'
    product = fields.Char('产品id')
    price = fields.Float('总和价格')
    month_unit_price =  fields.Float('月单价')
    qty = fields.Integer('总数量')
    warehouse = fields.Integer('仓库位置')
    month = fields.Char('月份')

    def sync_assets(self, start_time=None, end_time=None, is_order_time=False):

        str = "2020-12-17"
        timeArray = time.strptime(str, "%Y-%m-%d")
        end_time = time.strftime("%Y-%m-%d", timeArray)
        str2 = "2020-12-15"
        # 先转换为时间数组,然后转换为其他格式
        timeArray2 = time.strptime(str2, "%Y-%m-%d")
        start_time = time.strftime("%Y-%m-%d", timeArray2)

        # start_time = (end_time + offset).strftime('%Y-%m-%d')
        if not start_time and not end_time:
            start_time = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            end_time = datetime.datetime.now().strftime("%Y-%m-%d")
        filter_list = []
        if is_order_time:
            if start_time:
                filter_list.append(f"date >= '{start_time}'")
            if end_time:
                filter_list.append(f"date<='{end_time}'")
        else:
            if start_time:
                filter_list.append(f"date >= '{start_time}'")
            if end_time:
                filter_list.append(f"date<='{end_time}'")

        where_filter = ' And '.join(filter_list)

        sql = f'select  * from stock_move where {where_filter}'.replace('\\', '')
        print(sql)
        self.env.cr.execute(sql)  # 执行SQL语句
        dicts = self.env.cr.dictfetchall()  # 获取SQL的查询结果
        print(dicts[0])
        product_id_list = [dict['product_id'] for dict in dicts]
        product_id_list = list(set(product_id_list))
        print(product_id_list)
        print(len(product_id_list))
        # 公司1
        stock_warehouse_1 = self.env['stock.warehouse'].search([('company_id', '=', 1)])
        # 公司1拥有的仓库id
        print(stock_warehouse_1)
        stock_id = [stock_warehouse.lot_stock_id.id for stock_warehouse in stock_warehouse_1]
        stock_id = [8,35]
        print(stock_id)
        stock_dict = {}
        product_id_dict = {}
        for product_id in product_id_list:
            for stock_warehouse in stock_warehouse_1:
                stock_dict[stock_warehouse.lot_stock_id.id] = {
                    'price': 0,
                    'qty': 0
                }
            product_id_dict[product_id] = copy.deepcopy(stock_dict)
        print(stock_dict)
        print(product_id_dict)
        print(stock_id)
        print(len(dicts))
        for dict in dicts:
            location_id = dict['location_id']
            location_dest_id = dict['location_dest_id']
            product_uom_qty = dict['product_uom_qty']
            price_unit = random.randint(5, 10)
            product_id = dict['product_id']
            # print(product_id)
            # 出库
            if location_id in stock_id:
                # print("出库："+location_id)
                pass
            else:
                # print("入库：" + str(location_id))
                # print(location_id)
                # print(location_dest_id)

                # print(product_id)
                product_id_dict[product_id][location_dest_id]['price'] = price_unit * product_uom_qty + \
                                                                         product_id_dict[product_id][location_dest_id][
                                                                             'price']
                product_id_dict[product_id][location_dest_id]['qty'] = product_uom_qty + \
                                                                       product_id_dict[product_id][location_dest_id][
                                                                           'qty']
        print(product_id_dict)
        product_warehousing = {}
        for product_key in product_id_dict:
            print(product_key)
            price = 0
            qty = 0
            print(product_id_dict[product_key])
            for product_info_key in product_id_dict[product_key]:
                price = product_id_dict[product_key][product_info_key]['price'] + price
                qty = product_id_dict[product_key][product_info_key]['qty'] + qty
            product_warehousing[product_key] = {
                'price': price,
                'qty': qty
            }
        print(product_warehousing)

