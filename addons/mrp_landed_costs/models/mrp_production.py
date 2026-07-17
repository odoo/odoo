from odoo import models, _
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def action_reset_to_draft(self):
        landed_costs = self.env['stock.landed.cost'].sudo().search([
            ('mrp_production_ids', 'in', self.ids),
            ('state', '=', 'done'),
        ])
        if landed_costs:
            raise UserError(_("Landed Costs were already applied for this manufacture order."))
        super().action_reset_to_draft()
