from odoo import models, fields, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    bonus = fields.Integer("Bonus")
    payment_method = fields.Many2one("aumet.payment_method", string="payment method")

    @api.depends("product_id")
    def calculate_possible_payment_methods(self):
        payment_methods = self.env["aumet.payment_method"].search([])

        return [(i.marketplace_payment_method_id, i.name)for i in payment_methods]

