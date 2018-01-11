# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    payment_ids_nbr = fields.Integer(string='# of Payments', compute='_compute_payment_ids_nbr')

    @api.depends('payment_ids')
    def _compute_payment_ids_nbr(self):
        '''Compute the number of payments for each invoice in self.'''
        self.check_access_rights('write')
        self.env['account.payment'].check_access_rights('read')

        self._cr.execute('''
            SELECT inv.id, COUNT(rel.payment_id)
            FROM account_invoice inv
            LEFT JOIN account_invoice_payment_rel rel ON inv.id = rel.invoice_id
            WHERE inv.id IN %s
            GROUP BY inv.id
        ''', [tuple(self.ids)])
        records = dict((r.id, r) for r in self)
        for res in self._cr.fetchall():
            records[res[0]].payment_ids_nbr = res[1]

    @api.multi
    def get_portal_transactions(self):
        '''Retrieve the transactions to display in the portal.
        The transactions must be 'posted' (e.g. success with Paypal) or 'draft' + pending (Wire Transfer)
        but not in 'capture' (the user must capture the amount manually to get paid and set the transaction to
        'posted').

        :return: The transactions to display in the portal.
        '''
        return self.sudo().mapped('payment_ids.payment_transaction_id')\
            .filtered(lambda trans: trans.state == 'posted' or (trans.state == 'draft' and trans.pending))

    @api.multi
    def get_portal_last_transaction(self):
        return self.sudo().payment_tx_id

    def action_view_payments(self):
        action = {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'target': 'current',
        }
        payment_ids = self.mapped('payment_ids')
        if len(payment_ids) == 1:
            action['res_id'] = payment_ids.ids[0]
            action['view_mode'] = 'form'
        else:
            action['view_mode'] = 'tree,form'
            action['domain'] = [('id', 'in', payment_ids.ids)]
        return action
