from odoo import fields, models
from odoo.addons import account, product


class ProductProduct(product.ProductProduct, account.ProductProduct):

    event_ticket_ids = fields.One2many('event.event.ticket', 'product_id', string='Event Tickets')
