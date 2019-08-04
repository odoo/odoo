# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_l10n_latam_documents_domain(self):
        self.ensure_one()
        domain = super()._get_l10n_latam_documents_domain()
        if (self.journal_id.l10n_latam_use_documents and
                self.journal_id.company_id.country_id == self.env.ref('base.cl')):
            internal_type = self._context.get('default_type')
            if internal_type in ['in_invoice', 'out_invoice']:
                seq = self.journal_id.sequence_id
            else:
                seq = self.journal_id.refund_sequence_id
            domain = [('id', '=', seq.l10n_latam_document_type_id.id)]
        return domain

    def post(self):
        internal_type = self._context.get('default_type')
        for rec in self.filtered(lambda x: x.l10n_latam_use_documents and not x.l10n_latam_document_number and
                                 self.journal_id.company_id.country_id == self.env.ref('base.cl') and
                                 internal_type in ['out_invoice', 'out_refund']):
            if internal_type == 'out_invoice':
                sequence = self.journal_id.sequence_number_next
            else:
                sequence = self.journal_id.refund_sequence_number_next
            rec.l10n_latam_document_number = sequence
        return super().post()
