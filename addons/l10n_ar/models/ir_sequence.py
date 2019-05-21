# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.addons.l10n_ar.models.l10n_latam_document_type import L10nLatamDocumentType


class IrSequence(models.Model):

    _inherit = 'ir.sequence'

    l10n_ar_letter = fields.Selection(
        L10nLatamDocumentType._l10n_ar_letters,
        'Letter',
    )
