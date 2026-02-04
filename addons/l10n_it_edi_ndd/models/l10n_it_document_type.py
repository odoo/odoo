from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class L10nItDocumentType(models.Model):
    _name = 'l10n_it.document.type'
    _description = 'Italian Document Type'

    name = fields.Char(required=True, help='The document type name', translate=True)
    code = fields.Char(required=True)
    # not used, to be removed in master
    type = fields.Selection(
        selection=[
            ('sale', "Sale"),
            ('purchase', "Purchase"),
        ],
    )

    def _compute_display_name(self):
        for document_type in self:
            document_type.display_name = f"{document_type.code} - {document_type.name}"

    @api.constrains('code')
    def _check_code_unique(self):
        duplicate = self._read_group(
            domain=[],
            groupby=['code'],
            aggregates=['id:recordset'],
            having=[('__count', '>', 1)],
            limit=1,
        )
        if duplicate:
            raise ValidationError(_('Document Type code must be unique.'))
