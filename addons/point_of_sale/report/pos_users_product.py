# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from openerp.osv import osv
from openerp.report import report_sxw


class pos_user_product(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(pos_user_product, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
            'get_data':self._get_data,
            'get_user':self._get_user,
            'get_total':self._get_total,

        })

    def _get_data(self, o):
        self.total = 0.0
        data={}
        sql1=""" SELECT distinct(o.id) from account_bank_statement s, account_bank_statement_line l,pos_order o,pos_order_line i where  i.order_id=o.id and o.state='paid' and l.statement_id=s.id and l.pos_statement_id=o.id and s.id=%d"""%(o.id)
        self.cr.execute(sql1)
        data = self.cr.dictfetchall()
        a_l=[]
        for r in data:
            a_l.append(r['id'])
        if len(a_l):
            sql2="""SELECT sum(qty) as qty,l.price_unit*sum(l.qty) as amt,t.name as name, p.default_code as code, pu.name as uom from product_product p, product_template t,product_uom pu,pos_order_line l where order_id = %d and p.product_tmpl_id=t.id and l.product_id=p.id and pu.id=t.uom_id group by t.name,p.default_code,pu.name,l.price_unit"""%(o.id)
            self.cr.execute(sql2)
            data = self.cr.dictfetchall()
        for d in data:
            self.total += d['amt']
        return data

    def _get_user(self, object):
        names = []
        users_obj = self.pool['res.users']
        for o in object:
            sql = """select ru.id from account_bank_statement as abs,res_users ru
                                    where abs.user_id = ru.id
                                    and abs.id = %d"""%(o.id)
            self.cr.execute(sql)
            data = self.cr.fetchone()
            if data:
                user = users_obj.browse(self.cr, self.uid, data[0])
                names.append(user.partner_id.name)
        return list(set(names))

    def _get_total(self, o):
        return self.total


class report_pos_user_product(osv.AbstractModel):
    _name = 'report.point_of_sale.report_usersproduct'
    _inherit = 'report.abstract_report'
    _template = 'point_of_sale.report_usersproduct'
    _wrapped_report_class = pos_user_product
