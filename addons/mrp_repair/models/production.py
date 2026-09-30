# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    repair_count = fields.Integer(
        string='Count of source repairs',
        compute='_compute_repair_count',
        groups='stock.group_stock_user',
    )

    @api.depends('move_dest_ids.repair_id')
    def _compute_repair_count(self):
        for production in self:
            production.repair_count = len(production.move_dest_ids.repair_id)

    def action_view_repair_orders(self):
        self.ensure_one()
        repair_ids = self.move_dest_ids.repair_id
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'repair.order',
            'views': [[False, 'form']],
        }
        if self.repair_count == 1:
            action['res_id'] = repair_ids.id
        elif self.repair_count > 1:
            action['name'] = _("Repair Source of %s", self.name)
            action['views'] = [[False, 'list']]
            action['domain'] = [('id', 'in', repair_ids.ids)]
        return action
