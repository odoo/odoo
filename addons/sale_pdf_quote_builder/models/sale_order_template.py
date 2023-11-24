# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
from odoo import api, fields, models, _
import base64
from odoo.exceptions import ValidationError
from PyPDF2 import PdfFileReader
try:
    from PyPDF2.errors import PdfReadError
except ImportError:
    from PyPDF2.utils import PdfReadError

class SaleOrderTemplate(models.Model):
    _inherit = 'sale.order.template'

    sale_header = fields.Binary(
        string="Header pages", default=lambda self: self.env.company.sale_header)
    sale_header_name = fields.Char(default=lambda self: self.env.company.sale_header_name)
    sale_footer = fields.Binary(
        string="Footer pages", default=lambda self: self.env.company.sale_footer)
    sale_footer_name = fields.Char(default=lambda self: self.env.company.sale_footer_name)

    @api.constrains('sale_header', 'sale_footer')
    def _check_valid_header_and_footer(self):
        try:
            if self.sale_header:
                PdfFileReader(io.BytesIO(base64.b64decode(self.sale_header)), strict=False, overwriteWarnings=False)
            if self.sale_footer:
                PdfFileReader(io.BytesIO(base64.b64decode(self.sale_footer)), strict=False, overwriteWarnings=False)
        except PdfReadError:
            raise ValidationError(_("The uploaded file is not a valid PDF. Please upload a valid PDF file."))
