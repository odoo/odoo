# -*- encoding: utf-8 -*-
from openerp import models, fields

class website_config_settings(models.TransientModel):
    _inherit = 'website.config.settings'

    salesperson_id = fields.Many2one('res.users', related='website_id.salesperson_id', string='Salesperson')
    salesteam_id = fields.Many2one('crm.team', related='website_id.salesteam_id', string='Sales Team')
    module_delivery_fedex = fields.Selection([
            (0, "Do not activate the Fedex integration"),
            (1, "Activate the Fedex integration"),
            ], "Fedex Integration")
    module_delivery_ups = fields.Selection([
            (0, "Do not activate the UPS integration"),
            (1, "Activate the UPS integration"),
            ], "UPS Integration")
    module_delivery_usps = fields.Selection([
            (0, "Do not activate the USPS integration"),
            (1, "Activate the USPS integration"),
            ], "USPS Integration")
    module_sale_ebay = fields.Selection([
            (0, "Do not activate the eBay connector"),
            (1, "Activate the eBay connector"),
            ], "eBay connector")
