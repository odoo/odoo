from odoo import fields, models

from .const import CURRENCY_MAPPING


class PaymentAcquirer(models.Model):
    _inherit = "payment.acquirer"

    def _domain_asiapay_currency_id(self):
        xmlids = ["base.{}".format(key) for key in CURRENCY_MAPPING]
        return [('id', 'in', [self.env.ref(xmlid).id for xmlid in xmlids])]

    provider = fields.Selection(selection_add=[("asiapay", "Asiapay")], ondelete={"asiapay": "set default"})
    asiapay_merchant_id = fields.Char(
        string="AsiaPay Merchant Partner ID",
        required_if_provider="asiapay",
        help="The Merchant Partner ID is used to connect to Asiapay merchant account.",
    )
    asiapay_currency_id = fields.Many2one(
        "res.currency",
        required_if_provider="asiapay",
        string="AsiaPay Currency Code",
        domain=_domain_asiapay_currency_id,
    )
    asiapay_secure_hash = fields.Char(
        string="AsiaPay Secure Hash",
        help="The Secure Hash is used to ensure communications coming from Asiapay are valid and secured.",
    )
    asiapay_secure_hash_function = fields.Selection(
        [('sha1', 'Sha1'), ('sha256', 'Sha256')],
        required=True,
        default='sha1',
        string="AsiaPay Secure Hash Function",
        help="The Secure Hash Function to create the hash.",
    )

    def _asiapay_get_api_url(self):
        self.ensure_one()
        if self.state == "enabled":
            return "https://www.paydollar.com/b2c2/eng/payment/payForm.jsp"
        return "https://test.paydollar.com/b2cDemo/eng/payment/payForm.jsp"

    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.provider != "asiapay":
            return super()._get_default_payment_method_id()
        return self.env.ref("payment_asiapay.payment_method_asiapay").id
