# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models, fields


class AccountPayment(models.Model):
    _inherit = "account.payment"

    l10n_ca_cpa005_transaction_code_id = fields.Many2one(
        "l10n_ca_cpa005.transaction.code",
        string="EFT/CPA transaction code",
        help="Select the option that better represents the type/purpose of the payment. Every payment initiated using the "
        "Canadian EFT service must include a valid CPA code.",
    )

    @api.model
    def _get_method_codes_using_bank_account(self):
        return super()._get_method_codes_using_bank_account() + ["cpa005"]

    @api.model
    def _get_method_codes_needing_bank_account(self):
        return super()._get_method_codes_needing_bank_account() + ["cpa005"]
