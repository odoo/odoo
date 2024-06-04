# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
from collections import OrderedDict
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
            qr_inv_ids = []
            for invoice in invoices:
                # avoid duplicating existing streams
                if report.attachment_use and report.retrieve_attachment(invoice):
                    continue
                if invoice.l10n_ch_is_qr_valid:
                    qr_inv_ids.append(invoice.id)
            # Render the additional reports.
            collected_streams = OrderedDict()
            for res_id in res_ids:
                collected_streams[res_id] = {
                    'stream': None,
                    'attachment': None,
                }
            if qr_inv_ids:
                qr_html = self._render_qweb_html('l10n_ch.l10n_ch_qr_report', qr_inv_ids, data={**data, 'skip_headers': True})[0]
                qr_bodies, html_ids, _header, _footer, specific_paperformat_args = self._prepare_html(qr_html, report_model=self._get_report('l10n_ch.l10n_ch_qr_report').model)
                header = self.env.ref('l10n_ch.l10n_ch_qr_header', raise_if_not_found=False)
                if header:
                    header_html = self._render_qweb_html('l10n_ch.l10n_ch_qr_header', qr_inv_ids, data={**data, 'skip_headers': True})[0]
                    header_bodies, _html_ids, header, _footer, _specific_paperformat_args = self._prepare_html(header_html, report_model=self._get_report('l10n_ch.l10n_ch_qr_header').model)
                    pdf_content = self._run_wkhtmltopdf(
                        [header_body + qr_body for header_body, qr_body in zip(header_bodies, qr_bodies)],
                        report_ref='l10n_ch.l10n_ch_qr_report',
                        header=header,
                        footer=None,
                        specific_paperformat_args=specific_paperformat_args,
                    )
                else:
                    pdf_content = self._run_wkhtmltopdf(
                        qr_bodies,
                        report_ref='l10n_ch.l10n_ch_qr_report',
                        header=None,
                        footer=None,
                        specific_paperformat_args=specific_paperformat_args,
                    )

                collected_streams = self.split_pdf(io.BytesIO(pdf_content), html_ids, collected_streams, html_ids)

                # Add to results
                for invoice_id, additional_stream in collected_streams.items():
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
