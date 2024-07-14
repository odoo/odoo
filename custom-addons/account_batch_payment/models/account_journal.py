# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _default_inbound_payment_methods(self):
        res = super()._default_inbound_payment_methods()
        if self._is_payment_method_available('batch_payment'):
            res |= self.env.ref('account_batch_payment.account_payment_method_batch_deposit')
        return res

    @api.model
    def _create_batch_payment_outbound_sequence(self):
        IrSequence = self.env['ir.sequence']
        if IrSequence.search([('code', '=', 'account.outbound.batch.payment')]):
            return
        return IrSequence.sudo().create({
            'name': _("Outbound Batch Payments Sequence"),
            'padding': 4,
            'code': 'account.outbound.batch.payment',
            'number_next': 1,
            'number_increment': 1,
            'use_date_range': True,
            'prefix': 'BATCH/OUT/%(year)s/',
            #by default, share the sequence for all companies
            'company_id': False,
        })

    @api.model
    def _create_batch_payment_inbound_sequence(self):
        IrSequence = self.env['ir.sequence']
        if IrSequence.search([('code', '=', 'account.inbound.batch.payment')]):
            return
        return IrSequence.sudo().create({
            'name': _("Inbound Batch Payments Sequence"),
            'padding': 4,
            'code': 'account.inbound.batch.payment',
            'number_next': 1,
            'number_increment': 1,
            'use_date_range': True,
            'prefix': 'BATCH/IN/%(year)s/',
            #by default, share the sequence for all companies
            'company_id': False,
        })

    def open_action_batch_payment(self):
        ctx = self._context.copy()
        ctx.update({'journal_id': self.id, 'default_journal_id': self.id})
        return {
            'name': _('Create Batch Payment'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.batch.payment',
            'context': ctx,
        }
