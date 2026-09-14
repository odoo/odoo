from odoo import api, models

from odoo.addons.iap.tools import iap_tools


class IapEnrichApi(models.AbstractModel):
    _name = "iap.enrich.api"
    _description = "IAP Lead Enrichment API"
    _DEFAULT_ENDPOINT = "https://iap-services.odoo.com"

    @api.model
    def _contact_iap(self, local_endpoint, params):
        account = self.env["iap.account"].get("reveal")
        dbuuid = self.env["ir.config_parameter"].sudo().get_param("database.uuid")
        params["account_token"] = account.sudo().account_token
        params["dbuuid"] = dbuuid
        base_url = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("enrich.endpoint", self._DEFAULT_ENDPOINT)
        )
        return iap_tools.iap_jsonrpc(
            base_url + local_endpoint, params=params, timeout=300, env=self.env
        )

    @api.model
    def _request_enrich(self, lead_emails):
        """Contact endpoint to get enrichment data.

        :param lead_emails: dict{lead_id: email}
        :return: dict{lead_id: company data or False}
        :raise InsufficientCreditError: not enough credits on the 'reveal' account; its
          ``data`` holds the remaining credit, the service name and the purchase URL
        """
        params = {
            "domains": lead_emails,
        }
        return self._contact_iap("/iap/clearbit/1/lead_enrichment_email", params=params)
