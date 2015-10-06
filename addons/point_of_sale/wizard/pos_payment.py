# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from openerp import api, fields, models, _


class PosMakePayment(models.TransientModel):
    _name = 'pos.make.payment'
    _description = 'Point of Sale Payment'

    def _default_journal(self):
        session = False
        context = dict(self.env.context or {})
        active_id = context.get('active_id', False) or False
        if active_id:
            session = self.env['pos.order'].browse(active_id).session_id
        if session:
            for journal in session.config_id.journal_ids:
                return journal.id
        return False

    def _default_amount(self):
        context = dict(self.env.context or {})
        active_id = context.get('active_id', False) or False
        if active_id:
            order = self.env['pos.order'].browse(active_id)
            return order.amount_total - order.amount_paid
        return False

    journal_id = fields.Many2one('account.journal', string='Payment Mode', required=True, default=_default_journal)
    amount = fields.Float(digits=(16, 2), required=True, default=_default_amount)
    payment_name = fields.Char(string='Payment Reference')
    payment_date = fields.Date(string='Payment Date', required=True, default=lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'))

    @api.multi
    def check(self):
        """Check the order:
        if the order is not paid: continue payment,
        if the order is paid print ticket.
        """
        self.ensure_one()
        context = dict(self.env.context or {})
        active_id = context.get('active_id', False) or False
        order = self.env['pos.order'].browse(active_id)
        amount = order.amount_total - order.amount_paid
        data = self.read()[0]
        # this is probably a problem of osv_memory as it's not compatible with normal OSV's
        data['journal'] = data['journal_id'][0]
        if amount != 0.0:
            order.add_payment(data)
        if order.test_paid():
            order.signal_workflow('paid')
            return {'type': 'ir.actions.act_window_close'}

        return self.launch_payment()

    def launch_payment(self):
        return {
            'name': _('Payment'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pos.make.payment',
            'view_id': False,
            'target': 'new',
            'views': False,
            'type': 'ir.actions.act_window',
            'context': self.env.context,
        }

    def print_report(self):
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'pos.receipt',
            'datas': {'ids': [self.env.context.get('active_id', False)]},
        }
