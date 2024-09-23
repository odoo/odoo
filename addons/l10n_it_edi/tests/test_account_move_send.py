# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from odoo.tests import tagged
from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.addons.l10n_it_edi.tests.common import TestItEdi

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItAccountMoveSend(TestItEdi, TestAccountMoveSendCommon):

    def init_invoice(self, partners):
        invoices = self.env['account.move']
        for partner in partners:
            invoices |= super().init_invoice(
                "out_invoice",
                partner=partner,
                company=self.company,
                amounts=[1000],
                taxes=self.default_tax,
                post=True)
        return invoices

    def get_attachments(self, res_id):
        return self.env['ir.attachment'].with_company(self.company).search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', res_id),
            ('res_field', 'in', ('invoice_pdf_report_file', 'l10n_it_edi_attachment_file')),
        ])

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
        self.assertFalse(invoice1.l10n_it_edi_attachment_id)
        self.assertFalse(invoice1.is_being_sent)
        self.assertEqual(1, len(self.get_attachments(invoice2.id)))
        self.assertTrue(invoice2.invoice_pdf_report_id)
        self.assertFalse(invoice2.l10n_it_edi_attachment_id)
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
            self.env['account.move.send']._generate_and_send_invoices(invoice1 + invoice2)

        # Asserts
        self.assertEqual((invoice1 + invoice2).mapped('sending_data'), [False, False])
        self.assertEqual(2, len(self.get_attachments(invoice1.id)))
        self.assertTrue(invoice1.invoice_pdf_report_id)
        self.assertTrue(invoice1.l10n_it_edi_attachment_id)
        self.assertFalse(invoice1.is_being_sent)
        self.assertEqual(2, len(self.get_attachments(invoice2.id)))
        self.assertTrue(invoice2.invoice_pdf_report_id)
        self.assertTrue(invoice2.l10n_it_edi_attachment_id)
        self.assertFalse(invoice2.is_being_sent)
