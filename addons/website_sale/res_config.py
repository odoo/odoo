# -*- encoding: utf-8 -*-
from openerp import models, fields
from openerp.addons.sale.res_config import sale_configuration

class website_sale_configuration(models.TransientModel):
    _inherit = 'sale.config.settings'

    module_website_sale_digital = fields.Boolean('Sell digital products', 
        help="Allow you to set mark a product as a digital product, allowing customers that have purchased the product to download its attachments. This installs the module website_sale_digital.")
    module_website_sale_coupon = fields.Boolean(string='Pre Sale Voucher',
        help='- Allocates a coupon code to Customer which can be applied on successive purchase(s) of a particular Product.\n'
        '- This installs the module website_sale_coupon.')
