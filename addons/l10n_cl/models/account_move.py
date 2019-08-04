# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_l10n_latam_documents_domain(self):
        self.ensure_one()
        domain = super()._get_l10n_latam_documents_domain()
        if self.journal_id.company_id.country_id == self.env.ref('base.cl'):
            internal_type = self._context.get('default_type')
            if internal_type in ['in_invoice', 'out_invoice']:
                seq = self.journal_id.sequence_id
            else:
                seq = self.journal_id.refund_sequence_id
            domain = [('id', '=', seq.l10n_latam_document_type_id.id)]
        return domain

