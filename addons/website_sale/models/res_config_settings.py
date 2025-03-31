# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Groups
    group_delivery_invoice_address = fields.Boolean(
        string="Shipping Address",
        implied_group='account.group_delivery_invoice_address',
        group='base.group_portal,base.group_user,base.group_public',
    )
    group_show_uom_price = fields.Boolean(
        string="Base Unit Price",
        default=False,
        implied_group="website_sale.group_show_uom_price",
        group='base.group_portal,base.group_user,base.group_public',
    )
    group_product_price_comparison = fields.Boolean(
        string="Comparison Price",
        implied_group="website_sale.group_product_price_comparison",
        group='base.group_portal,base.group_user,base.group_public',
        help="Add a strikethrough price to your /shop and product pages for comparison purposes."
             "It will not be displayed if pricelists apply."
    )

    # Modules
    module_account = fields.Boolean("Invoicing")
    module_delivery_mondialrelay = fields.Boolean("Mondial Relay Connector")
    module_website_sale_autocomplete = fields.Boolean("Address Autocomplete")
    module_website_sale_comparison = fields.Boolean("Product Comparison Tool")
    module_website_sale_collect = fields.Boolean("Click & Collect")
    module_website_sale_wishlist = fields.Boolean("Wishlists")

    # Website-dependent settings
    add_to_cart_action = fields.Selection(related='website_id.add_to_cart_action', readonly=False)
    cart_recovery_mail_template = fields.Many2one(
        related='website_id.cart_recovery_mail_template_id',
        readonly=False,
    )
    cart_abandoned_delay = fields.Float(
        related='website_id.cart_abandoned_delay',
        readonly=False,
    )
    send_abandoned_cart_email = fields.Boolean(
        string="Abandoned Email",
        related='website_id.send_abandoned_cart_email',
        readonly=False,
    )
    salesperson_id = fields.Many2one(
        related='website_id.salesperson_id',
        readonly=False,
    )
    salesteam_id = fields.Many2one(related='website_id.salesteam_id', readonly=False)
    website_sale_prevent_zero_price_sale = fields.Boolean(
        string="Prevent Sale of Zero Priced Product",
        related='website_id.prevent_zero_price_sale',
        readonly=False,
    )
    website_sale_contact_us_button_url = fields.Char(
        string="Button Url",
        related='website_id.contact_us_button_url',
        readonly=False,
    )
    website_sale_enabled_portal_reorder_button = fields.Boolean(
        related='website_id.enabled_portal_reorder_button',
        readonly=False,
    )
    show_line_subtotals_tax_selection = fields.Selection(
        related='website_id.show_line_subtotals_tax_selection',
        readonly=False,
    )

    # Additional settings
    account_on_checkout = fields.Selection(
        string="Customer Accounts",
        selection=[
            ("optional", "Optional"),
            ("disabled", "Disabled (buy as guest)"),
            ("mandatory", "Mandatory (no guest checkout)"),
        ],
        compute="_compute_account_on_checkout",
        inverse="_inverse_account_on_checkout",
        readonly=False,
        required=True,
    )
    ecommerce_access = fields.Selection(
        related='website_id.ecommerce_access',
        readonly=False,
    )

    enabled_extra_checkout_step = fields.Boolean(string="Extra Step During Checkout",
                                                 compute='_compute_checkout_process_steps', readonly=False, store=True)
    enabled_buy_now_button = fields.Boolean(string="Buy Now",
                                            compute='_compute_checkout_process_steps', readonly=False, store=True)

    #=== COMPUTE METHODS ===#

    @api.depends('website_id.account_on_checkout')
    def _compute_account_on_checkout(self):
        for record in self:
            record.account_on_checkout = record.website_id.account_on_checkout or 'disabled'

    @api.depends('website_id')
    def _compute_checkout_process_steps(self):
        """
        Computing the extra info step and buy now settings when changing
        the website in the res.config.settings page to show the correct value
        in the checkbox.
        """
        for record in self:
            website = record.with_context(website_id=record.website_id.id).website_id
            record.enabled_extra_checkout_step = website.is_view_active(
                'website_sale.extra_info'
            )
            record.enabled_buy_now_button = website.is_view_active(
                'website_sale.product_buy_now'
            )

    def _inverse_account_on_checkout(self):
        for record in self:
            if not record.website_id:
                continue
            record.website_id.account_on_checkout = record.account_on_checkout
            # account_on_checkout implies different values for `auth_signup_uninvited`
            if record.account_on_checkout in ['optional', 'mandatory']:
                record.website_id.auth_signup_uninvited = 'b2c'
            else:
                record.website_id.auth_signup_uninvited = 'b2b'

    #=== CRUD METHODS ===#

    def set_values(self):
        super().set_values()
        if self.website_id:
            website = self.with_context(website_id=self.website_id.id).website_id
            extra_step_view = website.viewref('website_sale.extra_info')
            buy_now_view = website.viewref('website_sale.product_buy_now')

            if extra_step_view.active != self.enabled_extra_checkout_step:
                extra_step_view.active = self.enabled_extra_checkout_step
            if buy_now_view.active != self.enabled_buy_now_button:
                buy_now_view.active = self.enabled_buy_now_button

    #=== ACTION METHODS ===#

    def action_open_abandoned_cart_mail_template(self):
        return {
            'name': _("Customize Email Templates"),
            'type': 'ir.actions.act_window',
            'res_model': 'mail.template',
            'view_id': False,
            'view_mode': 'form',
            'res_id': self.env['ir.model.data']._xmlid_to_res_id("website_sale.mail_template_sale_cart_recovery"),
        }

    def action_open_extra_info(self):
        self.ensure_one()
        # Add the "edit" parameter in the url to tell the controller
        # that we want to edit even if we are not in a payment flow
        return self.env["website"].get_client_action(
            '/shop/extra_info?open_editor=true', mode_edit=True, website_id=self.website_id.id)

    def action_open_sale_mail_templates(self):
        return {
            'name': _("Customize Email Templates"),
            'type': 'ir.actions.act_window',
            'domain': [('model', '=', 'sale.order')],
            'res_model': 'mail.template',
            'view_id': False,
            'view_mode': 'list,form',
        }
