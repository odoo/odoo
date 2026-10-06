import base64
import uuid

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.pos_bancontact_pay import const


class ResCompany(models.Model):
    _inherit = 'res.company'

    bancontact_merchant_id = fields.Char("Bancontact Merchant ID", copy=False)
    bancontact_signing_key = fields.Char("Bancontact Signing Key", groups="base.group_system", copy=False)
    bancontact_signing_kid = fields.Char("Bancontact Signing Key ID", copy=False)

    def write(self, vals):
        res = super().write(vals)
        if vals.get('bancontact_merchant_id'):
            self.filtered(lambda company: not company.sudo().bancontact_signing_key)._bancontact_generate_signing_key()
        return res

    def _bancontact_generate_signing_key(self):
        """Generate a new ES256 key pair used to sign the requests sent to Bancontact."""
        for company in self:
            private_key = ec.generate_private_key(ec.SECP256R1())
            company.sudo().write({
                'bancontact_signing_key': private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                ).decode(),
                'bancontact_signing_kid': uuid.uuid4().hex,
            })

    def _bancontact_can_sign(self):
        """Return whether the company can sign the requests sent to Bancontact."""
        self.ensure_one()
        return bool(self.bancontact_merchant_id and self.sudo().bancontact_signing_key)

    def _bancontact_get_signing_key(self):
        """Return the private key used to sign the requests sent to Bancontact."""
        self.ensure_one()
        return serialization.load_pem_private_key(self.sudo().bancontact_signing_key.encode(), password=None)

    def _bancontact_get_public_jwk(self):
        """Return the public key of the company as a JWK, as published on the JWKS URL."""
        self.ensure_one()
        public_numbers = self._bancontact_get_signing_key().public_key().public_numbers()
        return {
            'kty': 'EC',
            'crv': 'P-256',
            'x': base64.urlsafe_b64encode(public_numbers.x.to_bytes(32, 'big')).decode().rstrip('='),
            'y': base64.urlsafe_b64encode(public_numbers.y.to_bytes(32, 'big')).decode().rstrip('='),
            'use': 'sig',
            'alg': 'ES256',
            'kid': self.bancontact_signing_kid,
        }

    @api.constrains('currency_id')
    def _check_currency(self):
        """Prevent setting an unsupported company currency when Bancontact Pay relies on it."""
        for record in self:
            # Currency already supported by Bancontact Pay
            if record.currency_id.name in const.SUPPORTED_CURRENCIES:
                return

            # If unsupported, check if any Bancontact Pay payment methods are using a journal with no currency set
            payment_method_ids = self.env['pos.payment.method'].search_count(
                [
                    ('company_id', '=', record.id),
                    ('journal_id.currency_id', '=', False),
                    ('payment_provider', '=', 'bancontact_pay'),
                ], limit=1,
            )
            if payment_method_ids:
                raise ValidationError(
                    _(
                        "A Bancontact Pay payment method is linked to a journal that uses the company's default currency.\n"
                        "This currency is not supported.\n"
                        "Supported currencies: %(currencies)s.",
                        currencies=", ".join(const.SUPPORTED_CURRENCIES),
                    ),
                )
