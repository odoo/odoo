# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'unalterable.hash.mixin']

    @api.model
    def _get_unalterable_fields(self):
        # Override
        return ['state', 'date', 'journal_id', 'company_id']

    @api.multi
    def _is_object_unalterable(self):
        # Override
        return self.company_id._is_accounting_unalterable() and self.state == 'posted'


class AccountMoveLine(models.Model):
    _name = 'account.move.line'
    _inherit = ['account.move.line', 'unalterable.fields.mixin']

    @api.model
    def _get_unalterable_fields(self):
        # Override
        return ['debit', 'credit', 'account_id', 'partner_id']

    @api.multi
    def _is_object_unalterable(self):
        # Override
        return self.move_id._is_object_unalterable()
