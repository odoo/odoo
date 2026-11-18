import base64
from contextlib import contextmanager

import requests
from lxml import etree

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools import file_path, format_date, zeep
from odoo.tools.zeep.exceptions import Error as ZeepError, Fault, TransportError

from odoo.addons.certificate.tools import CertificateAdapter
from odoo.addons.l10n_pt_at_webservice.const import (
    PT_AT_WS_ENDPOINT_PROD,
    PT_AT_WS_ENDPOINT_TEST,
    PT_AT_WS_WSDL_PATH,
)
from odoo.addons.l10n_pt_at_webservice.utils.series_ws import ATSeriesClient, ATUsernameToken, raise_for_http_error


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_pt_at_ws_env = fields.Selection(
        selection=[
            ('prod', 'Production'),
            ('test', 'Test'),
            ('offline', 'Offline (no connection)'),
        ],
        string="AT Webservice Environment",
        default='offline',
    )
    l10n_pt_at_ws_username = fields.Char(
        string='AT Webservice Username',
        groups='base.group_system',
        help="Username (NIF/sub-user ID) for the Autoridade Tributária Series webservice.",
    )
    l10n_pt_at_ws_password = fields.Char(
        string='AT Webservice Password',
        groups='base.group_system',
        help="Password for the Autoridade Tributária Series webservice.",
    )
    l10n_pt_at_ws_public_cert_id = fields.Many2one(
        comodel_name='certificate.certificate',
        string='AT Public Key Certificate',
        groups='base.group_system',
        help="The AT public key certificate used to encrypt the password sent to the Series webservice.",
        check_company=True,
    )

    def _l10n_pt_at_ws_get_soap_endpoint(self):
        self.ensure_one()
        if self.l10n_pt_at_ws_env == 'prod':
            return PT_AT_WS_ENDPOINT_PROD
        # The test environment may be pointed elsewhere, e.g. at a local stand-in for the AT;
        # production always calls the AT.
        return self.env['ir.config_parameter'].sudo().get_param('l10n_pt_at_webservice.test_endpoint') or PT_AT_WS_ENDPOINT_TEST

    def _l10n_pt_at_ws_check_configuration(self):
        """Raise when the company lacks what a call to the AT webservice needs."""
        self.ensure_one()
        if not self.l10n_pt_at_ws_username or not self.l10n_pt_at_ws_password:
            raise UserError(self.env._(
                "The AT webservice credentials are not configured for company %(company)s. "
                "Please configure them in the Accounting Settings.",
                company=self.name,
            ))
        # The AT mandates that the password is encrypted with their public key. Without the
        # certificate the request cannot be built, and must not fall back to sending the live
        # credential in clear text.
        if not self.l10n_pt_at_ws_public_cert_id.with_context(bin_size=False).pem_certificate:
            raise UserError(self.env._(
                "The AT public key certificate is not configured for company %(company)s. "
                "It is required to encrypt the password sent to the Autoridade Tributária. "
                "Please configure it in the Accounting Settings.",
                company=self.name,
            ))
        # The AT authenticates the connection itself with the company's client certificate, which it
        # signed: without it, the TLS handshake fails.
        if not self._l10n_pt_at_ws_get_ssl_certificate():
            certificates = self.env['certificate.certificate'].search(
                [('company_id', '=', self.id), ('scope', '=', 'at_series')], order='date_end desc',
            )
            if not certificates:
                raise UserError(self.env._(
                    "No SSL client certificate (scope AT Series) is configured for company %(company)s. "
                    "It is required to connect to the AT webservice. Please add it in the Accounting Settings.",
                    company=self.name,
                ))
            reasons = []
            for certificate in certificates:
                if not certificate.sudo().private_key_id:
                    reasons.append(self.env._("%(certificate)s has no private key", certificate=certificate.name))
                else:
                    reasons.append(self.env._(
                        "%(certificate)s is valid from %(start)s until %(end)s",
                        certificate=certificate.name,
                        start=format_date(self.env, certificate.date_start),
                        end=format_date(self.env, certificate.date_end),
                    ))
            raise UserError(self.env._(
                "No SSL client certificate (scope AT Series) of company %(company)s can be used today: %(reasons)s. "
                "Please add a valid one with its private key, e.g. as a PKCS#12 file, in the Accounting Settings.",
                company=self.name,
                reasons="; ".join(reasons),
            ))

    def _l10n_pt_at_ws_get_ssl_certificate(self):
        """
        The SSL client certificate the company presents to the AT, chosen when calling: its active
        certificate of scope AT Series, valid today and with its private key, that ends last. A
        renewed certificate is thus used from its first day, and an archived one no longer.
        """
        self.ensure_one()
        return self.env['certificate.certificate'].search([
            ('company_id', '=', self.id),
            ('scope', '=', 'at_series'),
            ('is_valid', '=', True),
            ('private_key_id', '!=', False),
        ], order='date_end desc', limit=1)

    @contextmanager
    def _l10n_pt_at_ws_series_client(self):
        """
        Yield a client of the AT's series webservice (``ATSeriesClient``), authenticated with the
        company's credentials, encrypted with the AT's public key, over a session holding the
        company's SSL client certificate. The session is closed on exit.

        A failure to reach the AT or to read its answer, while loading the WSDL or calling an
        operation in the ``with`` block, is raised as a ``UserError`` naming its cause.
        """
        self.ensure_one()
        self._l10n_pt_at_ws_check_configuration()
        public_cert = self.l10n_pt_at_ws_public_cert_id.with_context(bin_size=False)
        try:
            wsse_token = ATUsernameToken(
                self.l10n_pt_at_ws_username,
                self.l10n_pt_at_ws_password,
                base64.b64decode(public_cert.pem_certificate),
            )
        except ValueError as e:
            raise UserError(self.env._(
                "The AT public key certificate %(certificate)s of company %(company)s could not be read: %(error)s",
                certificate=public_cert.name, company=self.name, error=e,
            )) from e

        try:
            with requests.Session() as session:
                session.cert = self._l10n_pt_at_ws_get_ssl_certificate()
                session.mount('https://', CertificateAdapter())
                session.hooks['response'].append(raise_for_http_error)
                client = self._get_zeep_client__(
                    file_path(PT_AT_WS_WSDL_PATH),
                    wsse=wsse_token,
                    session=session,
                    # Lenient on the shape of the answer (`strict=False`), never on its XML: no DTD, entity
                    # or external resource is processed.
                    settings=zeep.Settings(strict=False, forbid_dtd=True, forbid_entities=True, forbid_external=True),
                )
                service = client.create_service(ATSeriesClient.BINDING, self._l10n_pt_at_ws_get_soap_endpoint())
                yield ATSeriesClient(self.env, service)
        except requests.exceptions.SSLError as e:
            raise UserError(self.env._(
                "The secure connection to the AT webservice failed: %(error)s. Check that the SSL client "
                "certificate of company %(company)s is the one the AT signed, and that it is still valid.",
                error=e, company=self.name,
            )) from e
        except requests.exceptions.Timeout as e:
            raise UserError(self.env._("The AT webservice did not answer in time: %(error)s. Please try again later.", error=e)) from e
        except OSError as e:
            raise UserError(self.env._("Could not connect to the AT webservice: %(error)s", error=e)) from e
        except TransportError as e:
            if e.status_code in (401, 403):
                raise UserError(self.env._(
                    "The AT webservice refused the connection (HTTP %(status)s). Check the SSL client "
                    "certificate and the credentials of company %(company)s.",
                    status=e.status_code, company=self.name,
                )) from e
            raise UserError(self.env._(
                "The AT webservice answered with an HTTP error (%(status)s): %(error)s",
                status=e.status_code, error=e.message,
            )) from e
        except Fault as e:
            raise UserError(self.env._("The AT webservice refused the request: %(error)s", error=e.message)) from e
        except (etree.XMLSyntaxError, ZeepError) as e:
            raise UserError(self.env._("The answer of the AT webservice could not be read: %(error)s", error=e)) from e
