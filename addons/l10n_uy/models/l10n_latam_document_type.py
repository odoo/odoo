# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, models
from odoo.exceptions import UserError
import re


class L10n_LatamDocumentType(models.Model):
    _inherit = 'l10n_latam.document.type'

    def _format_document_number(self, document_number):
        """ format and validate the document_number"""
        self.ensure_one()
        if self.country_id.code != "UY":
            return super()._format_document_number(document_number)

        if not document_number:
            return False

        if self.code == "0":
            return document_number

        document_number = document_number.strip()
        number_part = re.findall(r'[\d]+', document_number)
        serie_part = re.findall(r'^[A-Za-z]+', document_number)
        if not serie_part or len(serie_part) > 1 or len(serie_part[0]) > 2 \
           or not number_part or len(number_part) > 1 or len(number_part[0]) > 7:
            raise UserError(_(
                "%(document_number)s is not a valid value for %(document_type)s.\n"
                "The document number must be entered with a maximum of 2 letters for the first part "
                "and 7 numbers for the second. The following are examples of valid document numbers:\n"
                "- XX0000001\n - YY0000123\n - A0000001",
                document_number=document_number,
                document_type=self.name,
            ))
        return serie_part[0].upper() + number_part[0].zfill(7)
