from odoo import models


class AccountDebitNote(models.TransientModel):
    _inherit = 'account.debit.note'

    def _prepare_default_values(self, move):
        default_values = super()._prepare_default_values(move)
        if move.company_id.account_fiscal_country_id.code == "HU":
            default_values.update({
                'delivery_date': move.delivery_date
            })
        return default_values
