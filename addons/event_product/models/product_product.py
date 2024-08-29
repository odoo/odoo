from odoo import fields, models
from odoo.addons import product


class ProductProduct(models.Model, product.ProductProduct):

    event_ticket_ids = fields.One2many('event.event.ticket', 'product_id', string='Event Tickets')
