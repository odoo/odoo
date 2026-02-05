# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_new_picking_values(self):
        vals = super()._get_new_picking_values()
        if project_id := self.env.context.get('project_id'):
            vals['project_id'] = project_id
        return vals
