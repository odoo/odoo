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
        if report.report_name in ('account.report_invoice_with_payments', 'account.report_invoice'):
            invoices = self.env[report.model].browse(res_ids)
            # Determine which invoices need a QR/ISR.
            qr_inv_ids = []
            isr_inv_ids = []
            for invoice in invoices:
                if invoice.l10n_ch_is_qr_valid:
                    qr_inv_ids.append(invoice.id)
                elif invoice.company_id.country_code == 'CH' and invoice.l10n_ch_isr_valid:
                    isr_inv_ids.append(invoice.id)
            # Render the additional reports.
            streams_to_append = {}
            if qr_inv_ids:
                qr_res = self._render_qweb_pdf_prepare_streams('l10n_ch.l10n_ch_qr_report', data, res_ids=qr_inv_ids)
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
