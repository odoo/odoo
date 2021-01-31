# -*- coding: utf-8 -*-

from odoo import models, fields, api,tools
import pymssql
import xlwt,xlrd,datetime

class orderin(models.Model):
    _name = 'orderin.orderin'

    name = fields.Char('订单编号')
    prduct_name = fields.Char('产品名')
    product_uom_qty = fields.Float('最少购买量')
    commitment_date = fields.Char('送货日期')
    cate_nam = fields.Char('产品类型')

    def aaa(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'orderinquiry.orderinquiry',
            'multi': True,
            'auto_refresh': 1,
            'name': '查询结果',
            'context': {'search_default_name': self.name, 'search_default_product_uom_qty': self.product_uom_qty,
                        'search_default_commitment_date': self.commitment_date,
                        'search_default_prduct_name': self.prduct_name,
                        'search_default_cate_nam': self.cate_nam},
            'view_mode': 'tree,form',
            'target': 'main',
            'auto_search': True,
        }


# 产品类别导入
class produca(models.Model):
    _inherit = 'product.category'
    def prod_imp(self):
        sql='SELECT * FROM odoo_款式分类查询'
        conn = pymssql.connect('192.168.88.180', 'Pghcs6KcvXWS3t', 'ac@#F%tISqc1fSz9','erpdata')
        cur = conn.cursor()
        cur.execute(sql)  # 执行语句
        res = cur.fetchall()
        s=[]
        print(res)
        if(self.env['product.category'].search([('name','=','成品')])):
            pass
        else:
            super(produca, self).create([{'name':'成品','parent_id':None}]).id
        for i in res:
            z=0
            ss=''
            for j in i[0].split('/'):
                if z==0:
                    ss=j
                    if self.env['product.category'].search(['&', ('complete_name', '=', j), ('name', '=', j)]):
                        pass
                    else:
                        new = self.env['product.category'].search([('complete_name', '=', ss)]).id
                        super(produca, self).create([{'name': j, 'parent_id': new}])
                else:
                    if self.env['product.category'].search(['&',('complete_name','=',ss+' / '+j),('name','=',j)]):
                        pass
                    else:
                        new=self.env['product.category'].search([('complete_name', '=', ss)]).id
                        super(produca, self).create([{'name': j, 'parent_id': new}])
                if z==0:
                    z+=1
                    pass
                else:
                    ss+=' / '+j

#供应商导入
class supplierss(models.Model):
    _inherit = 'res.partner'

    short_name = fields.Char('简称')
    Entper = fields.Char('企业法人')
    # contacts=fields.Char('联系人')
    # position=fields.Char('联系职务')
    production_scale = fields.Char('生产规模')
    monthly_capacity = fields.Char('月产能')
    annual_capacity = fields.Char('年产能')
    address = fields.Char('工厂地址')
    bank_of_deposit = fields.Char('开户银行')
    bank_account = fields.Char('银行账号')
    remarks = fields.Char('备注')

    def imp(self):
        print(1)
        workBook = xlrd.open_workbook('F:\odoo2\odoo\myaddons\mode\供应商名录.xlsx')
        sheet1_content1 = workBook.sheet_by_index(0)
        adds = []
        ide = {'name': 0, 'short_name': 1, 'Entper': 2, 'contacts': 3,
               'position': 4, 'phone': 5, 'production_scale': 7, 'monthly_capacity': 8,
               'annual_capacity': 9, 'email': 10, 'address': 11, 'bank_of_deposit': 12,
               'bank_account': 13, 'remarks': 14}
        for data in range(4, sheet1_content1.nrows):
            row = sheet1_content1.row_values(data)
            if (self.env['res.partner'].search([('name', '=', row[ide['name']])])):
                update = self.env['res.partner'].search([('name', '=', ide['name'])])
                update.write({'short_name': row[ide['short_name']],
                              'Entper': row[ide['Entper']],
                              'child_ids': [(0, 0, {'type': 'contact', 'name': row[ide['contacts']],
                                                    'function': row[ide['position']],
                                                    'phone': str(row[ide['phone']]).split('.')[0]})],
                              'production_scale': row[ide['production_scale']],
                              'monthly_capacity': row[ide['monthly_capacity']],
                              'annual_capacity': row[ide['annual_capacity']],
                              'email': row[ide['email']],
                              'address': row[ide['address']],
                              'bank_of_deposit': row[ide['bank_of_deposit']],
                              'bank_account': row[ide['bank_account']],
                              'remarks': row[ide['remarks']]})
                pass
            else:
                add = {'name': row[ide['name']],
                       'short_name': row[ide['short_name']],
                       'Entper': row[ide['Entper']],
                       'child_ids': [(0, 0,
                                      {'type': 'contact', 'name': row[ide['contacts']],
                                       'function': row[ide['position']],
                                       'phone': str(row[ide['phone']]).split('.')[0]})],
                       'production_scale': row[ide['production_scale']],
                       'monthly_capacity': row[ide['monthly_capacity']],
                       'annual_capacity': row[ide['annual_capacity']],
                       'email': row[ide['email']],
                       'address': row[ide['address']],
                       'bank_of_deposit': row[ide['bank_of_deposit']],
                       'bank_account': row[ide['bank_account']],
                       'remarks': row[ide['remarks']],
                       'is_company': 't', 'type': 'contact',
                       'supplier_rank': '1', 'partner_gid': '0'}
                adds.append(add)
        super(supplierss, self).create(adds)