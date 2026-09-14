import logging

from requests.exceptions import HTTPError

from odoo import _, api, exceptions, models, release

from odoo.addons.iap.tools import iap_tools

_logger = logging.getLogger(__name__)


class MissingIAPAccountTokenError(Exception):
    """Raised by `_contact_iap` when the partner_autocomplete IAP account has
    no `account_token` configured yet."""


class IapAutocompleteApi(models.AbstractModel):
    _name = "iap.autocomplete.api"
    _description = "IAP Partner Autocomplete API"
    _DEFAULT_ENDPOINT = "https://partner-autocomplete.odoo.com"

    @api.model
    def _contact_iap(self, local_endpoint, action, params, timeout=15):
        # Spending the company's paid IAP credit balance requires the same
        # authority as managing partner records, not just being logged in.
        self.env["res.partner"].browse().check_access("write")
        account = self.env["iap.account"].get("partner_autocomplete")
        if not account.sudo().account_token:
            raise MissingIAPAccountTokenError(_("No account token"))
        params.update(
            {
                "db_uuid": self.env["ir.config_parameter"]
                .sudo()
                .get_param("database.uuid"),
                "db_version": release.version,
                "db_lang": self.env.lang,
                "account_token": account.sudo().account_token,
                "country_code": self.env.company.country_id.code,
                "zip": self.env.company.zip,
            }
        )
        base_url = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("iap.partner_autocomplete.endpoint", self._DEFAULT_ENDPOINT)
        )
        return iap_tools.iap_jsonrpc(
            base_url + local_endpoint + "/" + action,
            params=params,
            timeout=timeout,
            env=self.env,
        )

    @api.model
    def _request_partner_autocomplete(self, action, params, timeout=15):
        """Contact endpoint to get autocomplete data.

        :returns: a 2-element tuple (results, error code)
        :rtype: tuple[dict, Literal[False]] | tuple[Literal[False], str]
        """
        try:
            results = self._contact_iap("/api/dnb/1", action, params, timeout=timeout)
        except (
            ConnectionError,
            HTTPError,
            exceptions.AccessError,
            exceptions.UserError,
        ) as exception:
            _logger.warning("Autocomplete API error: %s", exception)
            return False, str(exception)
        except iap_tools.InsufficientCreditError as exception:
            _logger.warning(
                "Insufficient Credits for Autocomplete Service: %s", exception
            )
            return False, "Insufficient Credit"
        except MissingIAPAccountTokenError:
            return False, "No account token"
        return results, False
