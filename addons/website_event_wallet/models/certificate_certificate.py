# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class CertificateCertificate(models.Model):
    _inherit = 'certificate.certificate'

    scope = fields.Selection(
        selection_add=[('event', 'Event Pass')],
        ondelete={'event': 'set null'},
    )

    wallet_type = fields.Selection(
        selection=[
            ('apple', 'Apple Wallet'),
            ('samsung', 'Samsung Wallet'),
            ('google', 'Google Wallet'),
        ],
        string='Wallet Type',
        help='Wallet that uses this event pass certificate.',
    )

    @api.constrains('scope', 'wallet_type')
    def _check_event_pass_wallet_type(self):
        for certificate in self:
            if certificate.scope == 'event' and not certificate.wallet_type:
                raise ValidationError(self.env._('Select a wallet type for the event pass certificate.'))

    @api.model
    def _get_wallet_provider_scopes(self, **kwargs):
        """Return implemented provider codes mapped to certificate scopes.

        Integrations extend the dictionary returned by super to register their
        provider. Certificate lookup and company availability use this mapping.
        """
        return {}

    @api.model
    def _get_wallet_certificate(self, company, provider_code, **kwargs):
        """Select a usable certificate for this exact company and provider.

        Additional options are forwarded to the provider's readiness checks.
        """
        company.ensure_one()
        scope = self._get_wallet_provider_scopes(**kwargs).get(provider_code)
        if not scope:
            return self.browse()
        now = fields.Datetime.now()
        certificates = self.search([
            ('company_id', '=', company.id),
            ('scope', '=', scope),
            ('wallet_type', '=', provider_code),
            ('private_key_id', '!=', False),
            ('date_start', '<=', now),
            ('date_end', '>', now),
        ], order='date_end DESC, id DESC')
        return certificates.filtered(
            lambda certificate: certificate._is_wallet_provider_certificate_ready(provider_code, **kwargs)
        )[:1]

    def _is_wallet_certificate_ready(self, scope, **kwargs):
        """Check common certificate and private key requirements for ``scope``.

        Issuer and other provider-specific requirements belong in the provider
        readiness methods. Integrations may extend these checks using super.
        """
        self.ensure_one()
        return bool(
            scope
            and self.active
            and self.scope == scope
            and self.is_valid
            and self.private_key_id.active
            and not self.private_key_id.public
            and not self.private_key_id.loading_error
        )

    def _is_wallet_provider_certificate_ready(self, provider_code, **kwargs):
        """Apply readiness rules for a provider; extend for additional requirements."""
        self.ensure_one()
        if self.wallet_type != provider_code:
            return False
        scope = self._get_wallet_provider_scopes(**kwargs).get(provider_code)
        return self._is_wallet_certificate_ready(scope, **kwargs)

    def _generate_wallet_event_pass(self, event_data, provider_code, code_type='qr', lang=None, **kwargs):
        """Generate a downloadable pass as a JSON-serializable dictionary.

        The caller must authorize access to the ticket before calling.
        Integrations override this method for their provider codes and delegate
        unhandled codes to super. The parent does not implement a provider.

        :param dict event_data: Ticket details for the selected provider.
        :param str provider_code: Explicit code of the selected wallet provider.
        :param str code_type: Barcode format accepted by the selected provider.
        :param str lang: Optional Odoo language code for translated labels.
        :param kwargs: Additional options forwarded to the provider implementation.
        :return: A dictionary containing ``content`` (base64-encoded file bytes
            as an ASCII string), ``mimetype`` (the file's MIME type), and
            ``extension`` (the filename extension without a leading dot).
            Provider implementations may add JSON-serializable keys.
        :rtype: dict
        """
        self.ensure_one()
        certificate = self.with_context(lang=lang) if lang else self
        raise UserError(certificate.env._('Unsupported wallet provider: %s', provider_code))
