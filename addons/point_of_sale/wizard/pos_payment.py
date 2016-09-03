# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class PosMakePayment(models.TransientModel):
    _name = 'pos.make.payment'
    _description = 'Point of Sale Payment'

    def _default_journal(self):
        active_id = self.env.context.get('active_id')
        if active_id:
            session = self.env['pos.order'].browse(active_id).session_id
            return session.config_id.journal_ids and session.config_id.journal_ids.ids[0] or False
        return False

    def _default_amount(self):
        active_id = self.env.context.get('active_id')
        if active_id:
            order = self.env['pos.order'].browse(active_id)
            return (order.amount_total - order.amount_paid)
        return False

    journal_id = fields.Many2one('account.journal', string='Payment Mode', required=True, default=_default_journal)
    amount = fields.Float(digits=(16, 2), required=True, default=_default_amount)
    payment_name = fields.Char(string='Payment Reference')
    payment_date = fields.Date(string='Payment Date', required=True, default=lambda *a: fields.Datetime.now())

    @api.multi
    def check(self):
        """Check the order:
        if the order is not paid: continue payment,
        if the order is paid print ticket.
        """
        self.ensure_one()
        order = self.env['pos.order'].browse(self.env.context.get('active_id', False))
        amount = order.amount_total - order.amount_paid
        data = self.read()[0]
        # this is probably a problem of osv_memory as it's not compatible with normal OSV's
        data['journal'] = data['journal_id'][0]
        if amount != 0.0:
            order.add_payment(data)
        if order.test_paid():
            order.action_pos_order_paid()
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

