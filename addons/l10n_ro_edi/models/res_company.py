import base64
import binascii
from datetime import datetime

import requests
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.tools.safe_eval import json
from odoo.tools.urls import urljoin as url_join


class ResCompany(models.Model):
    _inherit = "res.company"
    _CREDENTIAL_FIELDS = {
        "l10n_ro_edi_client_secret": "l10n_ro_edi_client_secret",
        "l10n_ro_edi_access_token": "l10n_ro_edi_access_token",
        "l10n_ro_edi_refresh_token": "l10n_ro_edi_refresh_token",
    }

    l10n_ro_edi_client_id = fields.Char(string="eFactura Client ID")
    l10n_ro_edi_client_secret = fields.Char(
        string="Client Secret",
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
    )
    l10n_ro_edi_access_token = fields.Char(
        string="Access Token",
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
    )
    l10n_ro_edi_refresh_token = fields.Char(
        string="Refresh Token",
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
    )
    l10n_ro_edi_access_expiry_date = fields.Date(string="Access Token Expiry Date")
    l10n_ro_edi_refresh_expiry_date = fields.Date(string="Refresh Token Expiry Date")
    l10n_ro_edi_callback_url = fields.Char(compute="_compute_l10n_ro_edi_callback_url")
    l10n_ro_edi_test_env = fields.Boolean(
        string="Use Test Environment",
        default=True,
    )
    l10n_ro_edi_anaf_imported_inv_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Select journal for SPV imported bills",
        compute="_compute_l10n_ro_edi_anaf_imported_inv_journal_id",
        store=True,
        readonly=False,
        domain="[('type', '=', 'purchase')]",
    )

    @api.depends("country_code")
    def _compute_l10n_ro_edi_callback_url(self):
        """Callback URLs are used for generating client_id and client_secret from l10n_ro_edi's setting."""
        for company in self:
            if company.country_code == "RO":
                company.l10n_ro_edi_callback_url = url_join(
                    request.httprequest.url_root, "l10n_ro_edi/callback/%s" % company.id
                )
            else:
                company.l10n_ro_edi_callback_url = False

    @api.depends("country_code")
    def _compute_l10n_ro_edi_anaf_imported_inv_journal_id(self):
        for company in self:
            company.l10n_ro_edi_anaf_imported_inv_journal_id = False
            if company.country_code == "RO":
                company.l10n_ro_edi_anaf_imported_inv_journal_id = self.env[  # noqa: E8507 - one lookup per company, on its own journals
                    "account.journal"
                ].search(
                    [
                        ("type", "=", "purchase"),
                        *self.env["account.journal"]._check_company_domain(company.id),
                    ],
                    limit=1,
                )

    def _l10n_ro_edi_log_message(self, message: str, func: str):
        with self.pool.cursor() as cr:
            self = self.with_env(self.env(cr=cr))
            self.env["ir.logging"].sudo().create(
                {
                    "name": "l10n_ro_edi_log",
                    "type": "server",
                    "level": "INFO",
                    "dbname": self.env.cr.dbname,
                    "message": message,
                    "func": func,
                    "path": "",
                    "line": "1",
                }
            )
            self.env.cr.commit()

    def _l10n_ro_edi_process_token_response(self, response_json):
        """
        To be called just after processing the json response from https://logincert.anaf.ro/anaf-oauth2/v1/token
        This method reads and process the json, and writes the token fields on the company.
        """
        self.check_singleton()
        if "access_token" not in response_json or "refresh_token" not in response_json:
            raise ValidationError(_("Token not found.\nResponse: %s", response_json))

        # The access_token is in JWT format, which consists of 3 parts separated by '.':
        # Header, Payload, and Signature. We only need the Payload part to decode the token
        # and get the access expiry date
        payload = response_json["access_token"].split(".")[1]
        payload += "=" * (-len(payload) % 4)
        decoded_payload = base64.b64decode(payload, altchars=b"-_", validate=True)
        access_token_obj = json.loads(decoded_payload)
        access_expiry_date = datetime.fromtimestamp(access_token_obj["exp"])
        refresh_expiry_date = datetime.now() + relativedelta(years=3)
        self.write(
            {
                "l10n_ro_edi_access_token": response_json["access_token"],
                "l10n_ro_edi_refresh_token": response_json["refresh_token"],
                "l10n_ro_edi_access_expiry_date": access_expiry_date,
                "l10n_ro_edi_refresh_expiry_date": refresh_expiry_date,
            }
        )

    def _l10n_ro_edi_refresh_access_token(self):
        """
        Uses the saved client_id, client_secret, and refresh_token on the company (self)
        to make request to the SPV and renew the company's token fields.
        """
        self.check_singleton()
        if not self.l10n_ro_edi_client_id or not self.l10n_ro_edi_client_secret:
            raise UserError(_("Client ID and Client Secret field must be filled."))

        response = self._post_held_oauth2_refresh_grant(
            "https://logincert.anaf.ro/anaf-oauth2/v1/token",
            "l10n_ro_edi_refresh_token",
            {
                "client_id": self.l10n_ro_edi_client_id,
                "client_secret": self.l10n_ro_edi_client_secret,
            },
            purpose="l10n_ro_edi",
        )
        if response is None:
            raise UserError(_("Refresh token not found"))
        response_json = response.json()
        self._l10n_ro_edi_process_token_response(response_json)

    def _cron_l10n_ro_edi_refresh_access_token(self):
        """
        This CRON method will be run every 30 days to refresh the following fields on the company:

         - ``l10n_ro_edi_access_token``
         - ``l10n_ro_edi_refresh_token``
         - ``l10n_ro_edi_access_expiry_date``
         - ``l10n_ro_edi_refresh_expiry_date``
        """
        ro_companies = (
            self.env["res.company"]
            .sudo()
            .search(
                [
                    ("company_credential_id", "!=", False),
                    ("l10n_ro_edi_client_id", "!=", False),
                ]
            )
            .filtered(
                lambda company: (
                    company.l10n_ro_edi_refresh_token
                    and company.l10n_ro_edi_client_secret
                )
            )
        )
        for company in ro_companies:
            error_cause = ""
            try:
                company._l10n_ro_edi_refresh_access_token()
            except ValidationError as e:
                # From access/refresh token not found after sending request
                error_cause = e
            except requests.exceptions.RequestException as e:
                error_cause = _("Error when converting response to json: %s", e)
            except binascii.Error as e:
                error_cause = _("Error when decoding the access token payload: %s", e)
            except Exception as e:
                error_cause = _("Error when refreshing the access token: %s", e)

            if error_cause:
                error_header = _(
                    "Refresh token failed [company=%(company_id)s]",
                    company_id=company.id,
                )
                self._l10n_ro_edi_log_message(
                    message=f"{error_header}\n{error_cause}",
                    func="_cron_l10n_ro_edi_refresh_access_token",
                )

    def _cron_l10n_ro_edi_sync_invoices(self):
        """
        This CRON method will be run every 24 hours to synchronize the invoices and the bills with the ANAF
        """
        ro_companies = (
            self.env["res.company"]
            .sudo()
            .search(
                [
                    ("company_credential_id", "!=", False),
                    ("l10n_ro_edi_client_id", "!=", False),
                ]
            )
            .filtered(
                lambda company: (
                    company.l10n_ro_edi_refresh_token
                    and company.l10n_ro_edi_client_secret
                )
            )
        )
        for company in ro_companies:
            try:
                self.env["account.move"].with_company(
                    company
                )._l10n_ro_edi_import_invoices()
            except UserError as e:
                self._l10n_ro_edi_log_message(
                    message=f"{company.id}\n{e}",
                    func="_cron_l10n_ro_edi_sync_invoices",
                )
