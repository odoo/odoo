# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'

    l10n_latam_document_type_id = fields.Many2one('l10n_latam.document.type', 'Document Type')

    def _select_list(self, table):
        return super()._select_list(table) + [table.move_id.l10n_latam_document_type_id]
