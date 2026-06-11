# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError

SALE_INVOICE_POLICY = [("order", "Ordered quantities"), ("delivery", "Delivered quantities")]


class ResCompany(models.Model):
    _inherit = "res.company"
    _check_company_auto = True

    _check_quotation_validity_days = models.Constraint(
        "CHECK(quotation_validity_days >= 0)",
        "You cannot set a negative number for the default quotation validity. Leave empty (or 0) to"
        " disable the automatic expiration of quotations.",
    )

    portal_confirmation_sign = fields.Boolean(string="Online Signature", default=True)
    portal_confirmation_pay = fields.Boolean(string="Online Payment")
    prepayment_percent = fields.Float(
        string="Prepayment percentage",
        default=1.0,
        help="The percentage of the amount needed to be paid to confirm quotations.",
    )
    display_product_images_on_so = fields.Boolean(string="Display Product Images")
    quotation_validity_days = fields.Integer(
        string="Default Quotation Validity",
        default=30,
        help="Days between quotation proposal and expiration."
        " 0 days means automatic expiration is disabled",
    )
    sale_discount_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Discount Product",
        domain=[("type", "=", "service"), ("invoice_policy", "=", "order")],
        help="Default product used for discounts",
        check_company=True,
    )

    # sale onboarding
    sale_onboarding_payment_method = fields.Selection(
        selection=[
            ("digital_signature", "Sign online"),
            ("paypal", "PayPal"),
            ("stripe", "Stripe"),
            ("other", "Pay with another payment provider"),
            ("manual", "Manual Payment"),
        ],
        string="Sale onboarding selected payment method",
    )

    downpayment_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Downpayment Account",
        domain=[("account_type", "in", ("income", "income_other", "liability_current"))],
        help="This account will be used on Downpayment invoices.",
        tracking=True,
    )
    show_sol_numbers = fields.Boolean(
        string="Line Numbers", help="Display line numbers on Sales Orders."
    )

    sale_invoice_policy = fields.Selection(
        selection=SALE_INVOICE_POLICY, string="Invoicing Policy", default="order", required=True
    )

    sale_automatic_invoice = fields.Boolean(
        string="Automatic Invoicing",
        help="The invoice is generated automatically and available in the customer portal when the "
        "transaction is confirmed by the payment provider.\nThe invoice is marked as paid and "
        "the payment is registered in the payment journal defined in the configuration of the "
        "payment provider.\nThis mode is advised if you issue the final invoice at the order "
        "and not after the delivery.",
    )

    # === CONSTRAINT METHODS === #

    @api.constrains("prepayment_percent")
    def _check_prepayment_percent(self):
        for company in self:
            if company.portal_confirmation_pay and not (0 < company.prepayment_percent <= 1.0):
                raise ValidationError(
                    company.env._("Prepayment percentage must be a valid percentage.")
                )

    # === CRUD METHODS ===#

    @api.model_create_multi
    def create(self, vals_list):
        result = super().create(vals_list)
        self._sync_automatic_invoice_cron()
        return result

    def write(self, vals):
        result = super().write(vals)
        if "sale_automatic_invoice" in vals:
            self._sync_automatic_invoice_cron()
        return result

    def _sync_automatic_invoice_cron(self):
        automatic_invoice_cron = self.env.ref("sale.send_invoice_cron", raise_if_not_found=False)
        if not automatic_invoice_cron:
            return
        active_companies = self.search_count([("sale_automatic_invoice", "=", True)], limit=1)
        automatic_invoice_cron.sudo().active = bool(active_companies)
