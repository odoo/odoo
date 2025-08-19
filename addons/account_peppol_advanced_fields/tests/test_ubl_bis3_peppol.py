from odoo import Command
from odoo.tests import tagged

from odoo.addons.account_edi_ubl_cii.tests.test_ubl_bis3 import TestUblBis3


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUblBis3Peppol(TestUblBis3):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_module = 'account_peppol_advanced_fields'

    def test_export_invoice_with_peppol_fields(self):
        """ Test that all custom Peppol fields are correctly exported in a UBL invoice. """
        self.setup_partner_as_be1(self.env.company.partner_id)
        self.setup_partner_as_be2(self.partner_a)
        tax_21 = self.percent_tax(21.0)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax_21.ids)],
                }),
            ],
            'peppol_contract_document_reference': 'TEST-CONTRACT-001',
            'peppol_project_reference': 'PROJ-TEST-ABC',
            'peppol_originator_document_reference': 'PO-987654',
            'peppol_despatch_document_reference': 'DESP-12345',
            'peppol_additional_document_reference': 'ADD-DOC-A',
            'peppol_accounting_cost': 'COST-CENTER-001',
            'peppol_delivery_location_id': '9876543210987',
        })
        invoice.action_post()
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods=['manual'])
        self._assert_invoice_ubl_file(invoice, 'invoice')

    def test_export_credit_note_with_peppol_fields(self):
        """ Test that all custom Peppol fields are correctly exported in a UBL credit note. """
        self.setup_partner_as_be1(self.env.company.partner_id)
        self.setup_partner_as_be2(self.partner_a)
        tax_21 = self.percent_tax(21.0)

        credit_note = self.env['account.move'].create({
            'move_type': 'out_refund',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax_21.ids)],
                }),
            ],
            'peppol_contract_document_reference': 'TEST-CONTRACT-002',
            'peppol_originator_document_reference': 'PO-123456',
            'peppol_despatch_document_reference': 'DESP-67890',
            'peppol_additional_document_reference': 'ADD-DOC-B',
            'peppol_accounting_cost': 'COST-CENTER-002',
            'peppol_delivery_location_id': '1234567890123',
        })
        credit_note.action_post()
        self.env['account.move.send']._generate_and_send_invoices(credit_note, sending_methods=['manual'])
        self._assert_invoice_ubl_file(credit_note, 'credit_note')
