from odoo import models, fields


class MarketplaceProduct(models.Model):
    _name = 'aumet.marketplace_product'
    name = fields.Char(string="Name")
    unit_price = fields.Float(string="Unit Price")
    marketplace_distributor = fields.Many2one('aumet.marketplace_distributor', string="Distributor")
    is_archived = fields.Boolean(string="is archived")
    is_locked = fields.Boolean(string="is archived")
    uom = fields.Char(string="Unit of measure")
