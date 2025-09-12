from odoo import fields, models


class PurchaseOrderResponse(models.Model):
    _name = 'purchase.order.response'
    _description = 'Response received via PEPPOL network on a submitted purchase order'

    supplier_sales_order_id = fields.Char("Supplier Side Sales Order ID")
    issue_date = fields.Datetime("Issue Date")
    sequence_number_id = fields.Integer()
    status = fields.Selection([
        ('AB', 'Acknowledged'),
        ('AP', 'Accepted'),
        ('RE', 'Rejected'),
        ('CA', 'Conditionally Accepted'),
    ])
