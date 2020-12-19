# -*- coding: utf-8 -*-

from odoo import models, fields, api
import datetime,copy,random,time
from dateutil.relativedelta import relativedelta

class month_search(models.Model):
    _name = 'month_search.month_search'
    _description = 'month_search.month_search'

    product = fields.Char('产品id')
    price = fields.Float('总和价格')
    month_unit_price = fields.Float('月单价')
    qty = fields.Integer('总数量')
    warehouse = fields.Integer('仓库位置')
    month = fields.Char('月份')


    def sync_assets(self, start_time=None, end_time=None, is_order_time=False):

        current_month = (datetime.date.today()).month
        last_month = (datetime.date.today() - relativedelta(months=+1)).month
        # month = (datetime.datetime(2020, 1, 23) - relativedelta(months=+1)).month
        print(last_month)
        # last_month_data = self.env['month_search.month_search'].search([('month', '=', last_month)])
        print(last_month)
        sql = f"select  * from month_search_month_search where month='{last_month}'"
        print(sql)
        self.env.cr.execute(sql)  # 执行SQL语句
        last_month_data = self.env.cr.dictfetchall()  # 获取SQL的查询结果
        print(last_month_data)
        print(len(last_month_data))

        end_time = datetime.datetime(2020,12,17)
        start_time = datetime.datetime(2020,12,15)

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

        sql = f"select  * from stock_move where {where_filter} and state='done'".replace('\\', '')
        print(sql)
        # print(sql)
        self.env.cr.execute(sql)  # 执行SQL语句
        dicts = self.env.cr.dictfetchall()  # 获取SQL的查询结果
        # print(dicts[0])
        product_id_list = [dict['product_id'] for dict in dicts]
        product_id_list = list(set(product_id_list))
        # print(product_id_list)
        # print(len(product_id_list))
        # 公司1
        stock_warehouse_1 = self.env['stock.warehouse'].search([('company_id', '=', 1)])
        # 公司1拥有的仓库id
        # print(stock_warehouse_1)
        stock_id = [stock_warehouse.lot_stock_id.id for stock_warehouse in stock_warehouse_1]
        print(stock_id)
        # stock_id = [8,35,16]
        stock_id = stock_id
        stock_dict = {}
        product_id_dict = {}
        for product_id in product_id_list:
            for stock in stock_id:
                stock_dict[stock] = {
                    'price': 0,
                    'qty': 0
                }
            # product_id_dict[product_id] = stock_dict
            product_id_dict[product_id] = copy.deepcopy(stock_dict)
        # print(stock_dict)
        # print(product_id_dict)
        # print(stock_id)
        # print(len(dicts))
        for dict in dicts:
            location_id = dict['location_id']
            location_dest_id = dict['location_dest_id']
            product_uom_qty = dict['product_uom_qty']
            # price_unit = random.randint(5, 10)
            price_unit = dict['price_unit']
            product_id = dict['product_id']
            # print(product_id)
            # 出库
            if location_dest_id in stock_id:
                #入库
                product_id_dict[product_id][location_dest_id]['price'] = price_unit * product_uom_qty + \
                                                                         product_id_dict[product_id][location_dest_id][
                                                                             'price']
                product_id_dict[product_id][location_dest_id]['qty'] = product_uom_qty + \
                                                                       product_id_dict[product_id][location_dest_id][
                                                                           'qty']
            else:
                pass

            # if location_id in stock_id:
            #     # print("出库："+location_id)
            #     pass
            # elif location_dest_id in stock_id:
            #     # print("入库：" + str(location_id))
            #     # print(location_id)
            #     # print(location_dest_id)
            #
            #     # print(product_id)
            #     product_id_dict[product_id][location_dest_id]['price'] = price_unit * product_uom_qty + product_id_dict[product_id][location_dest_id][
            #                                                                  'price']
            #     product_id_dict[product_id][location_dest_id]['qty'] = product_uom_qty + product_id_dict[product_id][location_dest_id][
            #                                                                'qty']
        # print(product_id_dict)
        product_warehousing = []
        for product_key in product_id_dict:
            # print(product_key)
            price = 0
            qty = 0
            # print(product_id_dict[product_key])
            for product_info_key in product_id_dict[product_key]:
                price = product_id_dict[product_key][product_info_key]['price'] + price
                qty = product_id_dict[product_key][product_info_key]['qty'] + qty
            try:
                month_unit_price = price/qty
            except ZeroDivisionError:  # 'ZeroDivisionError'除数等于0的报错方式
                month_unit_price = 0
            product_dict = {
                'product':product_key,
                'price': price,
                'qty': qty,
                'month_unit_price':month_unit_price,
                'month':current_month
            }
            product_warehousing.append(product_dict)
        print(product_warehousing)
        # self.env['month_search.month_search'].create(product_warehousing)




        for current_data in product_warehousing:
            current_product = current_data['product']
            current_price = current_data['price']
            current_qty = current_data['qty']
            # print(current_product)
            # 如果有相同的产品，则进行计算   总价格相加/数量相加 更新当前单价
            for last_data in last_month_data:
                last_data_product = int(last_data['product'])
                if current_product==last_data_product:

                    last_data_price = last_data['price']
                    last_data_qty = last_data['qty']
                    update_price = last_data_price + current_price
                    update_qty = current_qty + last_data_qty
                    try:
                        update_month_unit_price = update_price/update_qty
                    except ZeroDivisionError:  # 'ZeroDivisionError'除数等于0的报错方式
                        update_month_unit_price = 0
                    current_data['price'] = update_price
                    current_data['qty'] = update_qty
                    current_data['month_unit_price'] = update_month_unit_price
                    # print(current_product)
                    # print(update_month_unit_price)
        # print("第二个")
        print(product_warehousing)

