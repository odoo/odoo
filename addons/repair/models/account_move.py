from odoo import fields, models


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = 'account.move'

    repair_order_id = fields.Many2one('repair.order', string='Repair Order', index='btree_not_null', copy=False)

    def action_show_repair(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'repair.order',
            'views': [[False, 'form']],
            'res_id': self.repair_order_id.id,
        }
