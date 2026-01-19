# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from odoo.tests import tagged
from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.addons.l10n_it_edi.tests.common import TestItEdi


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItAccountMoveSend(TestItEdi, TestAccountMoveSendCommon):

    def init_invoice(self, partners, company=None, taxes=None):
        invoices = self.env['account.move']
        for partner in partners:
            invoices |= super().init_invoice(
                "out_invoice",
                partner=partner,
                company=company or self.company,
                amounts=[1000],
                taxes=taxes or self.default_tax,
                post=True)
        return invoices

    def get_attachments(self, res_id):
        return self.env['ir.attachment'].with_company(self.company).search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', res_id),
            ('res_field', 'in', ('invoice_pdf_report_file', 'l10n_it_edi_attachment_file')),
        ])

    def generate_l10n_it_edi_send_attachments(self, invoices, from_cron=False):
        moves_data = {invoice: self.env['account.move.send']._get_default_sending_settings(invoice, from_cron=from_cron) for invoice in invoices}
        with patch('odoo.addons.l10n_it_edi.models.account_move_send.AccountMoveSend._call_web_service_after_invoice_pdf_render'):
            self.env['account.move.send']._generate_invoice_documents(moves_data)

    def test_invoice_multi_without_l10n_it_edi_xml_export(self):
        # Prepare
        invoice1, invoice2 = self.init_invoice(self.italian_partner_a + self.italian_partner_a)
        (self.italian_partner_a + self.italian_partner_b).with_company(invoice1.company_id).invoice_edi_format = False

        def _get_default_extra_edis(self, move):
            # in batch sending we use default settings, which is to use italian gov edi, bypass it
            return {}

        with patch(
                'odoo.addons.account.models.account_move_send.AccountMoveSend._get_default_extra_edis',
                _get_default_extra_edis
        ):
            self.env['account.move.send']._generate_and_send_invoices(invoice1 + invoice2)

        # Asserts
        self.assertEqual((invoice1 + invoice2).mapped('sending_data'), [False, False])
        self.assertEqual(1, len(self.get_attachments(invoice1.id)))
        self.assertTrue(invoice1.invoice_pdf_report_id)
        self.assertFalse(invoice1.l10n_it_edi_attachment_file)
        self.assertFalse(invoice1.is_being_sent)
        self.assertEqual(1, len(self.get_attachments(invoice2.id)))
        self.assertTrue(invoice2.invoice_pdf_report_id)
        self.assertFalse(invoice2.l10n_it_edi_attachment_file)
        self.assertFalse(invoice2.is_being_sent)

    def test_invoice_multi_with_l10n_it_edi_xml_export(self):
        # Prepare
        invoice1, invoice2 = self.init_invoice(self.italian_partner_a + self.italian_partner_a)
        (self.italian_partner_a + self.italian_partner_b).with_company(invoice1.company_id).invoice_edi_format = 'it_edi_xml'

        def _get_default_extra_edis(self, move):
            # in batch sending we use default settings, which is to use italian gov edi, bypass it
            return {}

        with patch(
                'odoo.addons.account.models.account_move_send.AccountMoveSend._get_default_extra_edis',
                _get_default_extra_edis
        ):
            self.env['account.move.send']._generate_and_send_invoices(invoice1 + invoice2, sending_methods=['email'])

        # Asserts
        self.assertEqual((invoice1 + invoice2).mapped('sending_data'), [False, False])
        self.assertEqual(2, len(self.get_attachments(invoice1.id)))
        self.assertTrue(invoice1.invoice_pdf_report_id)
        self.assertTrue(invoice1.l10n_it_edi_attachment_file)
        self.assertFalse(invoice1.is_being_sent)
        self.assertEqual(2, len(self.get_attachments(invoice2.id)))
        self.assertTrue(invoice2.invoice_pdf_report_id)
        self.assertTrue(invoice2.l10n_it_edi_attachment_file)
        self.assertFalse(invoice2.is_being_sent)

    def test_invoice_with_cig_or_cup_or_both(self):
            
            self.italian_partner_a.write({'l10n_it_pa_index': '1234567'})
            
            invoice_valid = self.init_invoice(self.italian_partner_a)
            invoice_cig_only = self.init_invoice(self.italian_partner_a)
            invoice_cup_only = self.init_invoice(self.italian_partner_a)
            invoice_cig_cup = self.init_invoice(self.italian_partner_a)

            invoice_valid.write({
                'l10n_it_cig': '1234567',
                'l10n_it_cup': '7654321',
                'l10n_it_origin_document_type': 'purchase_order'
            }) 
            
            invoice_cig_only.write({
                'l10n_it_cig': '1234567',
                'l10n_it_cup': False,
                'l10n_it_origin_document_type': False
            }) 
            
            invoice_cup_only.write({
                'l10n_it_cig': False,
                'l10n_it_cup': '7654321',
                'l10n_it_origin_document_type': False
            })
            
            invoice_cig_cup.write({
                'l10n_it_cig': '1234567',
                'l10n_it_cup': '7654321',
                'l10n_it_origin_document_type': False
            }) 

            valid = invoice_valid._l10n_it_edi_base_export_check()
            cig = invoice_cig_only._l10n_it_edi_base_export_check()
            cup = invoice_cup_only._l10n_it_edi_base_export_check()
            cig_cup = invoice_cig_cup._l10n_it_edi_base_export_check()

            self.assertNotIn('move_missing_origin_document_field', valid)
            self.assertIn('move_missing_origin_document_field', cig)
            self.assertIn('move_missing_origin_document_field', cup)
            self.assertIn('move_missing_origin_document_field', cig_cup)

    def test_invoice_send_with_multiple_company(self):
        second_company = self.company_data['company']
        second_company.write({
            'vat': 'IT12345670017',
            'phone': '0266766700',
            'email': 'test@test.it',
            'street': '1234 Test Street',
            'zip': '12345',
            'city': 'Prova',
            'l10n_it_codice_fiscale': '12345670017',
            'l10n_it_tax_system': 'RF01'
        })

        second_proxy = self.env['account_edi_proxy_client.user'].create({
            'proxy_type': 'l10n_it_edi',
            'id_client': 'l10n_it_edi_test_second_company',
            'company_id': second_company.id,
            'edi_identification': 'l10n_it_edi_test_second_company',
            'private_key_id': self.private_key_id.id,
            'edi_mode': 'demo',
        })

        self.proxy_user.edi_mode = 'demo'

        invoice1 = self.init_invoice(self.italian_partner_a)
        invoice2 = self.init_invoice(
            self.italian_partner_a,
            second_company,
            self.company_data['default_tax_sale']
        )

        with patch('odoo.addons.l10n_it_edi.models.account_move.AccountMove._l10n_it_edi_upload_single', return_value={}, autospec=True) as mock_check:
            self.env['account.move.send'].with_context(allowed_company_ids=[second_company.id, self.company.id])._generate_and_send_invoices(invoice2 + invoice1, sending_methods=['email'])
            self.assertEqual(mock_check.call_count, 2)
            res_call_invoice1, res_call_invoice2 = mock_check.call_args_list
            res_invoice1, res_invoice2 = res_call_invoice2[0][0], res_call_invoice1[0][0]
            self.assertEqual(res_invoice1, invoice1)
            self.assertEqual(res_invoice2, invoice2)
            self.assertEqual(res_invoice1.company_id.l10n_it_edi_proxy_user_id, self.proxy_user)
            self.assertEqual(res_invoice2.company_id.l10n_it_edi_proxy_user_id, second_proxy)

    def test_l10n_it_edi_send_success(self):
        invoice = self.init_invoice(self.italian_partner_a)
        self.generate_l10n_it_edi_send_attachments(invoice)
        success = {'id_transaction': "SDI ID 1", 'signed': False, 'signed_data': False}
        with patch('odoo.addons.l10n_it_edi.models.account_move.AccountMove._l10n_it_edi_upload_single', return_value=success) as mock_check:
            attachments_vals = {invoice: {'name': invoice.l10n_it_edi_attachment_name, 'raw': invoice.l10n_it_edi_attachment_file}}
            results = invoice._l10n_it_edi_send(attachments_vals)

            self.assertEqual(mock_check.call_count, 1)
            self.assertEqual(results, {invoice.l10n_it_edi_attachment_name: success})
            self.assertEqual(invoice.l10n_it_edi_state, "processing")
            self.assertEqual(invoice.l10n_it_edi_transaction, success['id_transaction'])

    def test_l10n_it_edi_send_proxy_error(self):
        invoice = self.init_invoice(self.italian_partner_a)
        self.generate_l10n_it_edi_send_attachments(invoice)
        proxy_error = {'error': 'error_code', 'error_description': 'error_description'}
        with patch('odoo.addons.l10n_it_edi.models.account_move.AccountMove._l10n_it_edi_upload_single', return_value=proxy_error) as mock_check:
            attachments_vals = {invoice: {'name': invoice.l10n_it_edi_attachment_name, 'raw': invoice.l10n_it_edi_attachment_file}}
            results = invoice._l10n_it_edi_send(attachments_vals)
            proxy_error['error_message'] = invoice._l10n_it_edi_upload_error_message(proxy_error['error'], proxy_error['error_description'])

            self.assertEqual(mock_check.call_count, 1)
            self.assertEqual(results, {invoice.l10n_it_edi_attachment_name: proxy_error})
            self.assertFalse(invoice.l10n_it_edi_state)
            self.assertFalse(invoice.l10n_it_edi_transaction)

    def test_l10n_it_edi_send_proxy_exception(self):
        invoice = self.init_invoice(self.italian_partner_a)
        self.generate_l10n_it_edi_send_attachments(invoice)
        with patch('odoo.addons.l10n_it_edi.models.account_move.AccountMove._l10n_it_edi_upload_single', side_effect=AccountEdiProxyError('error_code', message='error_description')) as mock_check:
            attachments_vals = {invoice: {'name': invoice.l10n_it_edi_attachment_name, 'raw': invoice.l10n_it_edi_attachment_file}}
            results = invoice._l10n_it_edi_send(attachments_vals)

            self.assertEqual(mock_check.call_count, 1)
            self.assertIn('error_message', results[invoice.l10n_it_edi_attachment_name])
            self.assertFalse(invoice.l10n_it_edi_state)
            self.assertFalse(invoice.l10n_it_edi_transaction)

    def test_l10n_it_edi_send_from_cron(self):
        invoices = self.init_invoice(self.italian_partner_a) | self.init_invoice(self.italian_partner_a)
        invoices.sending_data = {'author_user_id': self.env.user.id, 'author_partner_id': self.env.user.partner_id.id}
        self.generate_l10n_it_edi_send_attachments(invoices, from_cron=True)

        success = {'id_transaction': "SDI ID 1", 'signed': False, 'signed_data': False}
        proxy_error = {'error': 'error_code', 'error_description': 'error_description'}

        def _l10n_it_edi_upload_single(record, file):
            return success if file['filename'] == 'file_1.xml' else proxy_error

        with patch('odoo.addons.l10n_it_edi.models.account_move.AccountMove._l10n_it_edi_upload_single', side_effect=_l10n_it_edi_upload_single, autospec=True) as mock_check:
            invoices[0].l10n_it_edi_attachment_name = 'file_1.xml'

            attachments_vals = {invoice: {'name': invoice.l10n_it_edi_attachment_name, 'raw': invoice.l10n_it_edi_attachment_file} for invoice in invoices}
            results = invoices._l10n_it_edi_send(attachments_vals)

            self.assertEqual(mock_check.call_count, 2)
            self.assertEqual(results, {
                invoices[0].l10n_it_edi_attachment_name: success,
                invoices[1].l10n_it_edi_attachment_name: proxy_error
            })

            self.assertEqual(invoices[0].l10n_it_edi_state, "processing")
            self.assertEqual(invoices[0].l10n_it_edi_transaction, success['id_transaction'])
            self.assertTrue(invoices[0].l10n_it_edi_header)

            self.assertFalse(invoices[1].l10n_it_edi_state)
            self.assertFalse(invoices[1].l10n_it_edi_transaction)
            self.assertTrue(invoices[1].l10n_it_edi_header)

    def test_enasarco_no_warnings(self):
        self.proxy_user.edi_mode = 'demo'
        ref = self.env['account.chart.template'].with_company(self.proxy_user.company_id).ref
        self.partner_a.write({
            "l10n_it_codice_fiscale": "PERTLELPALQZRTSN",
            'country_id': self.env.ref('base.it').id,
            'street': 'Test street',
            'city': 'Test town',
            'zip': '32121',
        })
        invoice = self.init_invoice(partners=self.partner_a, taxes=ref('22v') | ref('23vwo') | ref('enasarcov'))
        wizard = self.create_send_and_print(invoice, sending_methods=['l10n_it_edi'])
        non_info_alerts = {k: v for k, v in wizard.alerts.items() if v.get('level') != 'info'}
        self.assertFalse(non_info_alerts)

    def test_l10n_it_edi_foreign_currency(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.italian_partner_a.id,
            'company_id': self.company.id,
            'currency_id': self.env.ref('base.USD').id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Zero total line',
                'quantity': 1.0,
                'price_unit': 100.0,
                'discount': 100.0,
                'tax_ids': [(6, 0, self.default_tax.ids)],
            })],
        })
        invoice.action_post()
        self.generate_l10n_it_edi_send_attachments(invoice)
        self.assertTrue(invoice.l10n_it_edi_attachment_file)
