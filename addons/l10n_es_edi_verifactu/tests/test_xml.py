from freezegun import freeze_time

from odoo import Command
from odoo.tests import tagged
from .common import TestEsEdiVerifactuCommon

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEsEdiVerifactuXml(TestEsEdiVerifactuCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_invoice_1(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2019-01-30',
            'date': '2019-01-30',
            'partner_id': self.partner_b.id,  # Spanish customer
            'invoice_line_ids': [
                # TODO: should goods and services be grouped together?
                Command.create({'product_id': self.product_1.id, 'price_unit': 100.0, 'tax_ids': [Command.set(self.tax21_goods.ids)]}),
                Command.create({'product_id': self.product_1.id, 'price_unit': 200.0, 'tax_ids': [Command.set(self.tax21_services.ids)]}),
                Command.create({'product_id': self.product_1.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(self.tax10_goods.ids)]}),
            ],
        })
        invoice.action_post()
        record_document = invoice._l10n_es_edi_verifactu_create_record_document()
        xml, errors = record_document._create_batch_xml()
        self._assert_verifactu_xml(xml, "l10n_es_edi_verifactu/tests/files/test_invoice_1.xml")

        # Test the credit note
        self.env['account.move.reversal'].with_company(self.company).create(
            {
                'move_ids': [Command.set((invoice.id,))],
                'date': '2019-02-10',
                'journal_id': invoice.journal_id.id,
            }
        ).reverse_moves()
        credit_note = invoice.reversal_move_id
        credit_note.invoice_date = '2019-02-11'
        credit_note.action_post()
        record_document = credit_note._l10n_es_edi_verifactu_create_record_document()
        xml, errors = record_document._create_batch_xml()
        self._assert_verifactu_xml(xml, "l10n_es_edi_verifactu/tests/files/test_invoice_1_credit_note.xml")

    def test_invoice_2(self):
        # Recargo de Equivalencia
        # FechaOperacion
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2019-01-30',
            'delivery_date': '2019-02-01',
            'date': '2019-01-30',
            'partner_id': self.partner_b.id,  # Spanish customer
            'invoice_line_ids': [
                Command.create({'product_id': self.product_1.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(self.tax21_services.ids)]}),
                Command.create({'product_id': self.product_1.id, 'price_unit': 100.0, 'tax_ids': [Command.set((self.tax10_goods + self.tax_s_req014).ids)]}),
                Command.create({'product_id': self.product_1.id, 'price_unit': 200.0, 'tax_ids': [Command.set((self.tax21_services + self.tax_s_req52).ids)]}),
            ],
        })
        invoice.action_post()
        record_document = invoice._l10n_es_edi_verifactu_create_record_document()
        xml, errors = record_document._create_batch_xml()
        self._assert_verifactu_xml(xml, "l10n_es_edi_verifactu/tests/files/test_invoice_2.xml")

    def test_invoice_multicurrency_1(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2019-01-30',
            'date': '2019-01-30',
            'currency_id': self.currency_data['currency'].id,
            'partner_id': self.partner_a.id,  # Belgian customer
            'invoice_line_ids': [
                Command.create({'product_id': self.product_1.id, 'price_unit': 100.0, 'tax_ids': [Command.set(self.tax21_goods.ids)]}),
                Command.create({'product_id': self.product_1.id, 'price_unit': 200.0, 'tax_ids': [Command.set(self.tax21_services.ids)]}),
                Command.create({'product_id': self.product_1.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(self.tax10_goods.ids)]}),
            ],
        })
        invoice.action_post()
        record_document = invoice._l10n_es_edi_verifactu_create_record_document()
        xml, errors = record_document._create_batch_xml()
        self._assert_verifactu_xml(xml, "l10n_es_edi_verifactu/tests/files/test_invoice_multi_currency_1.xml")

    def test_multiple_invoices_with_predecessor(self):
        invoices = self.env['account.move'].create([
            {
                'move_type': 'out_invoice',
                'invoice_date': '2019-02-01',
                'date': '2019-01-30',
                'partner_id': self.partner_b.id,  # Spanish customer
                'invoice_line_ids': [
                    Command.create({'product_id': self.product_1.id, 'price_unit': 100.0, 'tax_ids': [Command.set(self.tax21_goods.ids)]}),
                    Command.create({'product_id': self.product_1.id, 'price_unit': 200.0, 'tax_ids': [Command.set(self.tax21_services.ids)]}),
                    Command.create({'product_id': self.product_1.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(self.tax10_goods.ids)]}),
                ],
            },
            {
                'move_type': 'out_invoice',
                'invoice_date': '2019-02-02',
                'date': '2019-01-30',
                'partner_id': self.partner_b.id,  # Spanish customer
                'invoice_line_ids': [
                    Command.create({'product_id': self.product_1.id, 'price_unit': 100.0, 'tax_ids': [Command.set(self.tax21_goods.ids)]}),
                    Command.create({'product_id': self.product_1.id, 'price_unit': 200.0, 'tax_ids': [Command.set(self.tax21_services.ids)]}),
                    Command.create({'product_id': self.product_1.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(self.tax10_goods.ids)]}),
                ],
            },
            {
                'move_type': 'out_invoice',
                'invoice_date': '2019-02-03',
                'date': '2019-01-30',
                'partner_id': self.partner_b.id,  # Spanish customer
                'invoice_line_ids': [
                    Command.create({'product_id': self.product_1.id, 'price_unit': 100.0, 'tax_ids': [Command.set(self.tax21_goods.ids)]}),
                    Command.create({'product_id': self.product_1.id, 'price_unit': 200.0, 'tax_ids': [Command.set(self.tax21_services.ids)]}),
                    Command.create({'product_id': self.product_1.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(self.tax10_goods.ids)]}),
                ],
            },
        ])
        invoices.action_post()

        previous_record_identifier = {
            'IDEmisorFactura': '59962470K',
            'NumSerieFactura': 'INV/2018/00001',
            'FechaExpedicionFactura': '01-01-2018',
            'Huella': 'FA5DC48A0640BEB02A05160FD30020D1EA67FC1B400800ECDD9FC785E137C864',
        }

        record_document0 = invoices[0]._l10n_es_edi_verifactu_create_record_document(
            previous_record_identifier=previous_record_identifier,
        )
        record_document1 = invoices[1]._l10n_es_edi_verifactu_create_record_document(
            cancellation=True, previous_record_identifier=record_document0.record_identifier,
        )
        record_document2 = invoices[2]._l10n_es_edi_verifactu_create_record_document(
            previous_record_identifier=record_document1.record_identifier,
        )
        record_documents = self.env['l10n_es_edi_verifactu.record_document'].browse([
            record_document0.id, record_document1.id, record_document2.id,
        ])
        xml, errors = record_documents._create_batch_xml()
        self._assert_verifactu_xml(xml, "l10n_es_edi_verifactu/tests/files/test_multiple_invoices_with_predecessor.xml")

    def test_invoice_cancellation_1(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2019-01-30',
            'date': '2019-01-30',
            'partner_id': self.partner_b.id,  # Spanish customer
            'invoice_line_ids': [
                Command.create({'product_id': self.product_1.id, 'price_unit': 100.0, 'tax_ids': [Command.set(self.tax21_goods.ids)]}),
                Command.create({'product_id': self.product_1.id, 'price_unit': 200.0, 'tax_ids': [Command.set(self.tax21_services.ids)]}),
                Command.create({'product_id': self.product_1.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(self.tax10_goods.ids)]}),
            ],
        })
        invoice.action_post()
        record_document = invoice._l10n_es_edi_verifactu_create_record_document(cancellation=True)
        xml, errors = record_document._create_batch_xml()
        self._assert_verifactu_xml(xml, "l10n_es_edi_verifactu/tests/files/test_invoice_cancellation_1.xml")

    def test_invoice_simplified_partner(self):
        simplified_partner = self.env.ref('l10n_es.partner_simplified')
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2019-01-30',
            'date': '2019-01-30',
            'partner_id': simplified_partner.id,
            'invoice_line_ids': [
                Command.create({'product_id': self.product_1.id, 'price_unit': 100.0, 'tax_ids': [Command.set(self.tax21_goods.ids)]}),
            ],
        })
        invoice.action_post()
        record_document = invoice._l10n_es_edi_verifactu_create_record_document()
        xml, errors = record_document._create_batch_xml()
        self._assert_verifactu_xml(xml, "l10n_es_edi_verifactu/tests/files/test_invoice_simplified_partner.xml")
