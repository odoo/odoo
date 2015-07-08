# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from openerp import models, api


class ReportPosDetails(models.AbstractModel):
    _name = 'report.point_of_sale.report_detailsofsales'
    _inherit = 'report.abstract_report'
    _template = 'point_of_sale.report_detailsofsales'

    total = 0.0
    qty = 0.0
    total_invoiced = 0.0
    discount = 0.0
    total_discount = 0.0

    def _get_invoice(self, inv_id):
        res = {}
        if inv_id:
            self._cr.execute(
                "select number from account_invoice as ac where id = %s", (inv_id,))
            res = self._cr.fetchone()
            return res[0] or 'Draft'
        else:
            return ''

    def _get_all_users(self):
        return self.env['res.users'].search([]).ids

    def _pos_sales_details(self, form):
        data = []
        result = {}
        user_ids = form['user_ids'] or self._get_all_users()
        pos_order = self.env['pos.order'].search([('date_order', '>=', form['date_start'] + ' 00:00:00'), ('date_order', '<=', form['date_end'] + ' 23:59:59'), (
            'user_id', 'in', user_ids), ('state', 'in', ['done', 'paid', 'invoiced']), ('company_id', '=', self.env.user.company_id.id)])
        for pos in pos_order:
            for pol in pos.lines:
                result = {
                    'code': pol.product_id.default_code,
                    'name': pol.product_id.name,
                    'invoice_id': pos.invoice_id.id,
                    'price_unit': pol.price_unit,
                    'qty': pol.qty,
                    'discount': pol.discount,
                    'total': (pol.price_unit * pol.qty * (1 - (pol.discount) / 100.0)),
                    'date_order': pos.date_order,
                    'pos_name': pos.name,
                    'uom': pol.product_id.uom_id.name
                }
                data.append(result)
                self.total += result['total']
                self.qty += result['qty']
                self.discount += result['discount']
        if data:
            return data
        else:
            return {}

    def _get_qty_total_2(self):
        return self.qty

    def _get_sales_total_2(self):
        return self.total

    def _get_sum_invoice_2(self, form):
        user_ids = form['user_ids'] or self._get_all_users()
        pos_order = self.env[
            'pos.order'].search([('date_order', '>=', form['date_start'] + ' 00:00:00'),
                                ('date_order', '<=', form['date_end'] + ' 23:59:59'),
                                ('user_id', 'in', user_ids),
                                ('company_id', '=', self.env.user.company_id.id),
                                ('invoice_id', '<>', False)]
                                )
        for pos in pos_order:
            for pol in pos.lines:
                self.total_invoiced += (
                    pol.price_unit * pol.qty * (1 - (pol.discount) / 100.0))
        return self.total_invoiced or False

    def _paid_total_2(self):
        return self.total or 0.0

    def _get_sum_dis_2(self):
        return self.discount or 0.0

    def _get_sum_discount(self, form):
        # code for the sum of discount value
        user_ids = form['user_ids'] or self._get_all_users()
        pos_order = self.env[
            'pos.order'].search([('date_order', '>=', form['date_start'] + ' 00:00:00'), ('date_order', '<=',
                                                                                          form['date_end'] + ' 23:59:59'), ('user_id', 'in', user_ids), ('company_id', '=', self.env.user.company_id.id)])
        for pos in pos_order:
            for pol in pos.lines:
                self.total_discount += (
                    (pol.price_unit * pol.qty) * (pol.discount / 100))
        return self.total_discount or False

    def _get_payments(self, form):
        user_ids = form['user_ids'] or self._get_all_users()
        pos_order = self.env["pos.order"].search([('date_order', '>=', form['date_start'] + ' 00:00:00'), ('date_order', '<=', form['date_end'] + ' 23:59:59'), (
            'state', 'in', ['paid', 'invoiced', 'done']), ('user_id', 'in', user_ids), ('company_id', '=', self.env.user.company_id.id)])
        data = {}
        if pos_order:
            st_line = self.env["account.bank.statement.line"].search(
                [('pos_statement_id', 'in', pos_order.ids)])
            if st_line:
                a_l = []
                for r in st_line:
                    a_l.append(r['id'])
                self._cr.execute("select aj.name,sum(amount) from account_bank_statement_line as absl,account_bank_statement as abs,account_journal as aj "
                                 "where absl.statement_id = abs.id and abs.journal_id = aj.id  and absl.id IN %s "
                                 "group by aj.name ", (tuple(a_l),))

                data = self._cr.dictfetchall()
                return data
        else:
            return {}

    def _total_of_the_day(self, objects):
        return self.total or 0.00

    def _sum_invoice(self, objects):
        return reduce(lambda acc, obj:
                      acc + obj.invoice_id.amount_total,
                      [o for o in objects if o.invoice_id and o.invoice_id.number],
                      0.0)

    def _ellipsis(self, orig_str, maxlen=100, ellipsis='...'):
        maxlen = maxlen - len(ellipsis)
        if maxlen <= 0:
            maxlen = 1
        new_str = orig_str[:maxlen]
        return new_str

    def _strip_name(self, name, maxlen=50):
        return self._ellipsis(name, maxlen, ' ...')

    def _get_tax_amount(self, form):
        taxes = {}
        user_ids = form['user_ids'] or self._get_all_users()
        pos_order = self.env['pos.order'].search([('date_order', '>=', form['date_start'] + ' 00:00:00'), ('date_order', '<=', form['date_end'] + ' 23:59:59'), (
            'state', 'in', ['paid', 'invoiced', 'done']), ('user_id', 'in', user_ids), ('company_id', '=', self.env.user.company_id.id)])
        for order in pos_order:
            currency = order.session_id.currency_id
            for line in order.lines:
                if line.product_id.taxes_id:
                    line_taxes = line.product_id.taxes_id.compute_all(
                        line.price_unit * (1 - (line.discount or 0.0) / 100.0), currency, line.qty, product=line.product_id, partner=line.order_id.partner_id or False)
                    for tax in line_taxes['taxes']:
                        taxes.setdefault(
                            tax['id'], {'name': tax['name'], 'amount': 0.0})
                        taxes[tax['id']]['amount'] += tax['amount']
        return taxes.values()

    def _get_user_names(self, user_ids):
        return ', '.join(map(lambda x: x.name, self.env['res.users'].browse(user_ids)))

    @api.multi
    def render_html(self, data=None):
        Report = self.env['report']
        report = Report._get_report_from_name(
            'point_of_sale.report_detailsofsales')
        records = self.env['pos.order'].browse(self.ids)
        docargs = {
            'doc_ids': self._ids,
            'doc_model': report.model,
            'docs': records,
            'data': data,
            'time': time,
            'strip_name': self._strip_name,
            'getpayments': self._get_payments,
            'getsumdisc': self._get_sum_discount,
            'gettotaloftheday': self._total_of_the_day,
            'gettaxamount': self._get_tax_amount,
            'pos_sales_details': self._pos_sales_details,
            'getqtytotal2': self._get_qty_total_2,
            'getsalestotal2': self._get_sales_total_2,
            'getsuminvoice2': self._get_sum_invoice_2,
            'getpaidtotal2': self._paid_total_2,
            'getinvoice': self._get_invoice,
            'get_user_names': self._get_user_names,
        }
        return Report.render('point_of_sale.report_detailsofsales', docargs)
