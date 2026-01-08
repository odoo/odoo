from odoo import fields, models


class L10nItDocumentType(models.Model):
    _name = 'l10n_it.document.type'
    _description = 'Italian Document Type'

    name = fields.Char(required=True, help='The document type name', translate=True)
    code = fields.Char(required=True)
    type = fields.Selection(
        selection=[
            ('sale', "Sale"),
            ('purchase', "Purchase"),
        ],
        required=True,
    )

    def _compute_display_name(self):
        for document_type in self:
            document_type.display_name = f"{document_type.code} - {document_type.name}"
