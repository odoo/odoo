from odoo import models


class AccountEdiProxyClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    def _peppol_get_import_sale_journal(self, company):
        # EXTENDS 'account_peppol'

        return (
            self.env['account.journal'].search(
                [
                    *self.env['account.journal']._check_company_domain(company),
                    ('type', '=', 'sale'),
                    ('is_self_billing', '=', 'True'),
                ],
                limit=1,
            )
            or super()._peppol_get_import_sale_journal(company)
        )
