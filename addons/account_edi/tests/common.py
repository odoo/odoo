# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.modules.module import get_module_resource
from odoo.addons.account.tests.common import AccountTestInvoicingCommon

from contextlib import contextmanager
from unittest.mock import patch
from unittest import mock

import base64


class AccountEdiTestCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None, edi_format_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # ==== EDI ====
        if edi_format_ref:
            cls.edi_format = cls.env.ref(edi_format_ref)
        else:
            cls.edi_format = cls.env['account.edi.format'].sudo().create({
                'name': 'Test EDI format',
                'code': 'test_edi',
            })
        cls.journal = cls.company_data['default_journal_sale']
        cls.journal.edi_format_ids = [(6, 0, cls.edi_format.ids)]

    ####################################################
    # EDI helpers
    ####################################################

    def edi_cron(self):
        self.env['account.edi.document'].sudo().with_context(edi_test_mode=True).search([('state', 'in', ('to_send', 'to_cancel'))])._process_documents_web_services(with_commit=False)

    def _create_empty_vendor_bill(self):
        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'journal_id': self.company_data['default_journal_purchase'].id,
        })
        if 'extract_state' in invoice._fields:
            invoice.extract_state = 'done'  # prevent ocr
        return invoice

    def update_invoice_from_file(self, module_name, subfolder, filename, invoice):
        file_path = get_module_resource(module_name, subfolder, filename)
        file = open(file_path, 'rb').read()

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': base64.encodebytes(file),
            'res_id': invoice.id,
            'res_model': 'account.move',
        })

        invoice.message_post(attachment_ids=[attachment.id])

    def create_invoice_from_file(self, module_name, subfolder, filename):
        file_path = get_module_resource(module_name, 'test_file', filename)
        file = open(file_path, 'rb').read()

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': base64.encodebytes(file),
            'res_model': 'account.move',
        })

        journal_id = self.company_data['default_journal_sale']
        journal_id.with_context(default_move_type='in_invoice')._create_invoice_from_single_attachment(attachment)

    def assert_generated_file_equal(self, invoice, expected_values, applied_xpath=None):
        invoice.action_post()
        invoice.edi_document_ids._process_documents_web_services(with_commit=False)  # synchronous are called in post, but there's no CRON in tests for asynchronous
        attachment = invoice._get_edi_attachment(self.edi_format)
        if not attachment:
            raise ValueError('No attachment was generated after posting EDI')
        xml_content = base64.b64decode(attachment.with_context(bin_size=False).datas)
        current_etree = self.get_xml_tree_from_string(xml_content)
        expected_etree = self.get_xml_tree_from_string(expected_values)
        if applied_xpath:
            expected_etree = self.with_applied_xpath(expected_etree, applied_xpath)
        self.assertXmlTreeEqual(current_etree, expected_etree)

    def create_edi_document(self, edi_format, state, move=None, move_type=None):
        """ Creates a document based on an existing invoice or creates one, too.

        :param edi_format:  The edi_format of the document.
        :param state:       The state of the document.
        :param move:        The move of the document or None to create a new one.
        :param move_type:   If move is None, the type of the invoice to create, defaults to 'out_invoice'.
        """
        move = move or self.init_invoice(move_type or 'out_invoice')
        return self.env['account.edi.document'].create({
            'edi_format_id': edi_format.id,
            'move_id': move.id,
            'state': state
        })

    def _process_documents_web_services(self, moves, formats_to_return=None):
        """ Generates and returns EDI files for the specified moves.
        formats_to_return is an optional parameter used to pass a set of codes from
        the formats we want to return the files for (in case we want to test specific formats).
        Other formats will still generate documents, they simply won't be returned.
        """
        moves.edi_document_ids.with_context(edi_test_mode=True)._process_documents_web_services(with_commit=False)

        documents_to_return = moves.edi_document_ids
        if formats_to_return != None:
            documents_to_return = documents_to_return.filtered(lambda x: x.edi_format_id.code in formats_to_return)

        attachments = documents_to_return.attachment_id
        data_str_list = []
        for attachment in attachments.with_context(bin_size=False):
            data_str_list.append(base64.decodebytes(attachment.datas))
        return data_str_list
