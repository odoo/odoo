# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, models


class AccountPartialReconcileCashBasis(models.Model):
    _inherit = 'account.partial.reconcile'

    def _get_tax_cash_basis_base_account(self, line, tax):
        if tax.cash_basis_base_account_id:
            return tax.cash_basis_base_account_id
        return super(AccountPartialReconcileCashBasis, self)._get_tax_cash_basis_base_account(line, tax)
