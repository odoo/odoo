from odoo import fields, models


class PointOfSaleConfig(models.Model):
    _name = "point_of_sale.config"
    _description = "A company's point of sale configuration"
    _inherit = ["mixin.company.config"]

    point_of_sale_update_stock_quantities = fields.Selection(
        selection=[
            ("closing", "At the session closing"),
            ("real", "In real time"),
        ],
        string="Update quantities in stock",
        default="real",
        help="At the session closing: A picking is created for the entire session when it's closed\n In real time: Each order sent to the server create its own picking",
    )
    point_of_sale_use_ticket_qr_code = fields.Boolean(
        string="Self-service invoicing",
        default=True,
        help="Print information on the receipt to allow the customer to easily access the invoice anytime, from Odoo's portal.",
    )
    point_of_sale_ticket_unique_code = fields.Boolean(
        string="Generate a code on ticket",
        help="Add a 5-digit code on the receipt to allow the user to request the invoice for an order on the portal.",
    )
    point_of_sale_ticket_portal_url_display_mode = fields.Selection(
        selection=[
            ("qr_code", "QR code"),
            ("url", "URL"),
            ("qr_code_and_url", "QR code + URL"),
        ],
        string="Print",
        default="qr_code_and_url",
        required=True,
        help="Choose how the URL to the portal will be print on the receipt.",
    )
