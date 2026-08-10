from odoo import models


class AccountEDIProxyUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    def _get_company_details(self):
        return {
            **super()._get_company_details(),
            "peppol_validation_token": self.company_id.peppol_validation_token,
        }
