# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import models
from odoo.exceptions import UserError


class L10n_LatamDocumentType(models.Model):
    _inherit = 'l10n_latam.document.type'

    def _format_document_number(self, document_number):
        # EXTENDS 'l10n_latam_invoice_document'
        self.ensure_one()
        if self.country_id.code != 'PA' or not document_number:
            return super()._format_document_number(document_number)
        # DGI Ficha Técnica B07: numeroDocumentoFiscal is exactly 10 digits
        if not re.fullmatch(r'[0-9]{1,10}', document_number):
            raise UserError(self.env._("The document number must contain only digits and have at most 10 digits."))
        return document_number.zfill(10)
