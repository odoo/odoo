from odoo import _, api, models
from odoo.exceptions import UserError


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    @api.onchange('sequence_code')
    def _onchange_sequence_code(self):
        if (
            self.company_id.account_fiscal_country_id.code == 'TR'
            and self.code == 'outgoing'
            and self.sequence_code
            and len(self.sequence_code) != 3
        ):
            raise UserError(_("Only 3 characters are allowed in the Sequence Prefix by GİB"))
        return super()._onchange_sequence_code()
