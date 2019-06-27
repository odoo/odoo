# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class AccountInvoiceReport(models.Model):

    _inherit = 'account.invoice.report'

    l10n_latam_document_type_id = fields.Many2one('l10n_latam.document.type', 'Document Type', index=True)
    _depends = {'account.invoice': ['l10n_latam_document_type_id'],}

    def _select(self):
        return super()._select() + ", sub.l10n_latam_document_type_id as l10n_latam_document_type_id"

    def _sub_select(self):
        return super()._sub_select() + ", ai.l10n_latam_document_type_id as l10n_latam_document_type_id"

    def _group_by(self):
        return super()._group_by() + ", ai.l10n_latam_document_type_id"
