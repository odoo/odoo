# -*- coding: utf-8 -*-

from odoo import models, fields, api
import pymssql
import xlwt, xlrd, datetime


class produca(models.Model):
    _inherit = 'product.category'

    def aaa(self):
        print(11111)
        sql = "select * from 销售订单明细;"
        conn = pymssql.connect('192.168.88.174', 'sa', 'ad6e78dfj', 'erpdata')
        cur = conn.cursor()
        # conn = pymssql.connect('localhost', 'sa', 'sa', 'odoo')
        # cur = conn.cursor()
        # sql = 'select * from table1'
        cur.execute(sql)  # 执行语句
        res = cur.fetchall()
        adds = []
        z = 0
        for i in res:
            # z+=1
            # if(z>50):
            #     break
            if (i[7] > datetime.datetime.now() - datetime.timedelta(days=1)):
                print(i[7])
            add = {'name': str(i[8]).strip()}
            adds.append(add)
        # super(produca, self).create(adds)
        pass

    def bbb(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sys.sys',
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

    def ccc(self):
        pass
        sql = 'SELECT * FROM odoo_款式分类查询'
        conn = pymssql.connect('192.168.88.180', 'Pghcs6KcvXWS3t', 'ac@#F%tISqc1fSz9', 'erpdata')
        cur = conn.cursor()
        cur.execute(sql)  # 执行语句
        res = cur.fetchall()
        s = []
        print(res)
        if (self.env['product.category'].search([('name', '=', '成品')])):
            pass
        else:
            super(produca, self).create([{'name': '成品', 'parent_id': None}]).id
        for i in res:
            z = 0
            ss = ''
            for j in i[0].split('/'):
                if z == 0:
                    ss = j
                    if self.env['product.category'].search(['&', ('complete_name', '=', j), ('name', '=', j)]):
                        pass
                    else:
                        new = self.env['product.category'].search([('complete_name', '=', ss)]).id
                        super(produca, self).create([{'name': j, 'parent_id': new}])
                else:
                    if self.env['product.category'].search(
                            ['&', ('complete_name', '=', ss + ' / ' + j), ('name', '=', j)]):
                        pass
                    else:
                        new = self.env['product.category'].search([('complete_name', '=', ss)]).id
                        super(produca, self).create([{'name': j, 'parent_id': new}])
                if z == 0:
                    z += 1
                    pass
                else:
                    ss += ' / ' + j
        if (self.env['product.category'].search([('name', '=', '成品')])):
            root = self.env['product.category'].search([('name', '=', '成品')]).id
        else:
            root = super(produca, self).create([{'name': '成品', 'parent_id': None}]).id
        for i in res:
            if (self.env['product.category'].search([('name', '=', i[0])])):
                pass
            else:
                super(produca, self).create([{'name': i[0], 'parent_id': root}])


class sy(models.Model):
    _name = "sys.sys"

    name = fields.Char("")

    def shiyan(self):
        print(self.name)


class addproduct(models.Model):
    _inherit = 'product.template'

    color_cn = fields.Char('中文配色')
    color_en = fields.Char('英文配色')
    client_no = fields.Char('客户款号')
    brand = fields.Char('商标')

    def add(self):

        sql = 'SELECT * FROM odoo_工厂款号查询'
        conn = pymssql.connect('192.168.88.180', 'Pghcs6KcvXWS3t', 'ac@#F%tISqc1fSz9', 'erpdata')
        cur = conn.cursor(as_dict=True)
        cur.execute(sql)  # 执行语句
        res = cur.fetchall()
        res1 = self.env['product.category'].search([])
        res2 = self.env['uom.uom'].search([])
        rowsList = []
        print(res)
        i = 0
        for data in res:
            if i >= 100:
                break
            i += 1
            existRows = self.env['product.template'].search([('name', '=', data['工厂款号'])])
            if existRows:
                update_rowDict = {
                    'color_cn': data['配色Cn'],
                    'color_en': data['配色En'],
                    'client_no': data['客户款号'],
                    'uom_id': res2.filtered(lambda r: r.name == data['单位']).id,
                    'uom_po_id': res2.filtered(lambda r: r.name == data['单位']).id,
                    'categ_id': res1.filtered(lambda r: r.name == data['鞋码标准']).id,
                    'brand': data['商标']
                }
                existRows.write(update_rowDict)
                print(1)
            else:
                create_rowDict = {'name': data['工厂款号'],
                                  'color_cn': data['配色Cn'],
                                  'color_en': data['配色En'],
                                  'type': 'product',
                                  'uom_id': res2.filtered(lambda r: r.name == data['单位']).id,
                                  'uom_po_id': res2.filtered(lambda r: r.name == data['单位']).id,
                                  'client_no': data['客户款号'],
                                  'categ_id': res1.filtered(lambda r: r.name == data['鞋码标准']).id,
                                  # 'categ_id': self.env['product.category'].search([('name','=',data['鞋码标准'])]).id,
                                  'brand': data['商标']
                                  }
                print(create_rowDict)
                rowsList.append(create_rowDict)
        if rowsList:
            super(addproduct, self).create(rowsList)