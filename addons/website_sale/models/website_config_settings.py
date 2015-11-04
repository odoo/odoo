# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields

class WebsiteConfigSettings(models.TransientModel):
    _inherit = 'website.config.settings'

    salesperson_id = fields.Many2one('res.users', related='website_id.salesperson_id', string='Salesperson')
    salesteam_id = fields.Many2one('crm.team', related='website_id.salesteam_id', string='Sales Team')
    module_delivery_dhl = fields.Boolean(string='DHL integration')
    module_delivery_fedex = fields.Boolean(string='Fedex integration')
    module_delivery_temando = fields.Boolean(string='Temando integration')
    module_delivery_ups = fields.Boolean(string='UPS integration')
    module_delivery_usps = fields.Boolean(string='USPS integration')
    module_sale_ebay = fields.Boolean(string='eBay connector')
