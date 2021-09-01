from odoo import models, fields, api


class MarketplaceProduct(models.Model):
    _name = 'aumet.marketplace_product'

    name = fields.Char(string="Name")
    unit_price = fields.Float(string="Unit Price")
    marketplace_seller_id = fields.Integer(string="Seller id")
    is_archived = fields.Boolean(string="is archived")
    is_locked = fields.Boolean(string="is archived")
    marketplace_id = fields.Integer(string="Marketplace id")
    uom = fields.Char(string="Unit of measure")
