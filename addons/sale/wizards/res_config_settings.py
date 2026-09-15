from odoo import _, api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    default_invoice_policy = fields.Selection(
        selection=[
            ("ordered", "Invoice what is ordered"),
            ("transferred", "Invoice what is delivered"),
        ],
        string="Invoicing Policy",
        default="ordered",
        default_model="product.template",
    )

    lock_confirmed_so = fields.Boolean(
        string="Lock Confirmed Sales Orders",
        default=lambda self: self.env.company.order_lock_so == "lock",
    )
    order_lock_so = fields.Selection(
        related="company_id.order_lock_so",
        string="Sale Order Modification *",
        readonly=False,
    )

    group_auto_done_setting = fields.Boolean(
        string="Lock Confirmed Sales",
        implied_group="sale.group_auto_done_setting",
    )
    group_discount_per_so_line = fields.Boolean(
        string="Discounts",
        implied_group="sale.group_discount_per_so_line",
    )
    group_proforma_sales = fields.Boolean(
        string="Pro-Forma Invoice",
        implied_group="sale.group_proforma_sales",
        help="Allows you to send pro-forma invoice.",
    )
    group_warning_sale = fields.Boolean(
        string="Sale Order Warnings",
        implied_group="sale.group_warning_sale",
    )
    group_sale_order_template = fields.Boolean(
        string="Quotation Templates",
        implied_group="sale.group_sale_order_template",
    )
    group_sale_app_menu = fields.Boolean(
        string="Sales App",
        implied_group="sale.group_sale_app_menu",
    )
    company_so_template_id = fields.Many2one(
        related="company_id.sale_order_template_id",
        string="Default Template",
        readonly=False,
        domain="[('company_id', 'in', [False, company_id])]",
    )

    automatic_invoice = fields.Boolean(
        config_parameter="sale.automatic_invoice",
        help="The invoice is generated automatically and available in the customer portal when the "
        "transaction is confirmed by the payment provider.\nThe invoice is marked as paid and "
        "the payment is registered in the payment journal defined in the configuration of the "
        "payment provider.\nThis mode is advised if you issue the final invoice at the order "
        "and not after the delivery.",
    )

    invoice_mail_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Email Template",
        config_parameter="sale.default_invoice_email_template",
        domain=[("model", "=", "account.move")],
        help="Email sent to the customer once the invoice is available.",
    )
    quotation_validity_days = fields.Integer(
        related="company_id.quotation_validity_days",
        readonly=False,
    )
    portal_confirmation_sign = fields.Boolean(
        related="company_id.portal_confirmation_sign",
        readonly=False,
    )
    portal_confirmation_pay = fields.Boolean(
        related="company_id.portal_confirmation_pay",
        readonly=False,
    )
    prepayment_percent = fields.Float(
        related="company_id.prepayment_percent",
        readonly=False,
    )
    downpayment_account_id = fields.Many2one(
        related="company_id.downpayment_account_id",
        readonly=False,
    )

    module_delivery = fields.Boolean(string="Delivery Methods")
    module_delivery_bpost = fields.Boolean(string="bpost Connector")
    module_delivery_dhl = fields.Boolean(string="DHL Express Connector")
    module_delivery_easypost = fields.Boolean(string="Easypost Connector")
    module_delivery_envia = fields.Boolean(string="Envia.com Connector")
    module_delivery_fedex_rest = fields.Boolean(string="FedEx Connector")
    module_delivery_sendcloud = fields.Boolean(string="Sendcloud Connector")
    module_delivery_shiprocket = fields.Boolean(string="Shiprocket Connector")
    module_delivery_starshipit = fields.Boolean(string="Starshipit Connector")
    module_delivery_ups_rest = fields.Boolean(string="UPS Connector")
    module_delivery_usps_rest = fields.Boolean(string="USPS Connector")

    module_product_email_template = fields.Boolean(string="Specific Email")
    module_sale_amazon = fields.Boolean(string="Amazon Sync")
    module_sale_commission = fields.Boolean(string="Commissions")
    module_sale_gelato = fields.Boolean(string="Gelato")
    module_sale_loyalty = fields.Boolean(string="Coupons & Loyalty")
    module_sale_margin = fields.Boolean(string="Margins")
    module_sale_pdf_quote_builder = fields.Boolean(string="PDF Quote builder")
    module_sale_product_matrix = fields.Boolean(string="Sales Grid Entry")
    module_sale_shopee = fields.Boolean(string="Shopee Sync")

    @api.onchange("group_discount_per_so_line")
    def _onchange_group_discount_per_so_line(self):
        if self.group_discount_per_so_line:
            self.group_product_pricelist = True

    @api.onchange("group_product_variant")
    def _onchange_group_product_variant(self):
        if self.module_sale_product_matrix and not self.group_product_variant:
            self.module_sale_product_matrix = False
            _debug.logic(
                "module_disabled", module="sale_product_matrix", by="no_product_variant"
            )

    @api.onchange("portal_confirmation_pay")
    def _onchange_portal_confirmation_pay(self):
        self.prepayment_percent = self.prepayment_percent or 1.0

    @api.onchange("prepayment_percent")
    def _onchange_prepayment_percent(self):
        if not self.prepayment_percent:
            self.portal_confirmation_pay = False

    @api.onchange("quotation_validity_days")
    def _onchange_quotation_validity_days(self):
        return self._clamp_validity_days(
            "quotation_validity_days",
            _("Quotation Validity"),
        )

    def set_values(self):
        if not self.group_sale_order_template:
            if self.company_so_template_id:
                self.company_so_template_id = False
            companies = (
                self.env["res.company"]
                .sudo()
                .search([("sale_order_template_id", "!=", False)])
            )
            if companies:
                _debug.lifecycle(
                    "company_templates_cleared",
                    companies=companies,
                    reason="templates_feature_off",
                )
                companies.sale_order_template_id = False
        super().set_values()
        _debug.lifecycle(
            "sale_settings_saved",
            invoice_policy=self.default_invoice_policy,
            lock_confirmed=self.lock_confirmed_so,
            automatic_invoice=self.automatic_invoice,
        )
        if self.default_invoice_policy != "ordered":
            _debug.logic(
                "automatic_invoice_forced_off", reason="invoice_policy_not_ordered"
            )
            self.env["ir.config_parameter"].set_param(
                key="sale.automatic_invoice", value=False
            )
        self._sync_order_lock("lock_confirmed_so", "order_lock_so")

    def action_sale_start_payment_onboarding(self):
        menu = self.env.ref("sale.menu_sale_general_settings", raise_if_not_found=False)
        return self._start_payment_onboarding(menu and menu.id)
