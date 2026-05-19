from odoo import api, Command, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    @api.model_create_multi
    def create(self, vals_list):
        # EXTENDS account - ensure there is a tag on created MX accounts
        # The computation is a bit naive and might not be correct in all cases.
        accounts = super().create(vals_list)
        debit_tag = self.env.ref('l10n_mx.tag_debit_balance_account', raise_if_not_found=False)
        credit_tag = self.env.ref('l10n_mx.tag_credit_balance_account', raise_if_not_found=False)
        if not debit_tag or not credit_tag:
            return accounts
        mx_account_no_tags = accounts.filtered(
            lambda a: 'MX' in a.company_ids.mapped('country_code') and a.internal_group != 'off'
            and not a.tag_ids & (credit_tag + debit_tag)
        )
        DEBIT_GROUPS = ('asset', 'expense')  # remaining groups are considered "credit"
        for account in mx_account_no_tags:
            tag_id = debit_tag.id if account.internal_group in DEBIT_GROUPS else credit_tag.id
            account.tag_ids = [Command.link(tag_id)]
        return accounts
