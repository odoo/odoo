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
            return False

        if self.code == "0":
            return document_number

        # in CFE v25, CFE series now support numbers. The document number sequence could be
        # 2 alphanumeric + 7 digits OR 1 alphanumeric + 7 digits
        # Users are now expected to input a valid document number
        document_number = document_number.strip()
        if match := re.match(r'^([A-Za-z0-9]{1,2}) *(\d{7})$', document_number):
            series, number = match.group(1, 2)
            document_number = series.upper() + number
        else:
            raise UserError(_(
                "%(document_number)s is not a valid value for %(document_type)s.\n"
                "The document number must be entered with a maximum of 2 alphanumeric characters for the first part "
                "and exactly 7 numbers for the second. The following are examples of valid document numbers:\n"
                "- XX0000001\n- YY0000123\n- A0000001\n- 1A0000007\n- 880000001\n- 80000001",
                document_number=document_number,
                document_type=self.name,
            ))
        return document_number
