# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models

from odoo.addons.account.report.account_invoice_report import related_sql


class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'

    l10n_latam_document_type_id = fields.Many2one('l10n_latam.document.type', 'Document Type', **related_sql('move_id.l10n_latam_document_type_id'))
