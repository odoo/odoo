# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import datetime,pymssql,random,copy,time

class openshoes(models.Model):
    _name = 'openshoes.openshoes'
    _description = 'openshoes.openshoes'

    c_name = fields.Char('工厂名称')
    price = fields.Float('金额')
    name = fields.Char('负责人')
    date_1 = fields.Date('订单日期')
    type = fields.Selection(selection=[('sample', '样品'), ('development', '开发'), ('production', '批量')], string="测试性质",
                            help="选择", default="sample")
    property_id = fields.One2many('odoo.odoo', 'pltest_id', string='测试列表')




    def sync_assets(self,start_time = None,end_time= None,is_order_time=False):

        # end_time = datetime.datetime.now()
        # offset = datetime.timedelta(days=-2)
        str = "2020-12-17"
        timeArray = time.strptime(str, "%Y-%m-%d")
        end_time = time.strftime("%Y-%m-%d", timeArray)
        str2 = "2020-12-15"
        # 先转换为时间数组,然后转换为其他格式
        timeArray2 = time.strptime(str2, "%Y-%m-%d")
        start_time = time.strftime("%Y-%m-%d", timeArray2)

        # start_time = (end_time + offset).strftime('%Y-%m-%d')
        if not start_time and not end_time :
            start_time = (datetime.datetime.now()-datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            end_time = datetime.datetime.now().strftime("%Y-%m-%d")
        filter_list=[]
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

        sql = f'select  * from stock_move where {where_filter}'.replace('\\','')
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
        print(stock_id)
        stock_dict = {}
        product_id_dict = {}
        for product_id in product_id_list:
            for stock_warehouse in stock_warehouse_1:
                stock_dict[stock_warehouse.lot_stock_id.id] = {
                        'price':0,
                        'qty':0
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
            #出库
            if location_id in stock_id:
                # print("出库："+location_id)
                pass
            else:
                # print("入库：" + str(location_id))
                # print(location_id)
                # print(location_dest_id)

                # print(product_id)
                product_id_dict[product_id][location_dest_id]['price'] = price_unit*product_uom_qty + product_id_dict[product_id][location_dest_id]['price']
                product_id_dict[product_id][location_dest_id]['qty'] = product_uom_qty + product_id_dict[product_id][location_dest_id]['qty']
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
                'price':price,
                'qty':qty
            }
        print(product_warehousing)
        # for product_id in product_id_list:
        #     # product_id = 2517
        #     #当前产品的进出
        #     stock_move_data = self.env['stock.move'].search([('product_id','=',product_id)])
        #     # print(stock_move_data)
        #     # stock_dict = [{stock_warehouse.lot_stock_id.id:0} for stock_warehouse in stock_warehouse_1]
        #
        #     # stock_warehouse_3 = self.env['stock_warehouse'].search([('company_id','=',3)])
        #     print(stock_dict)
        #
        #
        #     new_stock_dict = copy.deepcopy(stock_dict)
        #     print(new_stock_dict)
        #
        #     # product_price = 0
        #     # product_qty = 0
        #
        #     for product in stock_move_data:
        #         # print(product.id)
        #         stock_location_id = product.location_id.id
        #         stock_location_dest_id = product.location_dest_id.id
        #         update_qty = product.product_uom_qty
        #
        #
        #
        #         # print(stock_location_id)
        #         # print(stock_location_dest_id)
        #         # print(update_qty)
        #         if stock_location_id in stock_id:
        #             #出仓库
        #             # print(stock_dict[stock_location_id])
        #             # new_stock_dict[stock_location_id] = new_stock_dict[stock_location_id] - update_qty
        #             # print(stock_dict)
        #             #出仓库的暂时不用管
        #             pass
        #         else:
        #             # 进
        #             # print(stock_dict[stock_location_dest_id])
        #             # 价格暂时没有值取一个5-10随机整数
        #             # price = product.price_unit
        #             price = random.randint(5, 10)
        #             # product_price = product_price + price*update_qty
        #             # product_qty = product_qty + update_qty
        #
        #             new_stock_dict[stock_location_dest_id]['price'] = price*update_qty+new_stock_dict[stock_location_dest_id]['price']
        #             new_stock_dict[stock_location_dest_id]['qty']= update_qty + new_stock_dict[stock_location_dest_id]['qty']
        #             # print(stock_dict)
        #     # price_qty_dict = {
        #     #     'price':product_price,
        #     #     'qty': product_qty
        #     # }
        #     # new_stock_dict[stock_location_id] = price_qty_dict
        #     print(new_stock_dict)
        #     product_id_dict[product_id] = new_stock_dict
        # print(product_id_dict)


    def get_tree_buttons(self):
        return {
            'tree': {
                'buttons': [
                    {
                        'name': 'My Action',
                        'classes': 'oe_link btn btn-primary',
                        'action': 'sync_assets'
                    }
                ]
            }
        }


class odoo(models.Model):
    _name = 'odoo.odoo'
    _description = 'odoo.odoo'

    method = fields.Char('品牌')
    property = fields.Char('111')
    num = fields.Char('数量')
    reqmt = fields.Char('金额')
    pltest_id = fields.Many2one('openshoes.openshoes', string='第二部分')


class TESTProjectShadowWizard(models.TransientModel):
    _name = 'test.project.shadow.wizard'
    _description = '测试'

    date_plan = fields.Date(string='计划日期')
    date_done = fields.Date(string='完成日期')
    employee_id = fields.Many2one('openshoes.openshoes', string='新人', track_visibility='onchange')

    def sync_assets(self):
        print(111)

    @api.model
    def btm_confirm(self):
        pass


class XXWizard(models.TransientModel):
    # 要点1: 使用瞬态模型
    _name = 'xx.wizard'
    _order = 'id asc'

    name = fields.Char('字段名')

    # // 要点2:这些字段在弹窗中由用户赋值

    @api.model
    def default_get(self, default_fields):
        """
        为向导赋默认值。
        """
        result = super(XXWizard, self).default_get(default_fields)

        result.update({
            'name': '你好',
        })
        return result

    @api.model
    def action_XX(self, url):
        """
        向导按钮的点击函数。
        """
        pass
