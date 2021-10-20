# -*- coding: utf-8 -*-
from io import BytesIO
from logging import getLogger
from PyPDF2 import PdfFileReader

from odoo import fields, models
from odoo import tools
from odoo.tools.pdf import OdooPdfFileWriter

_logger = getLogger(__name__)


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _post_pdf(self, save_in_attachment, pdf_content=None, res_ids=None):
        # OVERRIDE
        if self.model == 'account.move' and res_ids and len(res_ids) == 1:
            invoice = self.env['account.move'].browse(res_ids)
            if invoice.is_sale_document() and invoice.state != 'draft':
                xml_content = invoice._export_as_facturx_xml()

                reader_buffer = BytesIO(pdf_content)
                reader = PdfFileReader(reader_buffer)
                writer = OdooPdfFileWriter()
                writer.cloneReaderDocumentRoot(reader)

                if tools.str2bool(self.env['ir.config_parameter'].sudo().get_param('edi.use_pdfa', 'False')):
                    try:
                        writer.convert_to_pdfa()
                    except Exception as e:
                        _logger.exception("Error while converting to PDF/A: %s", e)

                    metadata_template = self.env.ref('account_facturx.account_invoice_pdfa_3_facturx_metadata', False)
                    if metadata_template:
                        metadata_content = metadata_template.render({
                            'title': invoice.name,
                            'date': fields.Date.context_today(self),
                        })
                        writer.add_file_metadata(metadata_content)

                writer.addAttachment('factur-x.xml', xml_content, '/application#2Fxml')

                buffer = BytesIO()
                writer.write(buffer)
                pdf_content = buffer.getvalue()
                buffer.close()
                reader_buffer.close()

        return super(IrActionsReport, self)._post_pdf(save_in_attachment, pdf_content=pdf_content, res_ids=res_ids)
