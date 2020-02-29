# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def _default_recovery_mail_template(self):
        try:
            return self.env.ref('website_sale.mail_template_sale_cart_recovery').id
        except ValueError:
            return False

    salesperson_id = fields.Many2one('res.users', related='website_id.salesperson_id', string='Salesperson', readonly=False)
    salesteam_id = fields.Many2one('crm.team', related='website_id.salesteam_id', string='Sales Team', readonly=False)
    module_website_sale_delivery = fields.Boolean("eCommerce Shipping Costs")
    # field used to have a nice radio in form view, resuming the 2 fields above
    sale_delivery_settings = fields.Selection([
        ('none', 'No shipping management on website'),
        ('internal', "Delivery methods are only used internally: the customer doesn't pay for shipping costs"),
        ('website', "Delivery methods are selectable on the website: the customer pays for shipping costs"),
    ], string="Shipping Management")

    group_delivery_invoice_address = fields.Boolean(string="Shipping Address", implied_group='sale.group_delivery_invoice_address', group='base.group_portal,base.group_user,base.group_public')

    module_website_sale_digital = fields.Boolean("Digital Content")
    module_website_sale_wishlist = fields.Boolean("Wishlists")
    module_website_sale_comparison = fields.Boolean("Product Comparison Tool")
    module_website_sale_stock = fields.Boolean("Inventory", help='Installs the "Website Delivery Information" application')

    module_account = fields.Boolean("Invoicing")

    cart_recovery_mail_template = fields.Many2one('mail.template', string='Cart Recovery Email', domain="[('model', '=', 'sale.order')]",
                                                  default=_default_recovery_mail_template, related='website_id.cart_recovery_mail_template_id', readonly=False)
    cart_abandoned_delay = fields.Float("Abandoned Delay", help="Number of hours after which the cart is considered abandoned.",
                                        default=1.0, related='website_id.cart_abandoned_delay', readonly=False)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()

        sale_delivery_settings = 'none'
        if self.env['ir.module.module'].search([('name', '=', 'delivery')], limit=1).state in ('installed', 'to install', 'to upgrade'):
            sale_delivery_settings = 'internal'
            if self.env['ir.module.module'].search([('name', '=', 'website_sale_delivery')], limit=1).state in ('installed', 'to install', 'to upgrade'):
                sale_delivery_settings = 'website'

        res.update(
            sale_delivery_settings=sale_delivery_settings,
        )
        return res

    @api.onchange('sale_delivery_settings')
    def _onchange_sale_delivery_settings(self):
        if self.sale_delivery_settings == 'none':
            self.update({
                'module_delivery': False,
                'module_website_sale_delivery': False,
            })
        elif self.sale_delivery_settings == 'internal':
            self.update({
                'module_delivery': True,
                'module_website_sale_delivery': False,
            })
        else:
            self.update({
                'module_delivery': True,
                'module_website_sale_delivery': True,
            })

    @api.onchange('group_discount_per_so_line')
    def _onchange_group_discount_per_so_line(self):
        if self.group_discount_per_so_line:
            self.update({
                'group_product_pricelist': True,
            })
