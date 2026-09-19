from odoo import fields, models


class PosPayment(models.Model):
    _inherit = "pos.payment"

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        related="pos_order_id.employee_id",
        string="Cashier",
    )
