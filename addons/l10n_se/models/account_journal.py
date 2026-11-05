# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    _check_ocr_length = models.Constraint(
        'CHECK(l10n_se_invoice_ocr_length >= 6)',
        'OCR Reference Number length need to be greater than 5. '
        'Please correct settings under invoice journal settings.',
    )

    invoice_reference_model = fields.Selection(
        selection_add=[
            ('se_ocr2', 'Sweden OCR Level 1 & 2 (1255)'),
            ('se_ocr3', 'Sweden OCR Level 3 (12658)'),
            ('se_ocr4', 'Sweden OCR Level 4 (001271)'),
        ],
        ondelete={'se_ocr2': 'set default', 'se_ocr3': 'set default', 'se_ocr4': 'set default'},
    )
    l10n_se_invoice_ocr_length = fields.Integer(string='OCR Number Length', help="Total length of OCR Reference Number including checksum.", default=6)
