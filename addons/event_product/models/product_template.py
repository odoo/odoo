from odoo import fields, models
from odoo.addons import account, product


class ProductTemplate(product.ProductTemplate, account.ProductTemplate):

    service_tracking = fields.Selection(selection_add=[
        ('event', 'Event Registration'),
    ], ondelete={'event': 'set default'})
