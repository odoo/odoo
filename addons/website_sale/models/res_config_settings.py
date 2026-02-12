# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Groups
    group_show_uom_price = fields.Boolean(
        string="Base Unit Price",
        default=False,
        implied_group="website_sale.group_show_uom_price",
        group='base.group_user',
    )
    group_product_price_comparison = fields.Boolean(
        string="Comparison Price",
        implied_group="website_sale.group_product_price_comparison",
        group='base.group_user',
        help="Add a strikethrough price to your /shop and product pages for comparison purposes."
             "It will not be displayed if pricelists apply."
    )
    group_gmc_feed = fields.Boolean(
        string="Google Merchant Center",
        implied_group='website_sale.group_product_feed',
        group='base.group_user',
    )
    group_suggested_products = fields.Boolean(
        string="Automate suggested products",
        help="Dynamically add optional, accessory and alternative products.",
        implied_group='website_sale.group_suggested_products',
        group='base.group_user',
    )

    # Modules
    module_website_sale_autocomplete = fields.Boolean("Address Autocomplete")
    module_website_sale_collect = fields.Boolean("Click & Collect")

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
    prevent_sale = fields.Boolean(related='website_id.prevent_sale', readonly=False)
    prevent_sale_for = fields.Selection(related='website_id.prevent_sale_for', readonly=False)
    prevent_sale_for_categories = fields.Many2many(
        related='website_id.prevent_sale_for_categories',
        readonly=False,
    )
    contact_us_link_url = fields.Char(related='website_id.contact_us_link_url', readonly=False)
    show_line_subtotals_tax_selection = fields.Selection(
        related='website_id.show_line_subtotals_tax_selection',
        readonly=False,
    )
    confirmation_email_template_id = fields.Many2one(
        related='website_id.confirmation_email_template_id', readonly=False
    )

    # Additional settings
    account_on_checkout = fields.Selection(
        string="Customer Accounts",
        selection=[
            ("optional", "Optional"),
            ("disabled", "Disabled"),
            ("mandatory", "Mandatory"),
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

    # === COMPUTE METHODS === #

    @api.depends('website_id.account_on_checkout')
    def _compute_account_on_checkout(self):
        for record in self:
            record.account_on_checkout = record.website_id.account_on_checkout or 'disabled'

    def _inverse_account_on_checkout(self):
        for record in self:
            if not record.website_id:
                continue
            # account_on_checkout implies different values for `auth_signup_uninvited`
            if record.website_id.account_on_checkout != record.account_on_checkout:
                if self.account_on_checkout in ['optional', 'mandatory']:
                    record.website_id.auth_signup_uninvited = 'b2c'
                else:
                    record.website_id.auth_signup_uninvited = 'b2b'
            record.website_id.account_on_checkout = record.account_on_checkout

    # === CRUD METHODS === #

    def set_values(self):
        super().set_values()
        if self.website_id:
            website = self.with_context(website_id=self.website_id.id).website_id

            # Pre-populate the website feeds if none already exists.
            if (
                self.group_gmc_feed
                and not self.env['product.feed'].search_count(
                    [('website_id', '=', website.id)], limit=1
                )
            ):
                website._populate_product_feeds()

        # Activate / deactivate the automation of suggested products
        suggested_products_cron = (
            self.env['ir.cron'].sudo().env.ref('website_sale.ir_cron_update_suggested_products')
        )
        if self.group_suggested_products and not suggested_products_cron.active:
            self._set_products_to_suggest()
            suggested_products_cron.active = True
            suggested_products_cron._trigger()
        elif not self.group_suggested_products and suggested_products_cron.active:
            suggested_products_cron.active = False

    def _set_products_to_suggest(self):
        products = (
            self.env['product.template']
            .sudo()  # TODO why?
            .search([('is_published', '=', True), ('sale_ok', '=', True)])
        )
        # Don't erase existing optional, accessory, alternative products when enabling the feature.
        products.filtered_domain([('optional_product_ids', '=', None)]).write({
            'suggest_optional_products': True
        })
        products.filtered_domain([('accessory_product_ids', '=', None)]).write({
            'suggest_accessory_products': True
        })
        products.filtered_domain([('alternative_product_ids', '=', None)]).write({
            'suggest_alternative_products': True
        })

    # === ACTION METHODS === #

    def action_view_delivery_provider_modules(self):
        return self.env['delivery.carrier'].install_more_provider()

    @api.readonly
    def action_open_abandoned_cart_mail_template(self):
        return {
            'name': self.env._("Customize Email Templates"),
            'type': 'ir.actions.act_window',
            'res_model': 'mail.template',
            'view_id': False,
            'view_mode': 'form',
            'res_id': self.env['ir.model.data']._xmlid_to_res_id("website_sale.mail_template_sale_cart_recovery"),
        }

    @api.readonly
    def action_open_sale_mail_templates(self):
        return {
            'name': self.env._("Customize Email Templates"),
            'type': 'ir.actions.act_window',
            'domain': [('model', '=', 'sale.order')],
            'res_model': 'mail.template',
            'view_id': False,
            'view_mode': 'list,form',
        }

    @api.readonly
    def action_open_product_feeds(self):
        """Open the list view to manage the feed specific to the current website."""
        self.ensure_one()
        return {
            'name': self.env._("Product Feeds"),
            'type': 'ir.actions.act_window',
            'res_model': 'product.feed',
            'views': [(False, 'list')],
            'target': 'new',
            'context': {
                'default_website_id': self.website_id.id,
                'hide_website_column': True,
            },
            'domain': [('website_id', '=', self.website_id.id)],
        }
