# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
from odoo import api, models
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter
from pathlib import Path
from reportlab.graphics.shapes import Drawing as ReportLabDrawing, Image as ReportLabImage
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
        assert isinstance(barcode_drawing, ReportLabDrawing)
        zoom_x = barcode_drawing.transform[0]
        zoom_y = barcode_drawing.transform[3]
        cross_width = CH_QR_CROSS_SIZE_RATIO * width
        cross_height = CH_QR_CROSS_SIZE_RATIO * height
        cross_path = Path(__file__).absolute().parent / CH_QR_CROSS_FILE
        qr_cross = ReportLabImage((width/2 - cross_width/2) / zoom_x, (height/2 - cross_height/2) / zoom_y, cross_width / zoom_x, cross_height / zoom_y, cross_path.as_posix())
        barcode_drawing.add(qr_cross)

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        # OVERRIDE
        res = super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids)
        if not res_ids:
            return res
        report = self._get_report(report_ref)
        if self._is_invoice_report(report_ref):
            invoices = self.env[report.model].browse(res_ids)
            # Determine which invoices need a QR/ISR.
            qr_inv_ids = []
            isr_inv_ids = []
            for invoice in invoices:
                # avoid duplicating existing streams
                if report.attachment_use and report.retrieve_attachment(invoice):
                    continue
                if invoice.l10n_ch_is_qr_valid:
                    qr_inv_ids.append(invoice.id)
                elif invoice.company_id.country_code == 'CH' and invoice.l10n_ch_isr_valid:
                    isr_inv_ids.append(invoice.id)
            # Render the additional reports.
            streams_to_append = {}
            if qr_inv_ids:
                qr_res = self._render_qweb_pdf_prepare_streams(
                    'l10n_ch.l10n_ch_qr_report',
                    {
                        **data,
                        'skip_headers': False,
                    },
                    res_ids=qr_inv_ids,
                )
                header = self.env.ref('l10n_ch.l10n_ch_qr_header', raise_if_not_found=False)
                if header:
                    # Make a separated rendering to get the a page containing the company header. Then, merge the qr bill with it.

                    header_res = self._render_qweb_pdf_prepare_streams(
                        'l10n_ch.l10n_ch_qr_header',
                        {
                            **data,
                            'skip_headers': True,
                        },
                        res_ids=qr_inv_ids,
                    )

                    for invoice_id, stream in qr_res.items():
                        qr_pdf = OdooPdfFileReader(stream['stream'], strict=False)
                        header_pdf = OdooPdfFileReader(header_res[invoice_id]['stream'], strict=False)

                        page = header_pdf.getPage(0)
                        page.mergePage(qr_pdf.getPage(0))

                        output_pdf = OdooPdfFileWriter()
                        output_pdf.addPage(page)
                        new_pdf_stream = io.BytesIO()
                        output_pdf.write(new_pdf_stream)
                        streams_to_append[invoice_id] = {'stream': new_pdf_stream}
                else:
                    for invoice_id, stream in qr_res.items():
                        streams_to_append[invoice_id] = stream

            if isr_inv_ids:
                isr_res = self._render_qweb_pdf_prepare_streams('l10n_ch.l10n_ch_isr_report', data, res_ids=isr_inv_ids)
                for invoice_id, stream in isr_res.items():
                    streams_to_append[invoice_id] = stream

            # Add to results
            for invoice_id, additional_stream in streams_to_append.items():
                invoice_stream = res[invoice_id]['stream']
                writer = OdooPdfFileWriter()
                writer.appendPagesFromReader(OdooPdfFileReader(invoice_stream, strict=False))
                writer.appendPagesFromReader(OdooPdfFileReader(additional_stream['stream'], strict=False))
                new_pdf_stream = io.BytesIO()
                writer.write(new_pdf_stream)
                res[invoice_id]['stream'] = new_pdf_stream
                invoice_stream.close()
                additional_stream['stream'].close()
        return res

    def get_paperformat(self):
        if self.env.context.get('snailmail_layout'):
            if self.report_name == 'l10n_ch.qr_report_main':
                return self.env.ref('l10n_ch.paperformat_euro_no_margin')
            if self.report_name == 'l10n_ch.qr_report_header':
                return self.env.ref('l10n_din5008.paperformat_euro_din')
        return super(IrActionsReport, self).get_paperformat()
