from odoo import models, fields


class AccountMoveLine(models.Model):

    _inherit = 'account.move.line'

    def _get_computed_taxes(self):
        taxes = super()._get_computed_taxes()
        # heredamos este metodo y no map_tax de fiscal positions porque el metod map_tax recibe solo taxes y no sabe
        # partner ni fecha y estos datos son necesarios para computar correctamente la alicuota
        if self.move_id.is_sale_document(include_receipts=True) and self.move_id.fiscal_position_id.l10n_ar_tax_ids:
            date = self.move_id.date
            taxes += self.move_id.fiscal_position_id._l10n_ar_add_taxes(self.partner_id, self.company_id, date)
        return taxes

