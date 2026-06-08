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
