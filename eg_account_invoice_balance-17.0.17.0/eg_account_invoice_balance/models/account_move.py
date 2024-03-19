from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = "account.move"

    customer_credit = fields.Float(string="Customer Credit", compute="_compute_customer_credit")
    print_customer_credit_on_invoice = fields.Boolean(string="Print Customer Credit")

    @api.depends("invoice_line_ids.product_id", "invoice_line_ids.quantity")
    def _compute_customer_credit(self):
        for invoice_id in self:
            customer_credit = 0
            move_line_ids = self.env["account.move.line"].search([("partner_id", "=", self.partner_id.id)])
            for line_id in move_line_ids:
                customer_credit += line_id.credit
            invoice_id.customer_credit = customer_credit