# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models, fields, _


class RepairOrder(models.Model):
    _inherit = 'repair.order'

    purchase_count = fields.Integer(string="Count of generated POs", compute="_compute_purchase_count", groups="purchase.group_purchase_user")

    @api.depends('move_ids.created_purchase_line_ids.order_id')
    def _compute_purchase_count(self):
        for repair in self:
            repair.purchase_count = len(repair.move_ids.created_purchase_line_ids.order_id)

    def action_view_purchase_orders(self):
        self.ensure_one()
        purchase_ids = self.move_ids.created_purchase_line_ids.order_id
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'views': [[False, 'form']],
        }
        if self.purchase_count == 1:
            action['res_id'] = purchase_ids.id
        elif self.purchase_count > 1:
            action['name'] = _('Purchase Orders')
            action['views'] = [[False, 'list']]
            action['domain'] = [('id', 'in', purchase_ids.ids)]
        return action
