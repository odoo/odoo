from odoo import models, fields, api


class PosPayment(models.Model):
    _inherit = "pos.payment"

    employee_id = fields.Many2one('hr.employee', string='Cashier', related='pos_order_id.employee_id', store=True, index=True)

    @api.depends('employee_id', 'user_id')
    def _compute_cashier(self):
        for order in self:
            if order.employee_id:
                order.cashier = order.employee_id.name
            else:
                order.cashier = order.user_id.name
