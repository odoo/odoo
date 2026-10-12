from odoo import models
from odoo.tools import SQL


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_last_sequence_domain(self, relaxed=False):
        condition = super()._get_last_sequence_domain(relaxed)
        if self.company_id.account_fiscal_country_id.code == 'CR' and self.l10n_latam_use_documents:
            condition = SQL("%s AND l10n_latam_document_type_id = %s", condition, self.l10n_latam_document_type_id.id or 0)
        return condition
