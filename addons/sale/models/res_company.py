from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class ResCompany(models.Model):
    _inherit = "res.company"
    _check_company_auto = True

    order_lock_so = fields.Selection(
        selection=[
            ("edit", "Allow to edit sale orders"),
            ("lock", "Confirmed sale orders are not editable"),
        ],
        string="Sale Order Modification",
        help="Sale Order Modification used when you want to keep sale orders editable after confirmation",
        default="edit",
    )
    portal_confirmation_sign = fields.Boolean(
        string="Online Signature",
        default=True,
    )
    portal_confirmation_pay = fields.Boolean(string="Online Payment")
    prepayment_percent = fields.Float(
        string="Prepayment percentage",
        help="The percentage of the amount needed to be paid to confirm quotations.",
        default=1.0,
    )
    quotation_validity_days = fields.Integer(
        string="Default Quotation Validity",
        help="Days between quotation proposal and expiration."
        " 0 days means automatic expiration is disabled",
        default=30,
    )
    sale_discount_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Discount Product",
        help="Default product used for discounts",
        domain=[
            ("type", "=", "service"),
            ("invoice_policy", "=", "ordered"),
        ],
        check_company=True,
    )
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
        help="This account will be used on Downpayment invoices.",
        domain=[
            ("account_type", "in", ("income", "income_other", "liability_current")),
        ],
        tracking=True,
    )

    _check_quotation_validity_days = models.Constraint(
        "CHECK(quotation_validity_days >= 0)",
        "You cannot set a negative number for the default quotation validity. Leave empty (or 0) to disable the automatic expiration of quotations.",
    )

    @api.constrains("prepayment_percent", "portal_confirmation_pay")
    def _check_prepayment_percent(self):
        for company in self:
            if company.portal_confirmation_pay and not (
                0 < company.prepayment_percent <= 1.0
            ):
                raise ValidationError(
                    _("Prepayment percentage must be a valid percentage."),
                )
