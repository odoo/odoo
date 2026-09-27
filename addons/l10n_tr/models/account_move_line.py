from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _compute_account_id(self):
        # OVERRIDE
        super()._compute_account_id()

        for line in self.filtered(lambda l: l.company_id.country_code == 'TR'
                                  and l.move_id.move_type == 'out_refund'
                                  and l.display_type == 'product'
                                  ):
            if (product := line.product_id) and product.with_company(line.company_id).l10n_tr_default_sales_return_account_id:
                line.account_id = product.with_company(line.company_id).l10n_tr_default_sales_return_account_id
            elif (journal := line.move_id.journal_id) and journal.l10n_tr_default_sales_return_account_id:
                line.account_id = journal.l10n_tr_default_sales_return_account_id

    def copy_data(self, default=None):
        # OVERRIDE
        data_list = super().copy_data(default=default)

        # The copied account is never recomputed, so set the return account here.
        # `_reverse_moves` always sets the key; skip duplicates and cancelling reversals.
        if 'move_reverse_cancel' in self.env.context and not self.env.context['move_reverse_cancel']:
            for line, values in zip(self, data_list):
                if (
                    line.company_id.country_code == 'TR'
                    and line.move_id.move_type == 'out_invoice'
                    and line.display_type == 'product'
                    and (account := line.move_id.journal_id.l10n_tr_default_sales_return_account_id)
                ):
                    values['account_id'] = account.id

        return data_list
