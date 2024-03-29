# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, models
from odoo.exceptions import UserError
import re


class L10nAccountDocumentType(models.Model):

    _inherit = 'l10n_latam.document.type'

    def _format_document_number(self, document_number):
        """ format and validate the document_number"""
        self.ensure_one()
        if self.country_id.code != "UY":
            return super()._format_document_number(document_number)

        if not document_number:
            return

        document_number = document_number.strip()
        number_part = re.findall(r'[\d]+', document_number)
        serie_part = re.findall(r'^[A-Za-z]+', document_number)

        if not serie_part or len(serie_part) > 1 or len(serie_part[0]) > 2 \
           or not number_part or len(number_part) > 1 or len(number_part[0]) > 7:
            raise UserError(_('Please introduce a valid Document number: 2 letters and 7 digits (XX0000001)'))

        return serie_part[0].upper() + number_part[0].zfill(7)
