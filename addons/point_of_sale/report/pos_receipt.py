# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from openerp import models, api


def titlize(journal_name):
    words = journal_name.split()
    while words.pop() != 'journal':
        continue
    return ' '.join(words)


class ReportOrderReceipt(models.AbstractModel):
    _name = 'report.point_of_sale.report_receipt'
    _inherit = 'report.abstract_report'
    _template = 'point_of_sale.report_receipt'

    def netamount(self, order_line_id):
        sql = 'select (qty*price_unit) as net_price from pos_order_line where id = %s'
        self._cr.execute(sql, (order_line_id,))
        res = self._cr.fetchone()
        return res[0]

    def discount(self, order_id):
        sql = 'select discount, price_unit, qty from pos_order_line where order_id = %s '
        self._cr.execute(sql, (order_id,))
        res = self._cr.fetchall()
        dsum = 0
        for line in res:
            if line[0] != 0:
                dsum = dsum + (line[2] * (line[0] * line[1] / 100))
        return dsum

    def _get_journal_amt(self, order_id):
        data = {}
        sql = """ select aj.name,absl.amount as amt from account_bank_statement as abs
                        LEFT JOIN account_bank_statement_line as absl ON abs.id = absl.statement_id
                        LEFT JOIN account_journal as aj ON aj.id = abs.journal_id
                        WHERE absl.pos_statement_id =%d""" % (order_id)
        self._cr.execute(sql)
        data = self._cr.dictfetchall()
        return data

    @api.multi
    def render_html(self, data=None):
        Report = self.env['report']
        report = Report._get_report_from_name(
            'point_of_sale.report_receipt')
        records = self.env['pos.order'].browse(self.ids)
        docargs = {
            'doc_ids': self._ids,
            'doc_model': report.model,
            'docs': records,
            'data': data,
            'time': time,
            'disc': self.discount,
            'net': self.netamount,
            'get_journal_amt': self._get_journal_amt,
            'address': self.env.user.partner_id or False,
            'titlize': titlize
        }
        return Report.render('point_of_sale.report_receipt', docargs)
