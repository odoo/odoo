# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import cleanup_xml_node

from lxml import etree
import base64
from xml.sax.saxutils import escape, quoteattr


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _add_pdf_into_invoice_xml(self, invoice, stream_data):
        for edi_attachment in invoice.edi_document_ids.attachment_id:
            old_xml = base64.b64decode(edi_attachment.with_context(bin_size=False).datas, validate=True)
            tree = etree.fromstring(old_xml)
            anchor_elements = tree.xpath("//*[local-name()='AccountingSupplierParty']")
            additional_document_elements = tree.xpath("//*[local-name()='AdditionalDocumentReference']")
            # with this clause, we ensure the xml are only postprocessed once (even when the invoice is reset to
            # draft then validated again)
            if anchor_elements and not additional_document_elements:
                pdf_stream = stream_data['stream']
                pdf_content_b64 = base64.b64encode(pdf_stream.getvalue()).decode()
                pdf_name = '%s.pdf' % invoice.name.replace('/', '_')
                to_inject = '''
                    <cac:AdditionalDocumentReference
                        xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
                        xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
                        xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
                        <cbc:ID>%s</cbc:ID>
                        <cac:Attachment>
                            <cbc:EmbeddedDocumentBinaryObject mimeCode="application/pdf" filename=%s>
                                %s
                            </cbc:EmbeddedDocumentBinaryObject>
                        </cac:Attachment>
                    </cac:AdditionalDocumentReference>
                ''' % (escape(pdf_name), quoteattr(pdf_name), pdf_content_b64)

                anchor_index = tree.index(anchor_elements[0])
                tree.insert(anchor_index, etree.fromstring(to_inject))
                new_xml = etree.tostring(cleanup_xml_node(tree))
                edi_attachment.write({
                    'res_model': 'account.move',
                    'res_id': invoice.id,
                    'datas': base64.b64encode(new_xml),
                    'mimetype': 'application/xml',
                })

    def _render_qweb_pdf_prepare_streams(self, data, res_ids=None):
        # EXTENDS base
        # Add the pdf report in the XML as base64 string.
        collected_streams = super()._render_qweb_pdf_prepare_streams(data, res_ids=res_ids)

        if collected_streams \
                and res_ids \
                and self.report_name in ('account.report_invoice_with_payments', 'account.report_invoice'):
            for res_id, stream_data in collected_streams.items():
                invoice = self.env['account.move'].browse(res_id)
                self._add_pdf_into_invoice_xml(invoice, stream_data)

        return collected_streams
