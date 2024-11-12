from odoo import api, Command, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    @api.model_create_multi
    def create(self, vals_list):
        # EXTENDS account - ensure there is a tag on created MX accounts
        # The computation is a bit naive and might not be correct in all cases.
        accounts = super().create(vals_list)
        debit_tag = self.env.ref('l10n_mx.tag_debit_balance_account')
        credit_tag = self.env.ref('l10n_mx.tag_credit_balance_account')
        mx_account_no_tags = accounts.filtered(lambda a: 'MX' in a.company_ids.mapped('country_code') and not a.tag_ids & (credit_tag + debit_tag))
        DEBIT_CODES = ['1', '5', '6', '7']  # all other codes are considered "credit"
        for account in mx_account_no_tags:
            tag_id = debit_tag.id if account.code[0] in DEBIT_CODES else credit_tag.id
            account.tag_ids = [Command.link(tag_id)]
        return accounts
