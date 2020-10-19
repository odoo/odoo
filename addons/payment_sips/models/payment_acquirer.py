# coding: utf-8

# Copyright 2015 Eezee-It

from hashlib import sha256

from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.addons.payment.models.payment_acquirer import ValidationError

from .const import SIPS_SUPPORTED_CURRENCIES

class AcquirerSips(models.Model):
    _inherit = "payment.acquirer"

    provider = fields.Selection(selection_add=[("sips", "Sips")],
        ondelete={"sips": "set default"})
    sips_merchant_id = fields.Char("Merchant ID", required_if_provider="sips",
        groups="base.group_user")
    sips_secret = fields.Char("Secret Key", size=64, required_if_provider="sips",
        groups="base.group_user")
    sips_test_url = fields.Char("Test url", required_if_provider="sips",
        default="https://payment-webinit.simu.sips-atos.com/paymentInit")
    sips_prod_url = fields.Char("Production url", required_if_provider="sips",
        default="https://payment-webinit.sips-atos.com/paymentInit")
    sips_version = fields.Char("Interface Version", required_if_provider="sips",
        default="HP_2.31")
    sips_key_version = fields.Integer("Secret Key Version", required_if_provider="sips",
        default=2)

    def _sips_generate_shasign(self, values):
        """ Generate the shasign for incoming or outgoing communications.
        :param dict values: transaction values
        :return string: shasign
        """
        self.ensure_one()
        if self.provider != "sips":
            raise ValidationError(_("Incorrect payment acquirer provider"))
        data = values["Data"]
        key = self.sips_secret

        shasign = sha256((data + key).encode("utf-8"))
        return shasign.hexdigest()

    @api.model
    def _sips_supported_currencies(self):
        sips_currencies = list(SIPS_SUPPORTED_CURRENCIES.keys())
        return self.env['res.currency'].search([('name', 'in', sips_currencies)])

    @api.model
    def _get_compatible_acquirers(self, company_id, partner_id, currency_id=None, allow_tokenization=False, preferred_acquirer_id=None, **kwargs):
        acquirers = super()._get_compatible_acquirers(company_id, partner_id, currency_id, allow_tokenization, preferred_acquirer_id, **kwargs)

        sips_currencies = self._sips_supported_currencies().ids
        if currency_id not in sips_currencies:
            sips = self.search([('provider', '=', 'sips')])
            acquirers = acquirers - sips

        return acquirers
