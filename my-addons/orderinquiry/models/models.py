# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools


# TransientModel临时存储数据
class orderinquiry_orderinquiry(models.Model):
    _name = 'orderinquiry.orderinquiry'
    _auto = False  # 不创建数据库表

    soid = fields.Many2one('sale.order', string='订单编号', readonly=True)
    name = fields.Char('订单编号', readonly=True)
    product_id = fields.Many2one('product.product', string='产品名', readonly=True)
    product_uom_qty = fields.Float('最少购买量', readonly=True)
    commitment_date = fields.Char('送货日期', readonly=True)
    prduct_name = fields.Char('产品名', readonly=True)
    categ_id = fields.Many2one('product.category', '产品类型', readonly=True)
    cate_nam = fields.Char('产品类型', readonly=True)

    order_size_seg = fields.Char(string="下单码段")
    customer_po = fields.Char(string="客户PO号")
    pack_method = fields.Char('装箱配码')
    pieces = fields.Integer('件数')
    pieces_pairs = fields.Integer('件双数')
    factory_date = fields.Date('工厂交期')
    pre_dept = fields.Char("预排部门")
    pre_line = fields.Char("预排线别")
    prod_dept = fields.Char("生产部门")
    prod_line = fields.Char("生产线别")
    batch_no = fields.Char("批次号")
    lc_no = fields.Char("轮次号")
    plan_started_date = fields.Date("计划上线")
    plan_finished_date = fields.Date("计划完成")

    # # @api.model
    # # @api.model_cr
    def init(self):  # 将查询到的结果集返回给当前视图
        """test report"""
        tools.drop_view_if_exists(self.env.cr, 'orderinquiry_orderinquiry')
        self.env.cr.execute("""CREATE OR REPLACE VIEW orderinquiry_orderinquiry AS ( SELECT a.id,
                                b.id AS soid,
                                a.product_id,
                                a.product_uom_qty,
                                b.name,
                                b.commitment_date,
                                d.name AS prduct_name,
                                d.categ_id,
                                e.name AS cate_nam,
                                a.pack_method,
                                a.pieces,
                                a.pieces_pairs,
                                    a.factory_date,
                                    a.pre_dept,
                                    a.pre_line,
                                    a.prod_dept,
                                    a.prod_line,
                                    a.batch_no,
                                    a.lc_no,
                                    a.plan_started_date,
                                    a.plan_finished_date,
                                    b.order_size_seg,
                                    b.customer_po
                               FROM ((((sale_order_line a
                                 LEFT JOIN sale_order b ON ((a.order_id = b.id)))
                                 LEFT JOIN product_product c ON ((a.product_id = c.id)))
                                 LEFT JOIN product_template d ON ((d.id = c.product_tmpl_id)))
                                 LEFT JOIN product_category e ON ((e.id = d.categ_id))))""")

    def inquiry(self):
        res = self.env.context['active_domain']
        add = {}
        for i in res:
            if isinstance(i, list):
                add['default_' + i[0]] = i[2]
        # print(add)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'orderin.orderin',
            # 'limit':1,
            'name': '多条件搜索',
            'multi': True,
            'auto_refresh': 1,
            # 'view_type': 'form',
            # 设置过滤条件search_default_+所需判断的字段名
            'context': add,
            'view_mode': 'form',
            # 'res_id':orde.id,
            # 'views': [(True, "tree")],
            'target': 'new',
            'auto_search': True,
        }


class orderin(models.Model):
    _name = 'orderin.orderin'

    # soid = fields.Many2one('sale.order', string='订单编号')
    name = fields.Char('订单编号')
    prduct_name = fields.Char('产品名')
    product_uom_qty = fields.Float('最少购买量')
    commitment_date = fields.Char('送货日期')
    cate_nam = fields.Char('产品类型')

    order_size_seg = fields.Char(string="下单码段")
    customer_po = fields.Char(string="客户PO号")

    pack_method = fields.Char('装箱配码')
    pieces = fields.Integer('件数')
    pieces_pairs = fields.Integer('件双数')
    factory_date = fields.Date('工厂交期')
    pre_dept = fields.Char("预排部门")
    pre_line = fields.Char("预排线别")
    prod_dept = fields.Char("生产部门")
    prod_line = fields.Char("生产线别")
    batch_no = fields.Char("批次号")
    lc_no = fields.Char("轮次号")
    plan_started_date = fields.Date("计划上线")
    plan_finished_date = fields.Date("计划完成")

    def aaa(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'orderinquiry.orderinquiry',
            # 'limit':1,
            'multi': True,
            'auto_refresh': 1,
            'name': '查询结果',
            # 'view_type': 'form',
            # 设置过滤条件
            'context': {'search_default_name': self.name, 'search_default_product_uom_qty': self.product_uom_qty,
                        'search_default_commitment_date': self.commitment_date,
                        'search_default_prduct_name': self.prduct_name,
                        'search_default_cate_nam': self.cate_nam},
            'view_mode': 'tree,form',
            # 'views': [(True, "tree")],
            'target': 'main',
            'auto_search': True,
        }
