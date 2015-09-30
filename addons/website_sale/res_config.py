# -*- encoding: utf-8 -*-
from openerp import models, fields

class website_config_settings(models.TransientModel):
    _inherit = 'website.config.settings'

    salesperson_id = fields.Many2one('res.users', related='website_id.salesperson_id', string='Salesperson')
    salesteam_id = fields.Many2one('crm.team', related='website_id.salesteam_id', string='Sales Team')
    module_delivery_dhl = fields.Boolean("DHL integration")
    module_delivery_fedex = fields.Boolean("Fedex integration")
    module_delivery_ups = fields.Boolean("UPS integration")
    module_delivery_usps = fields.Boolean("USPS integration")
    module_sale_ebay = fields.Boolean("eBay connector")
