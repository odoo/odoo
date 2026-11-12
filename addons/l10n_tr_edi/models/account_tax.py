from odoo import models
from odoo.tools import float_compare, float_is_zero, float_round


class AccountTax(models.Model):
    _inherit = 'account.tax'

    def _l10n_tr_get_withholding_ratio(self):
        """Return the VAT fraction these taxes withhold (tevkifat), 0 unless it is unique.

        A withholding tax groups the plain VAT with the negative withheld part, so a
        9/10 withholding groups +20% and -18% and yields 0.9. An invoice reports a single
        withholding reason, so taxes withholding at different ratios have no ratio.
        """
        ratios = set()
        # An archived tax still withholds on the entries that carry it, and its withheld
        # child is archived with it, so the children have to be read past `active`.
        for tax in self.with_context(active_test=False):
            amounts = tax.children_tax_ids.mapped('amount')
            # `account.tax.amount` is declared with digits=(16, 4), so compare on four.
            base_amount = sum(a for a in amounts if float_compare(a, 0, precision_digits=4) > 0)
            withheld_amount = sum(a for a in amounts if float_compare(a, 0, precision_digits=4) < 0)
            if not float_is_zero(base_amount, precision_digits=4) and not float_is_zero(withheld_amount, precision_digits=4):
                # Ratio compares to a GİB code's percentage, needs rounding:
                ratios.add(float_round(-withheld_amount / base_amount, precision_digits=4))
        return ratios.pop() if len(ratios) == 1 else 0.0
