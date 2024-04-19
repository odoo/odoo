# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockPicking(models.Model):

    _inherit = 'stock.picking'

    def _get_l10n_in_sale(self):
        self.ensure_one()
        return self.sale_id
