# -*- coding: utf-8 -*-
from odoo import tools
from odoo.tests import common

import logging
import base64

from lxml import etree

_logger = logging.getLogger(__name__)

UBL_NAMESPACES = {
    'cac': '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}',
    'cbc': '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}',
}

class TestUBL(common.TransactionCase):
    def test_ubl_invoice(self):
        Invoice = self.env['account.invoice']
        invoices_ids = Invoice.search([])
        for invoice in invoices_ids:
            if invoice.sent:
                country_code = invoice.company_id.country_id.code
                if country_code == 'MX':
                    attachment_ids = invoice._get_edi_attachments()
                    filenames = invoice.get_edi_filenames_MX()
                    for attachment_id in attachment_ids:
                        if attachment_id.name in filenames:
                            xml_schema_doc = etree.parse(tools.file_open(
                                'account_ubl/data/xsd/2.1/maindoc/UBL-Invoice-2.1.xsd'))
                            xsd_schema = etree.XMLSchema(xml_schema_doc)
                            tree = tools.str_as_tree(base64.decodestring(attachment_id.datas))
                            try:
                                xsd_schema.assertValid(tree)
                            except etree.DocumentInvalid, xml_errors:
                                error_pattern = 'The generate file %s is unvalid:\n%s'
                                error = reduce(lambda x, y: x + y, map(lambda z: z.message + '\n', xml_errors.error_log))
                                raise ValidationError(_(error_pattern % (attachment_id.name, error)))
                            # Further check for e-fff specific documents
                            if country_code == 'BE':
                                line_count_element = tree.find(
                                    './/' + UBL_NAMESPACES['cbc'] + 'LineCountNumeric')
                                doc_ref_element = tree.find(
                                    './/' + UBL_NAMESPACES['cac'] + 'AdditionalDocumentReference')
                                binary_element = tree.find(
                                    './/' + UBL_NAMESPACES['cbc'] + 'EmbeddedDocumentBinaryObject')
                                assert line_count_element is not None, \
                                    'cbc:LineCountNumeric not found for e-fff'
                                assert doc_ref_element is not None, \
                                    'cac:AdditionalDocumentReference not found for e-fff'
                                assert binary_element is not None, \
                                    'cbc:EmbeddedDocumentBinaryObject not found for e-fff'
                            _logger.info('File %s for invoice %s is valid' % (attachment_id.name, invoice.number))

