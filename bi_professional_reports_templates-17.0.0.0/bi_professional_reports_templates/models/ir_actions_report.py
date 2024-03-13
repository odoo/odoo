# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import io

from base64 import b64decode
from io import BytesIO
from PyPDF2 import PdfFileReader, PdfFileWriter


from odoo import api, fields, models





class Report(models.Model):
    _inherit = "ir.actions.report"
    @api.model
    def _run_wkhtmltopdf(self,bodies,report_ref=False,header=None,footer=None,landscape=False,specific_paperformat_args=None,set_viewport_size=False):
        rec = super(Report, self)._run_wkhtmltopdf(bodies,report_ref=report_ref,header=header,footer=footer,landscape=landscape,specific_paperformat_args=specific_paperformat_args,set_viewport_size=set_viewport_size,)
        company = self.env.company
        set_pdf_watermark = None
        if company.watermark_pdf:
            set_pdf_watermark = b64decode(company.watermark_pdf)
        if not set_pdf_watermark:
            return rec
        get_pdf = PdfFileWriter()
        set_watermark = PdfFileReader(BytesIO(set_pdf_watermark)).getPage(0)
        if not set_watermark:
            return rec
        for record in PdfFileReader(BytesIO(rec)).pages:
            set_page = get_pdf.addBlankPage( record.mediaBox.getWidth(), record.mediaBox.getHeight())
            set_page.mergePage(set_watermark)
            set_page.mergePage(record)

        set_content = BytesIO()
        get_pdf.write(set_content)

        return set_content.getvalue()
