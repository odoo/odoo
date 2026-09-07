from odoo import models


class AccountEDIProxyUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    def _get_company_details(self):
        return {
            **super()._get_company_details(),
            "peppol_validation_token": self.company_id.peppol_validation_token,
        }

    def _peppol_get_new_tax_data_documents(self):
        return self._peppol_get_new_unacknowledged_messages(endpoint='get_tax_data_documents')

    def _cron_peppol_get_new_tax_data_documents(self):
        edi_users = self.search([
            ('company_id.account_peppol_proxy_state', 'in', ('sender', 'smp_registration', 'receiver')),
            ('proxy_type', 'in', self._get_peppol_proxy_types()),
        ])
        edi_users._peppol_get_new_tax_data_documents()
