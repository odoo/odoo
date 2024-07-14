# -*- coding: utf-8 -*-
from unittest.mock import patch, MagicMock

import os

from lxml import etree

from odoo import fields
from odoo.tests import Form, tagged
from odoo.tools import misc
from .common import TestL10nClEdiCommon, _check_with_xsd_patch


@tagged('post_install_l10n', 'post_install', '-at_install')
@patch('odoo.tools.xml_utils._check_with_xsd', _check_with_xsd_patch)
class TestFetchmailServer(TestL10nClEdiCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref='cl'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        purchase_journal = cls.env['account.journal'].search([
            ('type', '=', 'purchase'),
            ('company_id', '=', cls.company_data['company'].id)
        ], limit=1)
        purchase_journal.write({'l10n_latam_use_documents': True})
        sale_journal = cls.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', cls.company_data['company'].id)
        ], limit=1)
        sale_journal.write({'l10n_cl_point_of_sale_type': 'online', 'l10n_latam_use_documents': True})

    def test_get_dte_recipient_company_incoming_supplier_document(self):
        incoming_supplier_dte = misc.file_open(os.path.join(
            'l10n_cl_edi', 'tests', 'fetchmail_dtes', 'incoming_supplier_dte.xml')).read()
        xml_content = etree.fromstring(incoming_supplier_dte)
        self.assertEqual(
            self.env['fetchmail.server']._get_dte_recipient_company(xml_content, 'incoming_supplier_document'),
            self.company_data['company']
        )

    def test_get_dte_recipient_company_incoming_sii_dte_result(self):
        incoming_sii_dte_result = misc.file_open(os.path.join(
            'l10n_cl_edi', 'tests', 'fetchmail_dtes', 'incoming_sii_dte_result.xml')).read()
        xml_content = etree.fromstring(incoming_sii_dte_result)
        self.assertEqual(
            self.env['fetchmail.server']._get_dte_recipient_company(xml_content, 'incoming_sii_dte_result'),
            self.company_data['company']
        )

    def test_get_dte_recipient_company_incoming_acknowledge(self):
        incoming_acknowledge = misc.file_open(os.path.join(
            'l10n_cl_edi', 'tests', 'fetchmail_dtes', 'incoming_acknowledge.xml')).read()
        xml_content = etree.fromstring(incoming_acknowledge)
        self.assertEqual(
            self.env['fetchmail.server']._get_dte_recipient_company(xml_content, 'incoming_acknowledge'),
            self.company_data['company']
        )

    def test_get_dte_recipient_company_incoming_commercial_accept(self):
        incoming_commercial_accept = misc.file_open(os.path.join(
            'l10n_cl_edi', 'tests', 'fetchmail_dtes', 'incoming_commercial_accept.xml')).read()
        xml_content = etree.fromstring(incoming_commercial_accept)
        self.assertEqual(
            self.env['fetchmail.server']._get_dte_recipient_company(xml_content, 'incoming_commercial_accept'),
            self.company_data['company']
        )

    def test_get_dte_recipient_company_incoming_commercial_reject(self):
        incoming_commercial_reject = misc.file_open(os.path.join(
            'l10n_cl_edi', 'tests', 'fetchmail_dtes', 'incoming_commercial_reject.xml')).read()
        xml_content = etree.fromstring(incoming_commercial_reject)
        self.assertEqual(
            self.env['fetchmail.server']._get_dte_recipient_company(xml_content, 'incoming_commercial_reject'),
            self.company_data['company']
        )

    @patch('odoo.fields.Date.context_today', return_value=fields.Date.from_string('2019-11-23'))
    def test_create_invoice_33_from_attachment(self, context_today):
        """DTE with unknown partner but known products"""
        att_name = 'incoming_invoice_33.xml'
        from_address = 'incoming_dte@test.com'
        att_content = misc.file_open(os.path.join('l10n_cl_edi', 'tests', 'fetchmail_dtes', att_name)).read()
        moves = self.env['fetchmail.server']._create_document_from_attachment(
            att_content, att_name, from_address, self.company_data['company'].id)

        self.assertEqual(len(moves), 1)

        move = moves[0]
        self.assertEqual(move.name, 'FAC 000001')
        self.assertEqual(move.partner_id, self.env['res.partner'])
        self.assertEqual(move.date, fields.Date.from_string('2019-11-23'))
        self.assertEqual(move.invoice_date, fields.Date.from_string('2019-10-23'))
        self.assertEqual(move.invoice_date_due, fields.Date.from_string('2019-10-23'))
        self.assertEqual(move.journal_id.type, 'purchase')
        self.assertEqual(move.l10n_latam_document_number, '000001')
        self.assertEqual(move.l10n_cl_dte_acceptation_status, 'received')
        self.assertEqual(move.invoice_source_email, from_address)
        self.assertEqual(move.l10n_latam_document_type_id.code, '33')
        self.assertEqual(move.company_id, self.company_data['company'])
        self.assertEqual(len(move.invoice_line_ids), 2)
        self.assertEqual(move.currency_id.name, 'CLP')
        self.assertEqual(move.amount_total, 351390)
        self.assertEqual(move.amount_tax, 56104)

    # Patch out the VAT check since the VAT number from the sender is invalid
    @patch('odoo.addons.base_vat.models.res_partner.ResPartner.check_vat', MagicMock())
    def test_create_invoice_33_from_attachment_with_sending_partner_defined_on_other_company(self):
        """DTE with unknown partner for the receiving company, but known partner for
        another company. Make sure we don't match with a partner the company associated
        with the invoice can't access.
        """

        self.env['res.partner'].create({
            'name': 'Other Partner SII Other Company',
            'is_company': 1,
            # Different company from the receiver on the XML (which is self.company_data['company'])
            'company_id': self.company_data_2['company'].id,
            # Same VAT as in the invoice XML
            'vat': '76086428-1',
        })

        att_name = 'incoming_invoice_33.xml'
        from_address = 'incoming_dte@test.com'
        att_content = misc.file_open('l10n_cl_edi/tests/fetchmail_dtes/{}'.format(att_name)).read()

        # Sudo to run like when OdooBot does the fetching. If we use a normal user,
        # `_get_invoice_form` will override `allowed_company_ids` in the context,
        # overriding anything we might set here. We want the user to be able to
        # access both company 1 (which is associated with the invoice) and company 2
        # (which is associated with the partner we just created) to trigger the
        # issue
        moves = self.env['fetchmail.server'].sudo()._create_document_from_attachment(
            att_content, att_name, from_address, self.company_data['company'].id)

        self.assertEqual(len(moves), 1)
        move = moves[0]
        # There's no valid partner, so it should be undefined.
        self.assertEqual(move.partner_id, self.env['res.partner'])
        self.assertEqual(move.company_id, self.company_data['company'])

    # Patch out the VAT check since the VAT number from the sender is invalid
    @patch('odoo.addons.base_vat.models.res_partner.ResPartner.check_vat', MagicMock())
    def test_create_invoice_33_from_attachment_with_sending_partner_defined_on_two_companies(self):
        """DTE with known partner for the receiving company and another company.
        Make sure the one from the receiving company gets picked, because otherwise
        there will be an access rights issue where the user accessing the invoice won't
        be able to access the partner.
        """

        self.env['res.partner'].create({
            'name': 'Other Partner SII Other Company',
            'is_company': 1,
            # Different company from the receiver on the XML (which is self.company_data['company'])
            'company_id': self.company_data_2['company'].id,
            # Same VAT as in the invoice XML
            'vat': '76086428-1',
        })

        partner_sii_same_company = self.env['res.partner'].create({
            'name': 'Other Partner SII Same Company',
            'is_company': 1,
            # Same company as the receiver on the XML
            'company_id': self.company_data['company'].id,
            # Same VAT as in the invoice XML
            'vat': '76086428-1',
        })

        att_name = 'incoming_invoice_33.xml'
        from_address = 'incoming_dte@test.com'
        att_content = misc.file_open('l10n_cl_edi/tests/fetchmail_dtes/{}'.format(att_name)).read()

        # Sudo to run like when OdooBot does the fetching. If we use a normal user,
        # `_get_invoice_form` will override `allowed_company_ids` in the context,
        # overriding anything we might set here. We want the user to be able to
        # access both company 1 (which is associated with the invoice and
        # one of the partners we created) and company 2 (which is associated with
        # the other partner we created) to trigger the issue
        moves = self.env['fetchmail.server'].sudo()._create_document_from_attachment(
            att_content, att_name, from_address, self.company_data['company'].id)

        self.assertEqual(len(moves), 1)
        move = moves[0]
        self.assertEqual(move.partner_id, partner_sii_same_company)
        self.assertEqual(move.company_id, self.company_data['company'])

    def test_create_invoice_34_from_attachment(self):
        """Include Invoice Reference"""
        att_name = 'incoming_invoice_34.xml'
        from_address = 'incoming_dte@test.com'
        att_content = misc.file_open(os.path.join('l10n_cl_edi', 'tests', 'fetchmail_dtes', att_name)).read()
        moves = self.env['fetchmail.server']._create_document_from_attachment(
            att_content, att_name, from_address, self.company_data['company'].id)

        self.assertEqual(len(moves), 1)

        move = moves[0]
        self.assertEqual(move.name, 'FNA 000100')
        self.assertEqual(move.partner_id, self.partner_sii)
        self.assertEqual(move.journal_id.type, 'purchase')
        self.assertEqual(move.l10n_latam_document_number, '000100')
        self.assertEqual(move.l10n_cl_dte_acceptation_status, 'received')
        self.assertEqual(move.invoice_source_email, from_address)
        self.assertEqual(move.l10n_latam_document_type_id.code, '34')
        self.assertEqual(move.company_id, self.company_data['company'])
        self.assertEqual(len(move.invoice_line_ids), 2)
        self.assertEqual(move.currency_id.name, 'CLP')
        self.assertEqual(move.amount_total, 295286)
        self.assertEqual(move.amount_tax, 0)
        self.assertEqual(len(move.l10n_cl_reference_ids), 2)
        self.assertEqual(move.l10n_cl_reference_ids.mapped('origin_doc_number'), ['996327', 'A349010'])
        self.assertIn(
            '52', ' '.join(move.l10n_cl_reference_ids.l10n_cl_reference_doc_type_id.mapped('code')),
            'The reference code 52 is not present.')
        self.assertEqual(move.l10n_cl_reference_ids.mapped('reason'), ['Test', 'HHA: Test Hoja de horas hombre'])

    def test_create_invoice_33_with_holding_taxes_from_attachment(self):
        """Include Invoice Reference"""
        att_name = 'incoming_invoice_33_with_holding_taxes.xml'
        from_address = 'incoming_dte@test.com'
        att_content = misc.file_open(os.path.join('l10n_cl_edi', 'tests', 'fetchmail_dtes', att_name)).read()
        moves = self.env['fetchmail.server']._create_document_from_attachment(
            att_content, att_name, from_address, self.company_data['company'].id)

        self.assertEqual(len(moves), 1)

        move = moves[0]
        self.assertEqual(move.name, 'FAC 000001')
        self.assertEqual(move.partner_id, self.partner_sii)
        self.assertEqual(move.journal_id.type, 'purchase')
        self.assertEqual(move.l10n_latam_document_number, '000001')
        self.assertEqual(move.l10n_cl_dte_acceptation_status, 'received')
        self.assertEqual(move.invoice_source_email, from_address)
        self.assertEqual(move.l10n_latam_document_type_id.code, '33')
        self.assertEqual(move.company_id, self.company_data['company'])
        self.assertEqual(len(move.invoice_line_ids), 7)
        self.assertEqual(move.currency_id.name, 'CLP')
        self.assertEqual(move.amount_total, 231119)
        self.assertEqual(move.amount_tax, 63670)
        self.assertEqual(len(move.l10n_cl_reference_ids), 0)

    def test_create_invoice_34_unknown_product_from_attachment(self):
        att_name = 'incoming_invoice_34_unknown_product.xml'
        from_address = 'incoming_dte@test.com'
        att_content = misc.file_open(os.path.join('l10n_cl_edi', 'tests', 'fetchmail_dtes', att_name)).read()
        moves = self.env['fetchmail.server']._create_document_from_attachment(
            att_content, att_name, from_address, self.company_data['company'].id)

        self.assertEqual(len(moves), 1)

        move = moves[0]
        self.assertEqual(move.name, 'FNA 000100')
        self.assertEqual(move.partner_id, self.partner_sii)
        self.assertEqual(move.journal_id.type, 'purchase')
        self.assertEqual(move.l10n_latam_document_number, '000100')
        self.assertEqual(move.l10n_cl_dte_acceptation_status, 'received')
        self.assertEqual(move.invoice_source_email, from_address)
        self.assertEqual(move.l10n_latam_document_type_id.code, '34')
        self.assertEqual(move.company_id, self.company_data['company'])
        self.assertEqual(move.currency_id.name, 'CLP')
        self.assertEqual(move.amount_total, 329800)
        self.assertEqual(move.amount_tax, 0)
        self.assertEqual(len(move.invoice_line_ids), 1)
        self.assertEqual(move.invoice_line_ids.product_id, self.env['product.product'])
        self.assertEqual(move.invoice_line_ids.name, 'Unknown Product')
        self.assertEqual(move.invoice_line_ids.price_unit, 32980.0)

    @patch('odoo.addons.l10n_cl_edi.models.fetchmail_server.FetchmailServer._get_dte_lines')
    def test_create_invoice_33_from_attachment_get_lines_exception(self, get_dte_lines):
        get_dte_lines.return_value = Exception

        att_name = 'incoming_invoice_33.xml'
        from_address = 'incoming_dte@test.com'
        att_content = misc.file_open(os.path.join('l10n_cl_edi', 'tests', 'fetchmail_dtes', att_name)).read()
        moves = self.env['fetchmail.server']._create_document_from_attachment(
            att_content, att_name, from_address, self.company_data['company'].id)

        self.assertEqual(len(moves), 1)

        move = moves[0]
        self.assertEqual(move.name, 'FAC 000001')
        self.assertEqual(move.partner_id, self.env['res.partner'])
        self.assertEqual(move.journal_id.type, 'purchase')
        self.assertEqual(move.l10n_latam_document_number, '000001')
        self.assertEqual(move.l10n_latam_document_type_id.code, '33')
        self.assertEqual(move.l10n_cl_dte_acceptation_status, 'received')
        self.assertEqual(move.company_id, self.company_data['company'])
        self.assertEqual(move.currency_id.name, 'CLP')

    def test_process_incoming_customer_claim_move_not_found(self):
        att_name = 'incoming_acknowledge.xml'
        att_content = misc.file_open(os.path.join('l10n_cl_edi', 'tests', 'fetchmail_dtes', att_name)).read()
        l10n_latam_document_type = self.env['l10n_latam.document.type'].search([
            ('code', '=', '34'),
            ('country_id.code', '=', 'CL')
        ])
        with patch('logging.Logger.warning') as logger:
            self.env['fetchmail.server']._process_incoming_customer_claim(
                self.company_data['company'].id, att_content, att_name, origin_type='incoming_acknowledge')
            logger.assert_called_with(
                'Move not found with partner: %s, document_number: %s, l10n_latam_document_type: %s, company_id: %s',
                    self.partner_sii.id, '254', l10n_latam_document_type.id, self.company_data['company'].id)

    def test_process_incoming_customer_claim_acknowledge(self):
        l10n_latam_document_type = self.env['l10n_latam.document.type'].search([
            ('code', '=', '34'),
            ('country_id.code', '=', 'CL')
        ])
        with Form(self.env['account.move'].with_context(default_move_type='out_invoice')) as invoice_form:
            invoice_form.partner_id = self.partner_sii
            invoice_form.l10n_latam_document_number = '00254'
            invoice_form.l10n_latam_document_type_id = l10n_latam_document_type
            with invoice_form.invoice_line_ids.new() as invoice_line_form:
                invoice_line_form.product_id = self.product_a
                invoice_line_form.quantity = 1
                invoice_line_form.price_unit = 79
                invoice_line_form.tax_ids.clear()

        move = invoice_form.save()
        move.l10n_cl_dte_status = 'accepted'
        # Since the new creation of the account move name, the name must by force to avoid errors
        move.name = 'FNA 000254'

        att_name = 'incoming_acknowledge.xml'
        att_content = misc.file_open(os.path.join('l10n_cl_edi', 'tests', 'fetchmail_dtes', att_name)).read()

        self.env['fetchmail.server']._process_incoming_customer_claim(
            self.company_data['company'].id, att_content, att_name, origin_type='incoming_acknowledge')

        self.assertEqual(move.l10n_cl_dte_acceptation_status, 'received')

    @patch('odoo.addons.l10n_cl_edi.models.l10n_cl_edi_util.L10nClEdiUtilMixin._get_cl_current_strftime')
    def test_process_incoming_customer_claim_accepted(self, get_cl_current_strftime):
        get_cl_current_strftime.return_value = '2019-10-24T20:00:00'
        l10n_latam_document_type = self.env['l10n_latam.document.type'].search([
            ('code', '=', '33'),
            ('country_id.code', '=', 'CL')
        ])
        with Form(self.env['account.move'].with_context(default_move_type='out_invoice')) as invoice_form:
            invoice_form.partner_id = self.partner_sii
            invoice_form.l10n_latam_document_number = '0301'
            invoice_form.l10n_latam_document_type_id = l10n_latam_document_type
            invoice_form.invoice_date = '2019-10-23'
            with invoice_form.invoice_line_ids.new() as invoice_line_form:
                invoice_line_form.product_id = self.product_a
                invoice_line_form.quantity = 1
                invoice_line_form.price_unit = 518732.7731

        move = invoice_form.save()
        # Since the new creation of the account move name, the name must by force to avoid errors
        move.name = 'FAC 000301'
        move.with_context(skip_xsd=True)._post(soft=False)
        move.l10n_cl_dte_status = 'accepted'

        att_name = 'incoming_commercial_accept.xml'
        att_content = misc.file_open(os.path.join('l10n_cl_edi', 'tests', 'fetchmail_dtes', att_name)).read()

        self.env['fetchmail.server']._process_incoming_customer_claim(
            self.company_data['company'].id, att_content, att_name, origin_type='incoming_commercial_accept')

        self.assertEqual(move.l10n_cl_dte_acceptation_status, 'accepted')

    @patch('odoo.addons.l10n_cl_edi.models.l10n_cl_edi_util.L10nClEdiUtilMixin._get_cl_current_strftime')
    def test_process_incoming_customer_claim_rejected(self, get_cl_current_strftime):
        get_cl_current_strftime.return_value = '2019-10-24T20:00:00'
        l10n_latam_document_type = self.env['l10n_latam.document.type'].search([
            ('code', '=', '34'),
            ('country_id.code', '=', 'CL')
        ])
        with Form(self.env['account.move'].with_context(default_move_type='out_invoice')) as invoice_form:
            invoice_form.partner_id = self.partner_sii
            invoice_form.l10n_latam_document_number = '254'
            invoice_form.l10n_latam_document_type_id = l10n_latam_document_type
            invoice_form.invoice_date = '2019-10-23'
            with invoice_form.invoice_line_ids.new() as invoice_line_form:
                invoice_line_form.product_id = self.product_a
                invoice_line_form.quantity = 1
                invoice_line_form.price_unit = 2398053.78
                invoice_line_form.tax_ids.clear() # there shouldn't be any taxes applied for document type 34

        move = invoice_form.save()
        # Since the new creation of the account move name, the name must by force to avoid errors
        move.name = 'FNA 000254'
        move.with_context(skip_xsd=True)._post(soft=False)
        move.l10n_cl_dte_status = 'accepted'

        att_name = 'incoming_commercial_reject.xml'
        att_content = misc.file_open(os.path.join('l10n_cl_edi', 'tests', 'fetchmail_dtes', att_name)).read()

        self.env['fetchmail.server']._process_incoming_customer_claim(
            self.company_data['company'].id, att_content, att_name, origin_type='incoming_commercial_reject')

        self.assertEqual(move.l10n_cl_dte_acceptation_status, 'claimed')
