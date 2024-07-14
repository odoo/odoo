# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class DocumentSpreadsheetShare(models.Model):
    _name = 'documents.shared.spreadsheet'
    _inherit = 'spreadsheet.mixin'
    _description = 'Copy of a shared spreadsheet'

    share_id = fields.Many2one('documents.share', required=True, ondelete='cascade')
    document_id = fields.Many2one('documents.document', required=True, ondelete='cascade')
    excel_export = fields.Binary()

    _sql_constraints = [
        ('_unique', 'unique(share_id, document_id)', "Only one freezed spreadsheet per document share"),
    ]
