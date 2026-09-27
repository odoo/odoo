from odoo import models


class AccountPartialReconcile(models.Model):
    _inherit = 'account.partial.reconcile'

    def _create_tax_cash_basis_moves(self):
        res = super()._create_tax_cash_basis_moves()
        res._create_l10n_th_tax_invoices_from_caba_entries()
        return res
