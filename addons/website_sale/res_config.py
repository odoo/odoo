# -*- encoding: utf-8 -*-
from openerp import models, fields
from openerp.addons.sale.res_config import sale_configuration

class website_sale_configuration(models.TransientModel):
    _inherit = 'sale.config.settings'

    module_website_sale_digital = fields.Boolean('Sell digital products', 
        help="Allow you to set mark a product as a digital product, allowing customers that have purchased the product to download its attachments. This installs the module website_sale_digital.")


class website_config_settings(models.TransientModel):
    _inherit = 'website.config.settings'

    salesperson_id = fields.Many2one('res.users', related='website_id.salesperson_id', string='Salesperson')
    salesteam_id = fields.Many2one('crm.team', related='website_id.salesteam_id', string='Sales Team')
