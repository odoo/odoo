# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64decode
from pytz import timezone
from datetime import datetime
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat


from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError
from odoo.addons.account.tools.certificate import load_key_and_certificates


class Certificate(models.Model):
    _name = 'l10n_es_edi.certificate'
    _description = 'Personal Digital Certificate'
    _order = 'date_start desc, id desc'
    _rec_name = 'date_start'

    content = fields.Binary(string="File", required=True, help="PFX Certificate")
    password = fields.Char(help="Passphrase for the PFX certificate", groups="base.group_system")
    date_start = fields.Datetime(readonly=True, help="The date on which the certificate starts to be valid")
    date_end = fields.Datetime(readonly=True, help="The date on which the certificate expires")
    company_id = fields.Many2one(comodel_name='res.company', required=True, default=lambda self: self.env.company)

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    @api.model
    def _get_es_current_datetime(self):
        """Get the current datetime with the Peruvian timezone. """
        return datetime.now(timezone('Europe/Madrid'))

    @tools.ormcache('self.content', 'self.password')
    def _decode_certificate(self):
        """Return the content (DER encoded) and the certificate decrypted based in the point 3.1 from the RS 097-2012
        http://www.vauxoo.com/r/manualdeautorizacion#page=21
        """
        self.ensure_one()

        if not self.password:
            return None, None, None

        private_key, certificate = load_key_and_certificates(
            b64decode(self.content),
            self.password.encode(),
        )

        pem_certificate = certificate.public_bytes(Encoding.PEM)
        pem_private_key = private_key.private_bytes(
            Encoding.PEM,
            format=PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=NoEncryption(),
        )
        return pem_certificate, pem_private_key, certificate

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        certificates = super().create(vals_list)

        spain_tz = timezone('Europe/Madrid')
        spain_dt = self._get_es_current_datetime()
        for certificate in certificates:
            try:
                _pem_certificate, _pem_private_key, certif = certificate._decode_certificate()
                cert_date_start = spain_tz.localize(certif.not_valid_before)
                cert_date_end = spain_tz.localize(certif.not_valid_after)
            except Exception:
                raise ValidationError(_(
                    "There has been a problem with the certificate, some usual problems can be:\n"
                    "- The password given or the certificate are not valid.\n"
                    "- The certificate content is invalid."
                ))
            # Assign extracted values from the certificate
            certificate.write({
                'date_start': fields.Datetime.to_string(cert_date_start),
                'date_end': fields.Datetime.to_string(cert_date_end),
            })
            if spain_dt > cert_date_end:
                raise ValidationError(_("The certificate is expired since %s", certificate.date_end))
        return certificates
