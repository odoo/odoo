# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PosPrepOrder(models.Model):
    _inherit = 'pos.prep.order'

    @api.model
    def _get_lines_to_prepare(self, order):
        return super()._get_lines_to_prepare(order).filtered(lambda line: not line.product_id.is_deposit)
