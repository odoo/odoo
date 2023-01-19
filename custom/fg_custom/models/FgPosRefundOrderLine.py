from odoo import fields, models


class PosOrderLineInherit(models.Model):
    _inherit = "pos.order.line"
    _description = "Refund Report"

    refund_reference_number = fields.Char(related='order_id.pos_refund_si_reference', string='Refund Reference Number', store=True)
