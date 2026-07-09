# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_source_document(self):
        return self.production_id or self.raw_material_production_id or super()._get_source_document()
