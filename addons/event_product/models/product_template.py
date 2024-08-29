from odoo import fields, models
from odoo.addons import product


class ProductTemplate(models.Model, product.ProductTemplate):

    service_tracking = fields.Selection(selection_add=[
        ('event', 'Event Registration'),
    ], ondelete={'event': 'set default'})
