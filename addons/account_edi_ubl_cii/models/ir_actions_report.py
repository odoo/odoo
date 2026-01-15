import io

from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        # EXTENDS base
        collected_streams = super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids)

        # allows to add factur-x.xml to custom PDF templates (comma separated list of template names)
        custom_templates = self.env['ir.config_parameter'].sudo().get_param('account.custom_templates_facturx_list', '')
        custom_templates = [report.strip() for report in custom_templates.split(',')]

        if (
            collected_streams
            and res_ids
            and len(res_ids) == 1
            and self._get_report(report_ref).report_name in custom_templates
        ):
            # Generate and embed Factur-X
            invoice = self.env['account.move'].browse(res_ids)
            if invoice.is_sale_document() and invoice.state == 'posted':
                pdf_stream = collected_streams[invoice.id]['stream']
                invoice_data = {'pdf_attachment_values': {'raw': pdf_stream.getvalue()}}
                self.env['account.move.send'].with_context(custom_template_facturx=True)._hook_invoice_document_after_pdf_report_render(invoice, invoice_data)
                collected_streams[invoice.id]['stream'] = io.BytesIO(invoice_data['pdf_attachment_values']['raw'])
        return collected_streams
