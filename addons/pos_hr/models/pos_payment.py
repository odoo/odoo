from odoo import models, fields, api


class PosPayment(models.Model):
    _inherit = "pos.payment"

    cashier_id = fields.Many2one('hr.employee', string='Cashier', related='pos_order_id.cashier_id', store=True, index=True)

    @api.depends('cashier_id', 'user_id')
    def _compute_cashier(self):
        for order in self:
            if order.cashier_id:
                order.cashier = order.cashier_id.name
            else:
                order.cashier = order.cashier_id.name
