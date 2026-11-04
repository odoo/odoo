# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields
from odoo.tools import SQL


class AccountInvoiceReport(models.Model):

    _inherit = 'account.invoice.report'

    l10n_latam_document_type_id = fields.Many2one('l10n_latam.document.type', 'Document Type', index=True)
    _depends = {'account.move': ['l10n_latam_document_type_id'],}

    def _select(self) -> SQL:
        return SQL("%s, move.l10n_latam_document_type_id as l10n_latam_document_type_id",
                   super()._select())
