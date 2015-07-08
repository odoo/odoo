# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from openerp import api, fields, models, _


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        session_id = self.env.context.get('pos_session_id', False) or False

        if session_id:
            session = self.env['pos.session'].browse(session_id)

            if session:
                journal_ids = [journal.id for journal in session.config_id.journal_ids]
                args += [('id', 'in', journal_ids)]

        return super(AccountJournal, self).search(args, offset=offset, limit=limit, order=order, count=count)


class PosMakePayment(models.TransientModel):
    _name = 'pos.make.payment'
    _description = 'Point of Sale Payment'

    def _default_journal(self):
        session = False
        active_id = self.env.context.get('active_id', False)
        if active_id:
            order_id = self.env['pos.order'].browse(active_id)
            session = order_id.session_id
        if session:
            for journal in session.config_id.journal_ids:
                return journal.id
        return False

    def _default_amount(self):
        active_id = self.env.context.get('active_id', False)
        if active_id:
            order_id = self.env['pos.order'].browse(active_id)
            return order_id.amount_total - order_id.amount_paid
        return False

    journal_id = fields.Many2one('account.journal', string='Payment Mode', required=True, default=_default_journal)
    amount = fields.Float(string='Amount', digits=(16, 2), required=True, default=_default_amount)
    payment_name = fields.Char(string='Payment Reference')
    payment_date = fields.Date(string='Payment Date', required=True, default=lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'))

    @api.multi
    def check(self):
        """Check the order:
        if the order is not paid: continue payment,
        if the order is paid print ticket.
        """
        self.ensure_one()
        active_id = self.env.context.get('active_id', False)
        pos_order = self.env['pos.order']
        order_id = pos_order.browse(active_id)
        amount = order_id.amount_total - order_id.amount_paid
        data = self.read()[0]
        # this is probably a problem of osv_memory as it's not compatible with normal OSV's
        data['journal'] = data['journal_id'][0]

        if amount != 0.0:
            pos_order.add_payment(order_id.id, data)

        if order_id.test_paid():
            order_id.signal_workflow('paid')
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
        active_id = self.env.context.get('active_id', [])
        datas = {'ids': [active_id]}
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'pos.receipt',
            'datas': datas,
        }