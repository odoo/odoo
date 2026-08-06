from odoo import models
from odoo.tools import float_round


class AccountTax(models.Model):
    _inherit = 'account.tax'

    def _l10n_tr_get_withholding_ratio(self):
        """Return the VAT fraction these taxes withhold (tevkifat), 0 unless it is unique.

        A withholding tax groups the plain VAT with the negative withheld part, so a
        9/10 withholding groups +20% and -18% and yields 0.9. An invoice reports a single
        withholding reason, so taxes withholding at different ratios have no ratio.
        """
        ratios = set()
        for tax in self:
            children = tax.children_tax_ids
            base_amount = sum(child.amount for child in children if child.amount > 0)
            withheld_amount = sum(child.amount for child in children if child.amount < 0)
            if base_amount and withheld_amount:
                # Ratio compares to a GİB code's percentage, needs rounding:
                ratios.add(float_round(-withheld_amount / base_amount, precision_digits=4))
        return ratios.pop() if len(ratios) == 1 else 0.0
