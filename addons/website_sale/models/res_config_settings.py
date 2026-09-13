from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    group_show_uom_price = fields.Boolean(
        string="Base Unit Price",
        default=False,
        implied_group="website_sale.group_show_uom_price",
        group="base.group_user",
    )
    group_product_price_comparison = fields.Boolean(
        string="Comparison Price",
        implied_group="website_sale.group_product_price_comparison",
        group="base.group_user",
        help="Add a strikethrough price to your /shop and product pages for comparison purposes."
        "It will not be displayed if pricelists apply.",
    )
    group_gmc_feed = fields.Boolean(
        related="website_id.enabled_gmc_src",
        string="Google Merchant Center",
        readonly=False,
        implied_group="website_sale.group_product_feed",
        group="base.group_user",
    )

    module_website_sale_autocomplete = fields.Boolean(string="Address Autocomplete")
    module_website_sale_collect = fields.Boolean(string="Click & Collect")

    add_to_cart_action = fields.Selection(
        related="website_id.add_to_cart_action",
        readonly=False,
    )
    cart_recovery_mail_template = fields.Many2one(
        related="website_id.cart_recovery_mail_template_id",
        readonly=False,
    )
    cart_abandoned_delay = fields.Float(
        related="website_id.cart_abandoned_delay",
        readonly=False,
    )
    send_abandoned_cart_email = fields.Boolean(
        related="website_id.send_abandoned_cart_email",
        string="Abandoned Email",
        readonly=False,
    )
    salesperson_id = fields.Many2one(
        related="website_id.salesperson_id",
        readonly=False,
    )
    salesteam_id = fields.Many2one(
        related="website_id.salesteam_id",
        readonly=False,
    )
    website_sale_prevent_zero_price_sale = fields.Boolean(
        related="website_id.prevent_zero_price_sale",
        string="Prevent Sale of Zero Priced Product",
        readonly=False,
    )
    website_sale_contact_us_button_url = fields.Char(
        related="website_id.contact_us_button_url",
        string="Button Url",
        readonly=False,
    )
    show_line_subtotals_tax_selection = fields.Selection(
        related="website_id.show_line_subtotals_tax_selection",
        readonly=False,
    )
    confirmation_email_template_id = fields.Many2one(
        related="website_id.confirmation_email_template_id",
        readonly=False,
    )

    account_on_checkout = fields.Selection(
        selection=[
            ("optional", "Optional"),
            ("disabled", "Disabled"),
            ("mandatory", "Mandatory"),
        ],
        string="Customer Accounts",
        compute="_compute_account_on_checkout",
        inverse="_inverse_account_on_checkout",
        readonly=False,
        required=True,
    )
    ecommerce_access = fields.Selection(
        related="website_id.ecommerce_access",
        readonly=False,
    )

    @api.depends("website_id.account_on_checkout")
    def _compute_account_on_checkout(self):
        for record in self:
            record.account_on_checkout = (
                record.website_id.account_on_checkout or "disabled"
            )

    def _inverse_account_on_checkout(self):
        for record in self:
            if not record.website_id:
                continue
            if record.website_id.account_on_checkout != record.account_on_checkout:
                if self.account_on_checkout in ["optional", "mandatory"]:
                    record.website_id.auth_signup_uninvited = "b2c"
                else:
                    record.website_id.auth_signup_uninvited = "b2b"
            record.website_id.account_on_checkout = record.account_on_checkout

    def set_values(self):
        super().set_values()
        if self.website_id:
            website = self.with_context(website_id=self.website_id.id).website_id

            if self.group_gmc_feed and not self.env["product.feed"].search_count(
                [("website_id", "=", website.id)], limit=1
            ):
                website._create_product_feeds()

            self.env["website"].sudo().search_fetch(
                [], []
            ).enabled_gmc_src = self.group_gmc_feed

    def action_view_delivery_provider_modules(self):
        return self.env["delivery.carrier"].install_more_provider()

    @api.readonly
    def action_view_abandoned_cart_mail_template(self):
        return {
            "name": self.env._("Customize Email Templates"),
            "type": "ir.actions.act_window",
            "res_model": "mail.template",
            "view_id": False,
            "view_mode": "form",
            "res_id": self.env["ir.model.data"]._xmlid_to_res_id(
                "website_sale.mail_template_sale_cart_recovery"
            ),
        }

    def action_view_extra_info(self):
        self.check_singleton()
        return self.env["website"].get_client_action(
            "/shop/extra_info?open_editor=true",
            mode_edit=True,
            website_id=self.website_id.id,
        )

    @api.readonly
    def action_view_sale_mail_templates(self):
        return {
            "name": self.env._("Customize Email Templates"),
            "type": "ir.actions.act_window",
            "domain": [("model", "=", "sale.order")],
            "res_model": "mail.template",
            "view_id": False,
            "view_mode": "list,form",
        }

    @api.readonly
    def action_view_product_feeds(self):
        self.check_singleton()
        return {
            "name": self.env._("Product Feeds"),
            "type": "ir.actions.act_window",
            "res_model": "product.feed",
            "views": [(False, "list")],
            "target": "new",
            "context": {
                "default_website_id": self.website_id.id,
                "hide_website_column": True,
            },
            "domain": [("website_id", "=", self.website_id.id)],
        }
