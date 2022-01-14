# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

from lxml import etree
import base64
from xml.sax.saxutils import escape, quoteattr


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _postprocess_pdf_report(self, record, buffer):
        '''Add the pdf report in the e-fff XML as base64 string.
        '''
        result = super()._postprocess_pdf_report(record, buffer)

        if record._name == 'account.move':
            edi_attachment = record.edi_document_ids.filtered(lambda d: d.edi_format_id.code == 'efff_1').attachment_id
            if edi_attachment:
                old_xml = base64.b64decode(edi_attachment.with_context(bin_size=False).datas, validate=True)
                tree = etree.fromstring(old_xml)
                anchor_elements = tree.xpath("//*[local-name()='AccountingSupplierParty']")
                additional_document_elements = tree.xpath("//*[local-name()='AdditionalDocumentReference']")
                if anchor_elements and not additional_document_elements:
                    pdf = base64.b64encode(buffer.getvalue()).decode()
                    pdf_name = '%s.pdf' % record._get_efff_name()
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
                    ''' % (escape(pdf_name), quoteattr(pdf_name), pdf)

                    anchor_index = tree.index(anchor_elements[0])
                    tree.insert(anchor_index, etree.fromstring(to_inject))
                    new_xml = etree.tostring(tree, pretty_print=True)
                    edi_attachment.write({
                        'res_model': 'account.move',
                        'res_id': record.id,
                        'datas': base64.b64encode(new_xml),
                        'mimetype': 'application/xml',
                    })

        return result
