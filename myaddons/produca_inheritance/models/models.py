# -*- coding: utf-8 -*-

from odoo import models, fields, api
import pymssql
import xlwt,xlrd,datetime

class produca_inheritance(models.Model):
    _inherit = 'sale.order'

    def aaa(self):
        sql = "select * from 销售订单明细;"
        conn = pymssql.connect('192.168.88.174', 'sa', 'ad6e78dfj', 'erpdata')
        cur = conn.cursor()
        # conn = pymssql.connect('localhost', 'sa', 'sa', 'odoo')
        # cur = conn.cursor()
        # sql = 'select * from table1'
        cur.execute(sql)  # 执行语句
        res = cur.fetchall()
        adds = []
        z=0
        for i in res:
            # z+=1
            # if(z>50):
            #     break
            if(i[7]>datetime.datetime.now()-datetime.timedelta(days=1)):
                print(i[7])
            add = {'name': str(i[8]).strip()}
            adds.append(add)
        # super(produca, self).create(adds)
        pass
    def bbb(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            # 'limit':1,
            'name': '实验',
            'multi': True,
            'auto_refresh': 1,
            # 'view_type': 'form',
            # 设置过滤条件search_default_+所需判断的字段名
            # 'context': {'ids': i},
            'view_mode': 'form',
            # 'res_id':orde.id,
            # 'views': [(True, "tree")],
            'target': 'new',
            'auto_search': True,
        }
#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

class sy(models.Model):
    _name="sys.sys"

    name=fields.Char("实验")