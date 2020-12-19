# -*- coding: utf-8 -*-

from odoo import models, fields, api
import pymssql
import hashlib
import psycopg2
import datetime
import time

#订单继承修改模块
from odoo.exceptions import ValidationError


class order_inheritance(models.Model):
    _inherit = 'sale.order'
    # order_numbers = fields.Char(string="订单编号", required=True, index=True)
    #name == 订单编号
    #partner == 客户全称
    #利用更新日期

    old_order_number = fields.Char(string="订单编号")
    order_size_seg = fields.Char(string="下单码段")
    season_identify = fields.Char(string="季节标识")

    discount_oder = fields.Boolean(string="促销订单")
    sync_state = fields.Char(string="同步状态")
    customer_po = fields.Char(string="客户PO号")
    main_compare_id = fields.Char(string="主表比较id")
    jh_date = fields.Char(string="交货日期")
    # 客户PO号就是订单号




    def order_import_data(self,start_time = None,end_time= None,is_order_time=False):
        #time   days
        if not start_time and not end_time :
            start_time = (datetime.datetime.now()-datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            end_time = datetime.datetime.now().strftime("%Y-%m-%d")
        filter_list=[]
        if is_order_time:
            if start_time:
               filter_list.append(f"更新日期 >= '{start_time}'")
            if end_time:
               filter_list.append(f"更新日期<='{end_time}'")
        else:
            if start_time:
               filter_list.append(f"下单日期 >= '{start_time}'")
            if end_time:
               filter_list.append(f"下单日期<='{end_time}'")

        where_filter = ' And '.join(filter_list)
        connect = pymssql.connect('192.168.88.180', 'Pghcs6KcvXWS3t', 'ac@#F%tISqc1fSz9', 'erpdata')

        sql = f'select TOP 10  * from odoo_订单主表查询 where {where_filter}'.replace('\\','')
        print(sql)
        cursor = connect.cursor(as_dict=True)
        cursor.execute(sql)  # 执行sql语句
        zb_rows = cursor.fetchall()

        order_name_list = []
        sale_order_dict ={}
        customer_list=[]
        for zb_row in zb_rows:
            order_no = zb_row['订单编号']
            sale_order_dict[order_no] = zb_row
            kh_name = zb_row['客户全称']
            if kh_name not in customer_list:
                customer_list.append(kh_name)

        exist_customer_models = self.env['res.partner']. search_read([('name', 'in', customer_list)],['id','name'])
        print(exist_customer_models)
        customer_name_dicts ={}
        for exist_customer_model in exist_customer_models:
            name = exist_customer_model['name']
            id = exist_customer_model['id']
            customer_name_dicts[name] = id


            #order_name_list.append(zb_row['订单编号'])
        #需要不重复的订单编号
        # order_name_list = list(set(order_name_list))
        order_name_list = list(sale_order_dict.keys())
        print(order_name_list)
        print('order_name_list:'+str(len(order_name_list)))



        # update_all_order_name_list = ['s3008','s3008','s3008']
        # update_all_order_name_list = order_name_list
        order_name_list  = str(order_name_list).replace('[','(').replace(']',')')
        sql2 = f'select  * from odoo_订单明细分组查询 where 订单编号 in {order_name_list}'
        cursor = connect.cursor(as_dict=True)
        cursor.execute(sql2)  # 执行sql语句
        mx_fz_rows = cursor.fetchall()
        # print(mx_fz_rows)
        # print(len(mx_fz_rows))
        # 明细分组查询订单号列表
        # mx_fz_order_number_list = []
        # for mx_fz_row in mx_fz_rows:
        #     mx_fz_order_number_list.append(mx_fz_row['订单号'])
        # print('mx_fz_order_number_list:'+str(len(mx_fz_order_number_list)))
        # print(mx_fz_order_number_list)


        # order_name_list = str(order_name_list).replace('[', '(').replace(']', ')')
        sql3 = f'select  * from odoo_订单明细查询 where 订单编号 in {order_name_list}'
        cursor = connect.cursor(as_dict=True)
        cursor.execute(sql3)  # 执行sql语句
        mx_rows = cursor.fetchall()
        print(mx_rows[0])
        product_names = []
        for mx_row in mx_rows:
            product_name = mx_row['工厂款号']
            if product_name not in product_names:
                product_names.append(product_name)
            md5 = hashlib.md5()
            md5_str = str(mx_row['订单编号'])+str(mx_row['订单号'])+str(mx_row['装箱配码'])+str(mx_row['工厂款号'])
            md5.update(md5_str.encode("utf-8"))
            # print(md5.hexdigest())
            mx_row['mxid'] = md5.hexdigest()
            order_no = mx_row['订单编号']
            customer_po = mx_row['订单号']

        exist_product_models = self.env['product.product'].search_read([('name', 'in', product_names)], ['id','name','uom_id'])
        product_name_dicts = {}
        for exist_product_model in exist_product_models:
            name = exist_product_model['name']
            product_name_dicts[name] = exist_product_model

        print('mx_rows:'+str(len(mx_rows)))

        mx_fz_row_compare_ids = []

        for mx_fz_row in mx_fz_rows:
            md5 = hashlib.md5()
            md5_str = str(mx_fz_row['订单编号']) + str(mx_fz_row['订单号'])+str(mx_fz_row['装箱配码'])
            md5.update(md5_str.encode("utf-8"))
            md5_val = md5.hexdigest()
            mx_fz_row['main_compare_id'] = md5_val
            mx_fz_row_compare_ids.append(md5_val)


        exist_order_lists = self.env['sale.order'].search([('main_compare_id', 'in', mx_fz_row_compare_ids)])
        exist_comp_ids = exist_order_lists.mapped("main_compare_id")
        update_order_data_list = []
        create_order_data_list = []

        for mx_fz_row in mx_fz_rows:
            comp_id = mx_fz_row['main_compare_id']
            if comp_id in exist_comp_ids:

                exist_comp_id_order = self.env['sale.order'].search([('main_compare_id', '=', comp_id)])

                main_order_lines = exist_comp_id_order.mapped('order_line')
                #数据库已存在明细id

                main_order_lines_mxid = main_order_lines.mapped('mxid')
                # print(main_order_lines_mxid)
                name = mx_fz_row['订单编号']
                customer_po = mx_fz_row['订单号']
                pack_method = mx_fz_row['装箱配码']
                src_sale_order = sale_order_dict[name]
                customer_name = src_sale_order['客户全称']
                # exist_order_lines = filter(lambda r: r['订单编号'] == name and r['订单号'] == customer_po, mx_rows)
                exist_order_lines =[]
                for mx_row in mx_rows:
                    if mx_row['订单编号'] == name and mx_row['订单号'] == customer_po and mx_row['装箱配码'] == pack_method:
                        exist_order_lines.append(mx_row)
                #需要操作的明细id
                sql_order_lines_mxid =[exist_order_line['mxid'] for exist_order_line in exist_order_lines]

                inserts = list(set(sql_order_lines_mxid) - set(main_order_lines_mxid))
                updates = list(set(sql_order_lines_mxid) & set(main_order_lines_mxid))
                update_mxid_list = self.env['sale.order.line'].search([('mxid', 'in', updates)])
                deletes = list(set(main_order_lines_mxid) - set(sql_order_lines_mxid))

                order_lines = []
                for exist_order_line in exist_order_lines:
                    # print(exist_order_line)
                    exist_mxid =  exist_order_line['mxid']
                    aa = product_name_dicts[exist_order_line['工厂款号']]["uom_id"]
                    order_line = {
                        'order_type': exist_order_line['订单类型'],
                        'pack_method': exist_order_line['装箱配码'],
                        'pieces': exist_order_line['件数'],
                        'pieces_pairs': exist_order_line['件双数'],
                        'factory_date': exist_order_line['工厂交期'],
                        'mxid': exist_order_line['mxid'],
                        'name': exist_order_line['工厂款号'],
                        'product_id': product_name_dicts[exist_order_line['工厂款号']]["id"],
                        'product_uom': aa[0],
                        'product_uom_qty': exist_order_line['数量'],
                        'pre_dept': exist_order_line['预排部门'],
                        'pre_line': exist_order_line['预排线别'],
                        'prod_dept': exist_order_line['生产部门'],
                        'prod_line': exist_order_line['生产线别'],
                        'batch_no': exist_order_line['批次号'],
                        'lc_no': exist_order_line['轮次号'],
                        'plan_started_date': exist_order_line['计划上线'],
                        'plan_finished_date': exist_order_line['计划完成'],
                    }
                    if exist_mxid in inserts:
                        order_line['mx_sync_state'] = '新增'
                        order_lines.append((0, 0, order_line))

                    if exist_mxid in updates:
                        mx_update = update_mxid_list.filtered(lambda x: x.mxid == exist_mxid)
                        order_line['mx_sync_state'] = '更新'
                        id = mx_update.id
                        order_lines.append((1, id, order_line))
                    if exist_mxid in deletes:
                        mx_delete = update_mxid_list.filtered(lambda x: x.mxid == exist_mxid)
                        mx_delete.mx_sync_state = '删除'

                order_dict = {
                    'company_id': self.env.user.company_id.id,
                    # 'name': name,
                    'old_order_number': name,
                    'discount_oder': src_sale_order['促销订单'],
                    'order_size_seg': src_sale_order['下单码段'],
                    'season_identify': src_sale_order['季节标识'],
                    'sync_state': '更新',
                    'customer_po': customer_po,
                    'partner_id': customer_name_dicts[customer_name],
                    'main_compare_id': comp_id,
                    # 'commitment_date': mx_fz_row['客户交期'],
                    'jh_date': mx_fz_row['客户交期'],
                    'order_line': order_lines
                }

                exist_comp_id_order.write(order_dict)



            else:
                name = mx_fz_row['订单编号']
                customer_po = mx_fz_row['订单号']
                pack_method = mx_fz_row['装箱配码']
                src_sale_order = sale_order_dict[name]
                customer_name = src_sale_order['客户全称']

                exist_order_lines = filter(lambda r: r['订单编号'] == name and r['订单号'] == customer_po and r['装箱配码'] == pack_method , mx_rows)
                order_lines =[]
                for exist_order_line in exist_order_lines:
                    aa = product_name_dicts[exist_order_line['工厂款号']]["uom_id"]
                    order_line={
                        'order_type':exist_order_line['订单类型'],
                        'pack_method':exist_order_line['装箱配码'],
                        'pieces':exist_order_line['件数'],
                        'pieces_pairs':exist_order_line['件双数'],
                        'mx_sync_state':'新增',
                        'factory_date':exist_order_line['工厂交期'],
                        'mxid':exist_order_line['mxid'],
                        'name': exist_order_line['工厂款号'],
                        'product_id':product_name_dicts[exist_order_line['工厂款号']]["id"],
                        'product_uom':aa[0],
                        'product_uom_qty':exist_order_line['数量'],
                        'pre_dept':exist_order_line['预排部门'],
                        'pre_line':exist_order_line['预排线别'],
                        'prod_dept':exist_order_line['生产部门'],
                        'prod_line':exist_order_line['生产线别'],
                        'batch_no':exist_order_line['批次号'],
                        'lc_no':exist_order_line['轮次号'],
                        'plan_started_date':exist_order_line['计划上线'],
                        'plan_finished_date':exist_order_line['计划完成'],

                    }
                    order_lines.append((0,0,order_line))
                order_dict = {
                    'old_order_number':name,
                    'company_id':self.env.user.company_id.id,
                    # 'name': name,
                    'discount_oder': src_sale_order['促销订单'],
                    'order_size_seg': src_sale_order['下单码段'],
                    'season_identify': src_sale_order['季节标识'],
                    'sync_state': '新增',
                    'customer_po': customer_po,
                    'partner_id': customer_name_dicts[customer_name],
                    'main_compare_id':comp_id,
                    # 'commitment_date':mx_fz_row['客户交期'],
                    'jh_date': mx_fz_row['客户交期'],
                    'order_line': order_lines
                }
                create_order_data_list.append(order_dict)
        return_data_list = super(order_inheritance, self).create(create_order_data_list)
        # print(return_data.name)
        #确定订单的S0
        order_number_list =[]
        for return_data in return_data_list:
            print(return_data.name)
            order_number_list.append(return_data.name)
            return_data.action_confirm()
        purchase_list = self.env['purchase.order'].search([('origin', 'in', order_number_list)])
        for purchase in purchase_list:
            purchase.button_confirm()
                # zb_rows[name]




        # 数据库中订单名列表
        data_order_name_list = []
        # 数据库中订单列表
        data_order_list = []
        for dx_data_order in exist_order_lists:
            exist_order_lists.mapped("main_compare_id")







        # name
        # partner_id
        # order_size_seg
        # season_identification
        # discount_oder
        # sync_state
        # customer_po



    # 筛选条件函数
    def set_search_criteria(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'search.criteria',
            # 'limit':1,
            'name': '自定义查询',
            'multi': True,
            'auto_refresh': 1,
            # 'view_type': 'form',
            # 设置过滤条件search_default_+所需判断的字段名
            # 'context': {'ids': i},
            'view_mode': 'form',
            # 'view_id': 'search.criteria.',
            # 'res_id':orde.id,
            # 'views': [(True, "tree")],
            'target': 'new',
            'auto_search': True,
        }



cols = {'订单编号': 'order_numbers', '客户缩写': 'customer_abbreviation', '季节标识': 'season_identification',
                '总PO号': 'po_number',
                '客户款号': 'customer_type_number', '下单日期': 'order_date', '订单类型': 'Order_type', '客户要求交期': 'customer_date',
                '装箱配码': 'packing_code',
                '工厂款号': 'factory_model_number', '订单号': 'order_number', '件数': 'pieces_number',
                '件双数': 'pieces_two_number',
                '总数': 'total', 'somxid': 'somxid', 'soid': 'soid',
                'mxid': 'mxid'}

#明细订单继承修改模块
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'


    order_type  =fields.Char('订单类型')
    pack_method  =fields.Char('装箱配码')
    pieces  =fields.Integer('件数')
    pieces_pairs  =fields.Integer('件双数')
    mx_sync_state  =fields.Char('明细同步状态')
    factory_date  =fields.Date('工厂交期')
    mxid = fields.Char('明细id')

    pre_dept = fields.Char("预排部门")
    pre_line = fields.Char("预排线别")
    prod_dept = fields.Char("生产部门")
    prod_line = fields.Char("生产线别")
    batch_no = fields.Char("批次号")
    lc_no = fields.Char("轮次号")
    plan_started_date = fields.Date("计划上线")
    plan_finished_date = fields.Date("计划完成")

    #mx_sync_state = md5(订单编号+订单号+装箱配码)
    @api.onchange('pieces_pairs')
    def onchange_responsible_person(self):
        pieces = self.pieces
        pieces_pairs = self.pieces_pairs
        if pieces and pieces_pairs:
            self.product_uom_qty = pieces*pieces_pairs


#客户继承修改模块
class customer_inheritance(models.Model):

    _inherit = 'res.partner'

    def set_search_criteria(self):
        pass

    def customer_import_data(self):
        print(self)
        print(self.env.user.company_id.id)
        print(self.env.context)
        print(self.env.context['allowed_company_ids'])
        connect = pymssql.connect('192.168.88.180', 'Pghcs6KcvXWS3t', 'ac@#F%tISqc1fSz9', 'erpdata')
        sql = 'select  客户全称 from odoo_客户名称查询'
        # sql = "select  * from 销售订单明细 where 订单编号  = '211707280089'"
        cursor = connect.cursor(as_dict=True)
        cursor.execute(sql)  # 执行sql语句
        rows = cursor.fetchall()
        # print(rows)
        rowsList = []
        #is_company
        #f是个人
        #t是公司
        #rupplier_rank默认为0，1则是供应商
        #customer_rank默认为0，1则是客户
        for index,row in enumerate(rows):
            existRows = self.env['res.partner'].search([('name', '=', row['客户全称'])])
            if existRows:
                update_rowDict = {
                    'company_id': self.env.user.company_id.id,
                     'is_company':'t',
                    'customer_rank':1
                }
                existRows.write(update_rowDict)
            else:
                create_rowDict = {
                    'company_id':self.env.user.company_id.id,
                    'name':row['客户全称'],
                    'is_company':'t',
                    'customer_rank':1,
                }
                rowsList.append(create_rowDict)

        super(customer_inheritance, self).create(rowsList)
        # print(rows)

# 产品继承修改模块
class product_inheritance(models.Model):

    _inherit = 'product.template'
    color_en = fields.Char("配色_en")
    color_cn = fields.Char("配色_cn")
    customer_number = fields.Char("客户款号")
    trademark = fields.Char("商标")




    def product_import_data(self):

        sql = 'SELECT  * FROM odoo_工厂款号查询'
        conn = pymssql.connect('192.168.88.180', 'Pghcs6KcvXWS3t', 'ac@#F%tISqc1fSz9', 'erpdata')
        cur = conn.cursor(as_dict=True)
        cur.execute(sql)  # 执行语句
        res = cur.fetchall()
        res1 = self.env['product.category'].search([])
        res2 = self.env['uom.uom'].search([])
        rowsList = []
        for data in res:
            existRows = self.env['product.template'].search([('name', '=', data['工厂款号'])])
            if existRows:
                update_rowDict = {
                    'color_cn': data['配色Cn'],
                    'color_en': data['配色En'],
                    'customer_number': data['客户款号'],
                    # 'uom_id': res2.filtered(lambda r: r.name == data['单位']).id,
                    # 'uom_po_id': res2.filtered(lambda r: r.name == data['单位']).id,
                    'categ_id': res1.filtered(lambda r: r.name == data['鞋码标准']).id,
                    'trademark': data['商标'],
                    'route_ids': [(6,0,[1,8] )],
                }
                existRows.write(update_rowDict)

            else:
                create_rowDict = {'name': data['工厂款号'],
                                  'color_cn': data['配色Cn'],
                                  'color_en': data['配色En'],
                                  'type': 'product',
                                  'uom_id': res2.filtered(lambda r: r.name == data['单位']).id,
                                  'uom_po_id': res2.filtered(lambda r: r.name == data['单位']).id,
                                  'customer_number': data['客户款号'],
                                  'categ_id': res1.filtered(lambda r: r.name == data['鞋码标准']).id,
                                  # 'categ_id': self.env['product.category'].search([('name','=',data['鞋码标准'])]).id,
                                  'trademark': data['商标'],
                                  'route_ids':[(6,0,[1,8] )],
                                  'seller_ids':[(0,0,{'name': 504,'price':1})]
                                  }
                rowsList.append(create_rowDict)
        # print(self)
        # print(self.env)
        # print(self.env.context)
        # print(self.env.user)
        a = self.warehouse_id.lot_stock_id
        b = self.warehouse_id

        if rowsList:
            # self.env['product.supplierinfo'].create(product_supplier_list)
            return_data_list = super(product_inheritance, self).create(rowsList)
            return_rex_data_dict_list = []
            id_list = []
            company_id = self.env.user.company_id.id
            print(self)
            print(self.env)
            print(self.env.context)
            print(self.env.user)
            for return_data in return_data_list:
                id_list.append(return_data.id)

                return_rex_data_dict = {
                    'active':'t',
                    'location_id':8,
                    'product_id':0,
                    'warehouse_id':1,
                    'product_category_id':20,
                    'product_min_qty':0,
                    'product_max_qty':0,
                    'qty_multiple':1,
                    'company_id':company_id,
                    'qty_to_order':1,
                }
                return_rex_data_dict_list.append(return_rex_data_dict)
            product_list = self.env['product.product'].search([('product_tmpl_id', 'in', id_list)])

            for index,product in enumerate(product_list):
                return_rex_data_dict_list[index]['product_id'] = product.id
            self.env['stock.warehouse.orderpoint'].create(return_rex_data_dict_list)


        # 明细数量
        # orderNumbers = existRows.mapped('factory_data_from_ids')
        # super(customer_inheritance, self).create()
        # is_customer = search_partner_mode == 'customer'
        # is_supplier = search_partner_mode == 'supplier'
        # if search_partner_mode:
        #     for vals in vals_list:
        #         if is_customer and 'customer_rank' not in vals:
        #             vals['customer_rank'] = 1
        #         elif is_supplier and 'supplier_rank' not in vals:
        #             vals['supplier_rank'] = 1
        # return super().create(vals_list)
        # b = 11
        # shift + f6
        # b =22

# # 产品继承修改模块
# class order_inheritance(models.Model):
#
#     _inherit = 'product.template'
#     color_en = fields.Char("配色_en")




class search_criteria(models.TransientModel):
    _name = "search.criteria"

    start_time = fields.Date("起始时间")
    end_time = fields.Date("结束时间")
    is_order_time = fields.Boolean("按下单日期查询导入")

    def import_data(self):
        for record in self:
            start_time = record.start_time
            end_time = record.end_time
            print(self.env)

            class_order = self.env['sale.order']
            class_order.order_import_data(start_time,end_time)

    @api.constrains('start_time', 'end_time')
    def _check_description(self):
        if self.start_time == self.end_time:
            raise ValidationError("时间相同，重新输入")
        if self.start_time > self.end_time:
            raise ValidationError("起始时间大于结束时间，请重新输入")

    @api.onchange('end_time')
    def _onchange_partner(self):
        # if self.start_time == self.end_time:
        #     raise ValidationError("时间相同，重新输入")
        if self.start_time > self.end_time:
            raise ValidationError("起始时间大于结束时间，请重新输入")
# stock.move继承修改模块
class stock_inheritance(models.Model):

    _inherit = 'stock.move'



    trademark = fields.Float("改变",compute='_default')

    @api.depends('trademark')
    def _default(self):
        try:
            if self.sale_line_id:
                return self.sale_line_id.prices_pairs
            else:
                return 1
        finally:
            pass





