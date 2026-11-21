# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import hashlib
from datetime import datetime, timezone

from asn1crypto import cms, x509 as asn1_x509
from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.x509 import load_der_x509_certificate

from odoo import api, models
from odoo.exceptions import UserError

from odoo.tools.pdf.signature import build_cms_signature, build_signed_attributes

from ..tools.apple_wallet import generate_event_pass


class CertificateCertificateApple(models.Model):
    _inherit = 'certificate.certificate'

    @api.model
    def _get_wallet_provider_scopes(self, **kwargs):
        return {**super()._get_wallet_provider_scopes(**kwargs), 'apple': 'event'}

    def _is_wallet_provider_certificate_ready(self, provider_code, **kwargs):
        is_ready = super()._is_wallet_provider_certificate_ready(provider_code, **kwargs)
        if provider_code == 'apple':
            return bool(is_ready and self.issuer_cert_id.is_valid)
        return is_ready

    def _generate_wallet_event_pass(self, event_data, provider_code, code_type='qr', lang=None, **kwargs):
        """Return the parent's documented JSON dictionary for Apple passes.

        Other provider codes are delegated to super. Additional keyword options
        are forwarded to the Apple implementation for inherited customizations.
        """
        if provider_code != 'apple':
            return super()._generate_wallet_event_pass(
                event_data, provider_code=provider_code, code_type=code_type, lang=lang, **kwargs,
            )
        self.ensure_one()
        certificate = self.with_context(lang=lang) if lang else self
        return certificate._generate_apple_wallet_event_pass(event_data, code_type=code_type, **kwargs)

    def _generate_apple_wallet_event_pass(self, event_data, code_type='qr', **kwargs):
        """Return the dictionary documented by ``_generate_wallet_event_pass``.

        Additional keyword options are accepted for inherited implementations.
        """
        self.ensure_one()
        certificate = self
        if not certificate._is_wallet_provider_certificate_ready('apple', **kwargs):
            raise UserError(certificate.env._('Configure a valid Apple Wallet certificate, its private key and its WWDR issuer.'))
        try:
            identifiers = certificate._get_apple_wallet_identifiers(**kwargs)
            payload = generate_event_pass(
                event_data,
                **identifiers,
                sign_manifest=lambda manifest: certificate._sign_apple_wallet_manifest(manifest, **kwargs),
                organization_name=certificate.company_id.name,
                code_type=code_type,
                translate=certificate.env._,
            )
        except (ValueError, TypeError, InvalidSignature, UnsupportedAlgorithm) as error:
            raise UserError(self.env._('Unable to generate the Apple Wallet pass: %s', str(error))) from error
        return {
            'content': base64.b64encode(payload).decode('ascii'),
            'mimetype': 'application/vnd.apple.pkpass',
            'extension': 'pkpass',
        }

    def _get_apple_wallet_identifiers(self, **kwargs):
        """Read Apple's UID and OU from the DER certificate exported by Odoo."""
        self.ensure_one()
        certificate = asn1_x509.Certificate.load(self._get_der_certificate_bytes(formatting=''))
        identifiers = {}
        for name, oid in (
            ('pass_type_identifier', '0.9.2342.19200300.100.1.1'),
            ('team_identifier', '2.5.4.11'),
        ):
            values = [
                attribute['value'].native
                for rdn in certificate.subject.chosen
                for attribute in rdn
                if attribute['type'].dotted == oid
            ]
            if len(values) != 1 or not isinstance(values[0], str) or not values[0].strip():
                raise ValueError('The signing certificate must contain a Pass Type ID and a Team ID.')
            identifiers[name] = values[0]
        return identifiers

    def _sign_apple_wallet_manifest(self, manifest, **kwargs):
        """Return a detached DER CMS signature using Odoo's certificate signer.

        Certificate validity, key loading and signing are delegated to
        certificate.certificate. Odoo's CMS helpers assemble the envelope.
        The caller must authorize access to the registration before signing.
        """
        self.ensure_one()
        if not self._is_wallet_provider_certificate_ready('apple', **kwargs):
            raise UserError(self.env._('Configure a valid Apple Wallet certificate, its private key and its WWDR issuer.'))
        der = self._get_der_certificate_bytes(formatting='')
        issuer_der = self.issuer_cert_id._get_der_certificate_bytes(formatting='')
        # Odoo may resolve an issuer through its AKI fallback. Preserve strict
        # issuer-signature verification before including that certificate.
        load_der_x509_certificate(der).verify_directly_issued_by(load_der_x509_certificate(issuer_der))
        signer = asn1_x509.Certificate.load(der)
        intermediate = asn1_x509.Certificate.load(issuer_der)
        signed_attrs = build_signed_attributes(hashlib.sha256(manifest).digest(), signer)
        # Apple requires the S/MIME signing-time attribute in its CMS signature.
        signed_attrs.append(cms.CMSAttribute({
            'type': 'signing_time',
            'values': [cms.Time({'utc_time': datetime.now(timezone.utc)})],
        }))
        signature = self._sign(signed_attrs.dump(), hashing_algorithm='sha256', formatting='')
        return build_cms_signature(signed_attrs, signature, signer, [intermediate]).dump()
