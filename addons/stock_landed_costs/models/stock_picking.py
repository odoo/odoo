# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Picking(models.Model):
    _inherit = "stock.picking"

    @api.depends('partner_id.name')
    @api.depends_context('landed_cost_form')
    def _compute_display_name(self):
        super()._compute_display_name()
        for picking in self:
            if self.env.context.get('landed_cost_form', False) and picking.partner_id:
                picking.display_name += f" {picking.partner_id.name}"
