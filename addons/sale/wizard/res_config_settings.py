# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Groups
    group_auto_done_setting = fields.Boolean(
        string="Lock Confirmed Sales", implied_group="sale.group_auto_done_setting"
    )
    group_discount_per_so_line = fields.Boolean(
        string="Discounts", implied_group="sale.group_discount_per_so_line"
    )
    group_proforma_sales = fields.Boolean(
        string="Pro Forma Invoice",
        implied_group="sale.group_proforma_sales",
        help="Allows you to send pro forma invoice.",
    )
    group_warning_sale = fields.Boolean(
        string="Sale Order Warnings", implied_group="sale.group_warning_sale"
    )
    group_services_and_material = fields.Boolean(
        string="Services & Materials", implied_group="sale.group_services_and_material"
    )

    # Config params
    invoice_mail_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Email Template",
        domain=[("model", "=", "account.move")],
        config_parameter="sale.default_invoice_email_template",
        help="Email sent to the customer once the invoice is available.",
    )

    sale_order_mandatory_product = fields.Boolean(
        string="Mandatory Product", config_parameter="sale.mandatory_product"
    )

    # Company dependent
    quotation_validity_days = fields.Integer(
        related="company_id.quotation_validity_days", readonly=False
    )
    portal_confirmation_sign = fields.Boolean(
        related="company_id.portal_confirmation_sign", readonly=False
    )
    portal_confirmation_pay = fields.Boolean(
        related="company_id.portal_confirmation_pay", readonly=False
    )
    prepayment_percent = fields.Float(related="company_id.prepayment_percent", readonly=False)
    display_product_images_on_so = fields.Boolean(
        related="company_id.display_product_images_on_so", readonly=False
    )
    downpayment_account_id = fields.Many2one(
        related="company_id.downpayment_account_id", readonly=False
    )
    downpayment_account_active = fields.Boolean(
        related="downpayment_account_id.active", string="Down payment Account Active"
    )
    sale_invoice_policy = fields.Selection(related="company_id.sale_invoice_policy", readonly=False)
    sale_automatic_invoice = fields.Boolean(
        related="company_id.sale_automatic_invoice", readonly=False
    )

    # Modules
    module_delivery = fields.Boolean("Delivery Methods")

    module_product_email_template = fields.Boolean("Specific Email")
    module_sale_amazon = fields.Boolean("Amazon Sync")
    module_sale_commission = fields.Boolean("Commissions")
    module_sale_gelato = fields.Boolean("Gelato")
    module_sale_loyalty = fields.Boolean("Coupons & Loyalty")
    module_sale_margin = fields.Boolean("Margins")
    module_sale_pdf_quote_builder = fields.Boolean("PDF Quote builder")
    module_sale_product_matrix = fields.Boolean("Sales Grid Entry")
    module_sale_shopee = fields.Boolean("Shopee Sync")
    module_sale_lazada = fields.Boolean("Lazada Sync")

    # === ONCHANGE METHODS ===#

    @api.depends("group_discount_per_so_line")
    def _onchange_group_discount_per_so_line(self):
        if self.group_discount_per_so_line:
            self.group_product_pricelist = True

    @api.onchange("group_product_variant")
    def _onchange_group_product_variant(self):
        """Disable the Product Grid module if variants are disabled."""
        if self.module_sale_product_matrix and not self.group_product_variant:
            self.module_sale_product_matrix = False

    @api.onchange("portal_confirmation_pay")
    def _onchange_portal_confirmation_pay(self):
        self.prepayment_percent = self.prepayment_percent or 1.0

    @api.onchange("prepayment_percent")
    def _onchange_prepayment_percent(self):
        if not self.prepayment_percent:
            self.portal_confirmation_pay = False

    @api.onchange("quotation_validity_days")
    def _onchange_quotation_validity_days(self):
        if self.quotation_validity_days < 0:
            self.quotation_validity_days = self.env["res.company"].default_get([
                "quotation_validity_days"
            ])["quotation_validity_days"]
            return {
                "warning": {
                    "title": self.env._("Warning"),
                    "message": self.env._(
                        "Quotation Validity is required and must be greater or equal to 0."
                    ),
                }
            }

    @api.onchange("sale_invoice_policy")
    def _onchange_sale_invoice_policy(self):
        if self.sale_invoice_policy != "order":
            self.sale_automatic_invoice = False

    def set_values(self):
        super().set_values()
        if mandatory_product_view := self.env.ref(
            "sale.view_order_form_mandatory_product", raise_if_not_found=False
        ):
            mandatory_product_view.active = self.sale_order_mandatory_product

    # === ACTION METHODS === #

    # Unique name to avoid colliding with `website_payment`.
    def action_sale_start_payment_onboarding(self):
        menu = self.env.ref("sale.menu_sale_general_settings", raise_if_not_found=False)
        return self.company_id._start_payment_onboarding(menu and menu.id)
