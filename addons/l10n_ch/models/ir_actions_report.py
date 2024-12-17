# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
from odoo import api, models
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter
from pathlib import Path
from reportlab.graphics.shapes import Image as ReportLabImage
from reportlab.lib.units import mm

CH_QR_CROSS_SIZE_RATIO = 0.1522 # Ratio between the side length of the Swiss QR-code cross image and the QR-code's
CH_QR_CROSS_FILE = Path('../static/src/img/CH-Cross_7mm.png') # Image file containing the Swiss QR-code cross to add on top of the QR-code


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.model
    def get_available_barcode_masks(self):
        rslt = super(IrActionsReport, self).get_available_barcode_masks()
        rslt['ch_cross'] = self.apply_qr_code_ch_cross_mask
        return rslt

    @api.model
    def apply_qr_code_ch_cross_mask(self, width, height, barcode_drawing):
        cross_width = CH_QR_CROSS_SIZE_RATIO * width
        cross_height = CH_QR_CROSS_SIZE_RATIO * height
        cross_path = Path(__file__).absolute().parent / CH_QR_CROSS_FILE
        qr_cross = ReportLabImage((width/2 - cross_width/2) / mm, (height/2 - cross_height/2) / mm, cross_width / mm, cross_height / mm, cross_path.as_posix())
        barcode_drawing.add(qr_cross)

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        # OVERRIDE
        res = super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids)
        if not res_ids:
            return res
        report = self._get_report(report_ref)
        if self._is_invoice_report(report_ref):
            invoices = self.env[report.model].browse(res_ids)

            # Determine which invoices need a QR.
            qr_inv_ids = invoices.filtered('l10n_ch_is_qr_valid').ids

            if qr_inv_ids:
                qr_res = self._render_qweb_pdf_prepare_streams(
                    'l10n_ch.l10n_ch_qr_report',
                    data,
                    res_ids=qr_inv_ids,
                )

                for invoice_id, stream in qr_res.items():
                    qr_pdf = OdooPdfFileReader(stream['stream'], strict=False)
                    res_pdf = OdooPdfFileReader(res[invoice_id]['stream'], strict=False)

                    last_page = res_pdf.getPage(-1)
                    last_page.mergePage(qr_pdf.getPage(0))

                    output_pdf = OdooPdfFileWriter()

                    # Add all pages from the original PDF except the last one
                    for page_num in range(res_pdf.getNumPages() - 1):
                        output_pdf.addPage(res_pdf.getPage(page_num))

                    output_pdf.addPage(last_page)  # Add the modified last page (with the QR code merged)

                    new_pdf_stream = io.BytesIO()
                    output_pdf.write(new_pdf_stream)
                    new_pdf_stream.seek(0)
                    res[invoice_id]['stream'].close()
                    res[invoice_id]['stream'] = new_pdf_stream
                    stream['stream'].close()

        return res

    def get_paperformat(self):
        if self.env.context.get('snailmail_layout'):
            if self.report_name == 'l10n_ch.qr_report_main':
                return self.env.ref('l10n_ch.paperformat_euro_no_margin')
            if self.report_name == 'l10n_ch.qr_report_header':
                return self.env.ref('l10n_din5008.paperformat_euro_din')
        return super(IrActionsReport, self).get_paperformat()
