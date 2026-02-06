# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class L10nCoEdiDocumentType(models.Model):
    _name = 'l10n_co_edi.document.type'
    _description = 'DIAN Electronic Document Type'
    _order = 'code'

    code = fields.Char(
        string='Code',
        required=True,
        help='DIAN document type code for UBL XML.',
    )
    name = fields.Char(
        string='Name',
        required=True,
        translate=True,
    )
    description = fields.Char(
        string='Description',
        translate=True,
    )
    is_dee = fields.Boolean(
        string='Is Equivalent Document',
        help='True if this is a Documento Equivalente Electronico (DEE).',
    )
    active = fields.Boolean(default=True)

    _unique_code = models.Constraint(
        'UNIQUE(code)',
        'Document type code must be unique.',
    )
