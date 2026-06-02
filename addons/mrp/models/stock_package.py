from odoo import models


class StockPackage(models.Model):
    _inherit = 'stock.package'

    def _get_package_vals(self):
        vals = super()._get_package_vals()
        productions = self.move_line_ids.move_id.mapped('production_id')
        if productions:
            vals['production_id'] = productions[0].id
        return vals
