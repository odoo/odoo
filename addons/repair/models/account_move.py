# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.exceptions import UserError


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

    def button_draft(self):
        draft_invoices = self.repair_order_id.invoice_ids.filtered(lambda move: move.state == 'draft')
        if draft_invoices:
            raise UserError(self.env._('You can only have one invoice linked to a repair order.'))
        super().button_draft()
