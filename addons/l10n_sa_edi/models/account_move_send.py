import io
import logging

from odoo import api, fields, models
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter

_logger = logging.getLogger(__name__)


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _get_alerts(self, moves, moves_data):
        res = super()._get_alerts(moves, moves_data)
        res.update(moves._l10n_sa_get_alerts())
        return res

    @api.model
    def _is_sa_edi_testing_applicable(self, move):
        return move._l10n_sa_is_phase_2_applicable() and move.company_id.l10n_sa_api_mode != 'prod' and move.l10n_sa_edi_state not in ('accepted', 'warning')

    @api.model
    def _is_sa_edi_production_applicable(self, move):
        return move._l10n_sa_is_phase_2_applicable() and move.company_id.l10n_sa_api_mode == 'prod' and move.l10n_sa_edi_state not in ('accepted', 'warning')

    def _get_all_extra_edis(self) -> dict:
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res.update({'sa_edi': {'label': self.env._("To ZATCA"), 'is_applicable': self._is_sa_edi_production_applicable}})
        res.update({'sa_edi_test': {'label': self.env._("To ZATCA (Testing)"), 'is_applicable': self._is_sa_edi_testing_applicable}})
        return res

    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        for invoice, invoice_data in invoices_data.items():
            if 'sa_edi' in invoice_data['extra_edis'] or 'sa_edi_test' in invoice_data['extra_edis']:
                invoice.l10n_sa_edi_document_id._l10n_sa_post_zatca_edi(len(invoices_data.keys()) == 1)

    def _hook_invoice_document_after_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS account
        super()._hook_invoice_document_after_pdf_report_render(invoice, invoice_data)
        if 'sa_edi' not in invoice_data['extra_edis'] and 'sa_edi_test' not in invoice_data['extra_edis']:
            return

        edi_document = invoice.l10n_sa_edi_document_id
        attachment = edi_document.sudo().attachment_id
        if not attachment or not attachment.raw:
            if edi_document.state in ['accepted', 'warning', 'rejected']:
                _logger.warning("No attachment found for invoice %s", invoice.name)
            return

        xml_content = attachment.raw.content
        file_name = attachment.name
        # Read pdf content.
        pdf_values = invoice_data.get('pdf_attachment_values')
        reader_buffer = io.BytesIO(pdf_values['raw'])
        reader = OdooPdfFileReader(reader_buffer, strict=False)

        # Post-process.
        pdf_writer = OdooPdfFileWriter()
        pdf_writer.cloneReaderDocumentRoot(reader)
        pdf_writer.addAttachment(file_name, xml_content, subtype='text/xml')
        if not pdf_writer.is_pdfa:
            try:
                pdf_writer.convert_to_pdfa()
            except Exception:
                _logger.exception("Error while converting to PDF/A")
            content = self.env['ir.qweb']._render(
                'account_edi_ubl_cii.account_invoice_pdfa_3_facturx_metadata',
                {
                    'title': invoice.name,
                    'date': fields.Date.context_today(self),
                },
            )
            if "<pdfaid:conformance>B</pdfaid:conformance>" in content:
                content.replace("<pdfaid:conformance>B</pdfaid:conformance>", "<pdfaid:conformance>A</pdfaid:conformance>")
            pdf_writer.add_file_metadata(content.encode())
