from odoo import models, fields


class MarketplaceDistributor(models.Model):
    _name = 'aumet.marketplace_distributor'
    name = fields.Char(string="Distributor ")
    country_id = fields.Integer("Country ID")
