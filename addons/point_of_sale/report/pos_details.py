# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time
from odoo import api, models


class ReportPosDetails(models.AbstractModel):
    _name = 'report.point_of_sale.report_detailsofsales'

    def _prepare_pos_data(self, user_ids=False, date_start=False, date_end=False):
        data = {
            'pos_lines': [],
            'total': 0.0,
            'total_qty': 0.0,
            'total_discount': 0.0,
            'total_invoice': 0.0,
            'date_start': date_start,
            'date_end': date_end}
        result = {}
        taxes = {}
        domain = [
            ('date_order', '>=', date_start + ' 00:00:00'),
            ('date_order', '<=', date_end + ' 23:59:59'),
            ('state', 'in', ['done', 'paid', 'invoiced'])]
        if user_ids:
            domain.append(('user_id', 'in', user_ids))
        orders = self.env['pos.order'].search(domain)

        for order in orders:
            for pol in order.lines:
                result = {
                    'code': pol.product_id.default_code,
                    'name': pol.product_id.name,
                    'invoice': order.invoice_id,
                    'price_unit': pol.price_unit,
                    'qty': pol.qty,
                    'discount': pol.discount,
                    'total': (pol.price_unit * pol.qty * (1 - (pol.discount) / 100.0)),
                    'date_order': order.date_order,
                    'pos_name': order.name,
                    'uom': pol.product_id.uom_id.name
                }
                data['pos_lines'].append(result)
                data['total'] += result['total']
                data['total_qty'] += result['qty']
                data['total_discount'] += ((pol.price_unit * pol.qty) * (pol.discount / 100))
                if order.invoice_id:
                    data['total_invoice'] += result['total']
                if pol.product_id.taxes_id:
                    line_taxes = pol.product_id.taxes_id.compute_all(result['total'], order.session_id.currency_id, pol.qty, product=pol.product_id, partner=pol.order_id.partner_id or False)
                    for tax in line_taxes['taxes']:
                        taxes.setdefault(tax['id'], {'name': tax['name'], 'amount': 0.0})
                        taxes[tax['id']]['amount'] += tax['amount']
        data['taxes'] = taxes.values()  # total amount of taxes
        data['payments'] = self._get_payments(orders)  # total payment amount
        return data

    def _get_payments(self, orders):
        if orders:
            statement_lines = self.env["account.bank.statement.line"].search([('pos_statement_id', 'in',  orders.ids)])
            journals_name = set([line.statement_id.journal_id.name for line in statement_lines if line.statement_id.journal_id])
            res = dict(map(lambda x: (x, 0.0), journals_name))
            if res:
                for line in statement_lines.filtered(lambda line: line.statement_id.journal_id):
                    res[line.statement_id.journal_id.name] += line.amount
                return res
        return {}

    def _get_user_names(self, user_ids):
        return ', '.join(map(lambda x: x.name, self.env['res.users'].browse(user_ids)))

    @api.multi
    def render_html(self, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        form = data.get('form')
        docargs = {
            'doc_ids': self.ids,
            'doc_model': model,
            'docs': docs,
            'time': time,
            'pos_data': self._prepare_pos_data(form['user_ids'], form['date_start'], form['date_end']),
            'user_names': self._get_user_names(form['user_ids']),
        }
        return self.env['report'].render('point_of_sale.report_detailsofsales', docargs)
