# -*- coding: utf-8 -*-

from odoo import models


class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"

    def _get_tax_cash_basis_base_key(self, tax, move, line):
        account_id = self._get_tax_cash_basis_base_account(line, tax)
        return (move.id, account_id.id, tax.id, line.currency_id.id, line.partner_id.id)

    def _get_tax_cash_basis_base_common_vals(self, key, new_move):
        move, account_id, tax, currency_id, partner_id = key
        move = self.env['account.move'].browse(move)
        return {
            'name': move.name,
            'account_id': account_id,
            'tax_exigible': True,
            'tax_ids': [(6, 0, [tax])],
            'move_id': new_move.id,
            'currency_id': currency_id,
            'partner_id': partner_id,
        }
