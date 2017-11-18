# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def _default_order_mail_template(self):
        if self.env['ir.module.module'].search([('name', '=', 'website_quote')]).state in ('installed', 'to upgrade'):
            return self.env.ref('website_quote.confirmation_mail').id
        else:
            return self.env.ref('sale.email_template_edi_sale').id

    def _default_recovery_mail_template(self):
        try:
            return self.env.ref('website_sale.mail_template_sale_cart_recovery').id
        except ValueError:
            return False

    salesperson_id = fields.Many2one('res.users', related='website_id.salesperson_id', string='Salesperson')
    salesteam_id = fields.Many2one('crm.team', related='website_id.salesteam_id', string='Sales Channel', domain=[('team_type', '!=', 'pos')])
    module_website_sale_delivery = fields.Boolean("Shipping Costs")
    # field used to have a nice radio in form view, resuming the 2 fields above
    sale_delivery_settings = fields.Selection([
        ('none', 'No shipping management on website'),
        ('internal', "Delivery methods are only used internally: the customer doesn't pay for shipping costs"),
        ('website', "Delivery methods are selectable on the website: the customer pays for shipping costs"),
        ], string="Shipping Management")

    group_website_multiimage = fields.Boolean(string='Multi-Images', implied_group='website_sale.group_website_multi_image', group='base.group_portal,base.group_user,base.group_public')
    group_delivery_invoice_address = fields.Boolean(string="Shipping Address", implied_group='sale.group_delivery_invoice_address')

    module_website_sale_options = fields.Boolean("Optional Products")
    module_website_sale_digital = fields.Boolean("Digital Content")
    module_website_sale_wishlist = fields.Boolean("Wishlists")
    module_website_sale_comparison = fields.Boolean("Product Comparison Tool")
    module_website_sale_stock = fields.Boolean("Inventory", help='Installs *e-Commerce Inventory*')

    module_account_invoicing = fields.Boolean("Invoicing")

    order_mail_template = fields.Many2one('mail.template', string='Order Confirmation Email',
        default=_default_order_mail_template, domain="[('model', '=', 'sale.order')]",
        help="Email sent to customer at the end of the checkout process")

    automatic_invoice = fields.Boolean("Automatic Invoice")

    module_l10n_eu_service = fields.Boolean(string="EU Digital Goods VAT")

    cart_recovery_mail_template = fields.Many2one('mail.template', string='Cart Recovery Email',
        default=_default_recovery_mail_template, domain="[('model', '=', 'sale.order')]")
    cart_abandoned_delay = fields.Float("Abandoned Delay", default=1.0, help="number of hours after which the cart is considered abandoned")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()

        sale_delivery_settings = 'none'
        if self.env['ir.module.module'].search([('name', '=', 'delivery')], limit=1).state in ('installed', 'to install', 'to upgrade'):
            sale_delivery_settings = 'internal'
            if self.env['ir.module.module'].search([('name', '=', 'website_sale_delivery')], limit=1).state in ('installed', 'to install', 'to upgrade'):
                sale_delivery_settings = 'website'

        cart_recovery_mail_template = literal_eval(params.get_param('website_sale.cart_recovery_mail_template_id', default='False'))
        if cart_recovery_mail_template and not self.env['mail.template'].browse(cart_recovery_mail_template).exists():
            cart_recovery_mail_template = self._default_recovery_mail_template()

        res.update(
            automatic_invoice=params.get_param('website_sale.automatic_invoice', default=False),
            sale_delivery_settings=sale_delivery_settings,
            cart_recovery_mail_template=cart_recovery_mail_template,
            cart_abandoned_delay=float(params.get_param('website_sale.cart_abandoned_delay', '1.0'))
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        value = self.module_account_invoicing and self.default_invoice_policy == 'order' and self.automatic_invoice
        self.env['ir.config_parameter'].sudo().set_param('website_sale.automatic_invoice', value)
        self.env['ir.config_parameter'].sudo().set_param('website_sale.cart_recovery_mail_template_id', self.cart_recovery_mail_template.id)
        self.env['ir.config_parameter'].sudo().set_param('website_sale.cart_abandoned_delay', self.cart_abandoned_delay)

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
                'multi_sales_price': True,
            })
