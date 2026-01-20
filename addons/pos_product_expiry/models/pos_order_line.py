# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    @api.model
    def get_existing_lots(self, company_id, config_id, product_id):
        result = super().get_existing_lots(company_id, config_id, product_id)
        for lot in result:
            lot_id = lot.get('id')
            lot_recordset = self.env['stock.lot'].browse(lot_id)
            lot['expiration_date'] = lot_recordset.expiration_date
        return result
