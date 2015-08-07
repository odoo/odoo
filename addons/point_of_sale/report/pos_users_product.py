# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from openerp import models, api


class ReportPosUserProduct(models.AbstractModel):
    _name = 'report.point_of_sale.report_usersproduct'
    _inherit = 'report.abstract_report'
    _template = 'point_of_sale.report_usersproduct'

    def _get_data(self, o):
        self.total = 0.0
        data = {}
        sql1 = """ SELECT distinct(o.id) from account_bank_statement s, account_bank_statement_line l,pos_order o,pos_order_line i where  i.order_id=o.id and o.state='paid' and l.statement_id=s.id and l.pos_statement_id=o.id and s.id=%d""" % (
            o.id)
        self.env.cr.execute(sql1)
        data = self.env.cr.dictfetchall()
        a_l = []
        for r in data:
            a_l.append(r['id'])
        if len(a_l):
            sql2 = """SELECT sum(qty) as qty,l.price_unit*sum(l.qty) as amt,t.name as name, p.default_code as code, pu.name as uom from product_product p, product_template t,product_uom pu,pos_order_line l where order_id = %d and p.product_tmpl_id=t.id and l.product_id=p.id and pu.id=t.uom_id group by t.name,p.default_code,pu.name,l.price_unit""" % (
                o.id)
            self.env.cr.execute(sql2)
            data = self.env.cr.dictfetchall()
        for d in data:
            self.total += d['amt']
        return data

    def _get_user(self, object):
        names = []
        Users = self.env['res.users']
        for o in object:
            sql = """select ru.id from account_bank_statement as abs,res_users ru
                                    where abs.user_id = ru.id
                                    and abs.id = %d""" % (o.id)
            self.env.cr.execute(sql)
            data = self.env.cr.fetchone()
            if data:
                user = Users.browse(data[0])
                names.append(user.partner_id.name)
        return list(set(names))

    def _get_total(self, o):
        return self.total

    @api.multi
    def render_html(self, data=None):
        Report = self.env['report']
        report = Report._get_report_from_name(
            'point_of_sale.report_usersproduct')
        records = self.env['account.bank.statement'].browse(self.ids)
        docargs = {
            'doc_ids': self._ids,
            'doc_model': report.model,
            'docs': records,
            'time': time,
            'data': data,
            'get_data': self._get_data,
            'get_user': self._get_user,
            'get_total': self._get_total,
        }
        return Report.render('point_of_sale.report_usersproduct', docargs)
