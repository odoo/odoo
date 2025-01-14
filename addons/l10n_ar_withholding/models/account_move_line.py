from odoo import models


class AccountMoveLine(models.Model):

    _inherit = 'account.move.line'

    def _get_computed_taxes(self):
        """
        Compute the taxes for the account move line, including additional taxes
        based on the fiscal position for sales documents.

        This method extends the base `_get_computed_taxes` to include additional
        taxes (e.g., perceptions) defined in the fiscal position. It ensures that
        the partner, company, and date are considered when computing the correct
        tax rates.

        Returns:
            taxes (account.tax): The computed taxes, including any additional
            taxes added based on the fiscal position.
        """
        taxes = super()._get_computed_taxes()
        # We inherit this method and not map_tax from fiscal positions because the map_tax method only receives taxes
        # and does not know the partner or date, and this data is necessary to correctly compute the tax alicuot.
        if self.move_id.is_sale_document(include_receipts=True) and self.move_id.fiscal_position_id.l10n_ar_tax_ids:
            date = self.move_id.date
            taxes += self.move_id.fiscal_position_id._l10n_ar_add_taxes(self.partner_id, self.company_id, date, 'perception')
        return taxes
