# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.modules.module import get_module_resource
from odoo.addons.account.tests.common import AccountTestInvoicingCommon

from contextlib import contextmanager
from unittest.mock import patch

import base64


def _generate_mocked_needs_web_services(needs_web_services):
    return lambda edi_format: needs_web_services


def _mocked_get_move_applicability(edi_format, move):
    if move.is_invoice():
        return {
            'post': edi_format._post_invoice_edi,
            'cancel': edi_format._cancel_invoice_edi,
        }
    elif move.payment_id or move.statement_line_id:
        return {
            'post': edi_format._post_payment_edi,
            'cancel': edi_format._cancel_invoice_edi,
        }


def _mocked_check_move_configuration_success(edi_format, move):
    return []


def _mocked_check_move_configuration_fail(edi_format, move):
    return ['Fake error (mocked)']


def _mocked_cancel_success(edi_format, invoices):
    return {invoice: {'success': True} for invoice in invoices}


class AccountEdiTestCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None, edi_format_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # ==== EDI ====
        if edi_format_ref:
            cls.edi_format = cls.env.ref(edi_format_ref)
        else:
            with cls.mock_edi(cls, _needs_web_services_method=_generate_mocked_needs_web_services(True)):
                cls.edi_format = cls.env['account.edi.format'].sudo().create({
                    'name': 'Test EDI format',
                    'code': 'test_edi',
                })
        cls.journal = cls.company_data['default_journal_sale']
        cls.journal.edi_format_ids = [(6, 0, cls.edi_format.ids)]

    ####################################################
    # EDI helpers
    ####################################################

    def _create_fake_edi_attachment(self):
        return self.env['ir.attachment'].create({
            'name': '_create_fake_edi_attachment.xml',
            'datas': base64.encodebytes(b"<?xml version='1.0' encoding='UTF-8'?><Invoice/>"),
            'mimetype': 'application/xml'
        })

    @contextmanager
    def with_custom_method(self, method_name, method_content):
        path = f'odoo.addons.account_edi.models.account_edi_format.AccountEdiFormat.{method_name}'
        with patch(path, new=method_content, create=not hasattr(self.env['account.edi.format'], method_name)):
            yield

    @contextmanager
    def mock_edi(self,
                 _get_move_applicability_method=_mocked_get_move_applicability,
                 _needs_web_services_method=_generate_mocked_needs_web_services(False),
                 _check_move_configuration_method=_mocked_check_move_configuration_success,
                 ):

        try:
            with patch('odoo.addons.account_edi.models.account_edi_format.AccountEdiFormat._needs_web_services',
                       new=_needs_web_services_method), \
                 patch('odoo.addons.account_edi.models.account_edi_format.AccountEdiFormat._check_move_configuration',
                       new=_check_move_configuration_method), \
                 patch('odoo.addons.account_edi.models.account_edi_format.AccountEdiFormat._get_move_applicability',
                       new=_get_move_applicability_method):

                yield
        finally:
            pass

    def edi_cron(self):
        self.env['account.edi.document'].sudo().search([('state', 'in', ('to_send', 'to_cancel'))])._process_documents_web_services(with_commit=False)

    def create_invoice_from_file(self, module_name, subfolder, filename):
        file_path = get_module_resource(module_name, subfolder, filename)
        file = open(file_path, 'rb').read()

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': base64.encodebytes(file),
            'res_model': 'account.move',
        })
        journal_id = self.company_data['default_journal_sale']
        action_vals = journal_id.with_context(default_move_type='in_invoice').create_document_from_attachment(attachment.ids)
        return self.env['account.move'].browse(action_vals['res_id'])

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
        move = move or self.init_invoice(move_type or 'out_invoice', products=self.product_a)
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
        moves.edi_document_ids._process_documents_web_services(with_commit=False)

        documents_to_return = moves.edi_document_ids
        if formats_to_return != None:
            documents_to_return = documents_to_return.filtered(lambda x: x.edi_format_id.code in formats_to_return)

        attachments = documents_to_return.attachment_id
        data_str_list = []
        for attachment in attachments.with_context(bin_size=False):
            data_str_list.append(base64.decodebytes(attachment.datas))
        return data_str_list
