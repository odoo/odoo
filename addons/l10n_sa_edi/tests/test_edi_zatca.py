# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
from freezegun import freeze_time
import logging
from pytz import timezone

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import misc

from .common import TestSaEdiCommon

_logger = logging.getLogger(__name__)


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestEdiZatca(TestSaEdiCommon):
    # """Test ZATCA EDI compliance for Saudi Arabia."""

    def _test_document_generation(self, test_file_path, expected_xpath, freeze_time_at, additional_xpath='', document_type=False, move=False, move_data=False):
        """
        Common helper to test document generation against expected XML.
        """
        with freeze_time(freeze_time_at):
            # Load expected XML
            expected_xml = misc.file_open(test_file_path, 'rb').read()
            expected_tree = self.get_xml_tree_from_string(expected_xml)
            expected_tree = self.with_applied_xpath(expected_tree, expected_xpath)

            creation_handlers = {
                "invoice": self._create_invoice,
                "credit_note": self._create_credit_note,
                "debit_note": self._create_debit_note,
            }

            if additional_xpath:
                expected_tree = self.with_applied_xpath(expected_tree, additional_xpath)

            if move:
                final_move = move
            elif move_data and document_type in creation_handlers:
                final_move = creation_handlers[document_type](**move_data)
            else:
                raise ValidationError("Either move or document_type + move_data need to be given")

            # Generate ZATCA XML
            if final_move.state != 'posted':
                final_move.action_post()

            final_move._l10n_sa_generate_unsigned_data()
            generated_file = self.env['account.edi.format']._l10n_sa_generate_zatca_template(final_move)
            current_tree = self.get_xml_tree_from_string(generated_file)
            current_tree = self.with_applied_xpath(current_tree, self.remove_ubl_extensions_xpath)

            # Assert
            self.assertXmlTreeEqual(current_tree, expected_tree)

    def testCreditNoteSimplified(self):
        """Test simplified credit note generation."""
        move_data = {
            'name': 'INV/2023/00034',
            'invoice_date': '2023-03-10',
            'invoice_date_due': '2023-03-10',
            'partner_id': self.partner_sa_simplified,
            'invoice_line_ids': [{
                'product_id': self.product_burger.id,
                'price_unit': self.product_burger.standard_price,
                'quantity': 3,
                'tax_ids': self.tax_15.ids,
            }]
        }

        self._test_document_generation(
            document_type='credit_note',
            test_file_path='l10n_sa_edi/tests/compliance/simplified/credit.xml',
            expected_xpath=self.credit_note_applied_xpath,
            move_data=move_data,
            freeze_time_at=datetime(2023, 3, 10, 14, 59, 38, tzinfo=timezone('Etc/GMT-3'))
        )

    def testCreditNoteStandard(self):
        """Test standard credit note generation."""
        move_data = {
            'name': 'INV/2022/00014',
            'invoice_date': '2022-09-05',
            'invoice_date_due': '2022-09-22',
            'partner_id': self.partner_sa,
            'invoice_line_ids': [{
                'product_id': self.product_a.id,
                'price_unit': self.product_a.standard_price,
                'quantity': 1,
                'tax_ids': self.tax_15.ids,
            }]
        }

        additional_xpath = '''
            <xpath expr="(//*[local-name()='AdditionalDocumentReference']/*[local-name()='UUID'])[1]" position="replace">
                <UUID>___ignore___</UUID>
            </xpath>
        '''

        self._test_document_generation(
            document_type='credit_note',
            test_file_path='l10n_sa_edi/tests/compliance/standard/credit.xml',
            expected_xpath=self.credit_note_applied_xpath,
            move_data=move_data,
            freeze_time_at=datetime(2022, 9, 5, 9, 39, 15, tzinfo=timezone('Etc/GMT-3')),
            additional_xpath=additional_xpath
        )

    def testDebitNoteSimplified(self):
        """Test simplified debit note generation."""
        move_data = {
            'name': 'INV/2023/00034',
            'invoice_date': '2023-03-10',
            'invoice_date_due': '2023-03-10',
            'partner_id': self.partner_sa_simplified,
            'invoice_line_ids': [{
                'product_id': self.product_burger.id,
                'price_unit': self.product_burger.standard_price,
                'quantity': 2,
                'tax_ids': self.tax_15.ids,
            }]
        }

        self._test_document_generation(
            document_type='debit_note',
            test_file_path='l10n_sa_edi/tests/compliance/simplified/debit.xml',
            expected_xpath=self.debit_note_applied_xpath,
            move_data=move_data,
            freeze_time_at=datetime(2023, 3, 10, 15, 1, 46, tzinfo=timezone('Etc/GMT-3'))
        )

    def testDebitNoteStandard(self):
        """Test standard debit note generation."""
        move_data = {
            'name': 'INV/2022/00001',
            'invoice_date': '2022-09-05',
            'invoice_date_due': '2022-09-22',
            'partner_id': self.partner_sa,
            'invoice_line_ids': [{
                'product_id': self.product_b.id,
                'price_unit': self.product_b.standard_price,
                'quantity': 1,
                'tax_ids': self.tax_15.ids,
            }]
        }

        additional_xpath = '''
            <xpath expr="(//*[local-name()='AdditionalDocumentReference']/*[local-name()='UUID'])[1]" position="replace">
                <UUID>___ignore___</UUID>
            </xpath>
        '''

        self._test_document_generation(
            document_type='debit_note',
            test_file_path='l10n_sa_edi/tests/compliance/standard/debit.xml',
            expected_xpath=self.debit_note_applied_xpath,
            move_data=move_data,
            freeze_time_at=datetime(2022, 9, 5, 9, 45, 27, tzinfo=timezone('Etc/GMT-3')),
            additional_xpath=additional_xpath
        )

    def testInvoiceSimplified(self):
        """Test simplified invoice generation."""
        move_data = {
            'name': 'INV/2023/00034',
            'invoice_date': '2023-03-10',
            'invoice_date_due': '2023-03-10',
            'partner_id': self.partner_sa_simplified,
            'invoice_line_ids': [{
                'product_id': self.product_burger.id,
                'price_unit': self.product_burger.standard_price,
                'quantity': 3,
                'tax_ids': self.tax_15.ids,
            }]
        }

        self._test_document_generation(
            document_type='invoice',
            test_file_path='l10n_sa_edi/tests/compliance/simplified/invoice.xml',
            expected_xpath=self.invoice_applied_xpath,
            move_data=move_data,
            freeze_time_at=datetime(2023, 3, 10, 14, 56, 55, tzinfo=timezone('Etc/GMT-3'))
        )

    def testInvoiceStandard(self):
        """Test standard invoice generation."""
        move_data = {
            'name': 'INV/2022/00014',
            'invoice_date': '2022-09-05',
            'invoice_date_due': '2022-09-22',
            'partner_id': self.partner_sa,
            'invoice_line_ids': [{
                'product_id': self.product_a.id,
                'price_unit': self.product_a.standard_price,
                'quantity': 1,
                'tax_ids': self.tax_15.ids,
            }]
        }

        self._test_document_generation(
            document_type='invoice',
            test_file_path='l10n_sa_edi/tests/compliance/standard/invoice.xml',
            expected_xpath=self.invoice_applied_xpath,
            move_data=move_data,
            freeze_time_at=datetime(2022, 9, 5, 8, 20, 2, tzinfo=timezone('Etc/GMT-3'))
        )

    def testInvoiceWithDownpayment(self):
        """Test invoice generation with downpayment scenarios."""
        if 'sale' not in self.env["ir.module.module"]._installed():
            self.skipTest("Sale module is not installed")

        freeze = datetime(2022, 9, 5, 8, 20, 2, tzinfo=timezone('Etc/GMT-3'))

        # Helper to test generated files
        saudi_pricelist = self.env['product.pricelist'].create({
            'name': 'SAR',
            'currency_id': self.env.ref('base.SAR').id
        })
        with freeze_time(freeze):
            sale_order = self.env['sale.order'].create({
                'partner_id': self.partner_sa.id,
                'pricelist_id': saudi_pricelist.id,
                'order_line': [
                    Command.create({
                        'product_id': self.product_a.id,
                        'price_unit': 1000,
                        'product_uom_qty': 1,
                        'tax_id': [Command.set(self.tax_15.ids)],
                    })
                ]
            })
            sale_order.action_confirm()

            # Context for wizards
            context = {
                'active_model': 'sale.order',
                'active_ids': [sale_order.id],
                'active_id': sale_order.id,
                'default_journal_id': self.customer_invoice_journal.id,
            }

            # Create downpayment invoice
            downpayment_wizard = self.env['sale.advance.payment.inv'].with_context(context).create({
                'advance_payment_method': 'fixed',
                'fixed_amount': 115,
                'deposit_taxes_id': [Command.set(self.tax_15.ids)],
            })
            downpayment = downpayment_wizard._create_invoices(sale_order)
            downpayment.invoice_date_due = '2022-09-22'

            # Create final invoice
            final_wizard = self.env['sale.advance.payment.inv'].with_context(context).create({})
            final = final_wizard._create_invoices(sale_order)
            final.invoice_date_due = '2022-09-22'

        # Test invoices
        for move, test_file in [
            (downpayment, "downpayment_invoice"),
            (final, "final_invoice")
        ]:
            with self.subTest(move=move, test_file=test_file):
                self._test_document_generation(
                    test_file_path=f'l10n_sa_edi/tests/test_files/{test_file}.xml',
                    expected_xpath=self.invoice_applied_xpath,
                    freeze_time_at=freeze,
                    move=move,
                )

        # Test credit notes
        for move, test_file in [
            (downpayment, "downpayment_credit_note"),
            (final, "final_credit_note")
        ]:
            with self.subTest(move=move, test_file=test_file):
                # Create refund
                wiz_context = {
                    'active_model': 'account.move',
                    'active_ids': [move.id],
                    'default_journal_id': move.journal_id.id,
                }
                refund_wizard = self.env['account.move.reversal'].with_context(wiz_context).create({
                    'reason': 'please reverse :c',
                    'date': '2022-09-05',
                })
                refund_invoice = self.env['account.move'].browse(refund_wizard.reverse_moves()['res_id'])
                refund_invoice.invoice_date_due = '2022-09-22'
                self._test_document_generation(
                    test_file_path=f'l10n_sa_edi/tests/test_files/{test_file}.xml',
                    expected_xpath=self.credit_note_applied_xpath,
                    freeze_time_at=freeze,
                    move=refund_invoice,
                )

    def testInvoiceWithRetention(self):
        """Test standard invoice generation."""

        retention_tax = self.env['account.tax'].create({
            'l10n_sa_is_retention': True,
            'name': 'Retention Tax',
            'amount_type': 'percent',
            'amount': -10.0,
        })

        move_data = {
            'name': 'INV/2022/00014',
            'invoice_date': '2022-09-05',
            'invoice_date_due': '2022-09-22',
            'partner_id': self.partner_sa,
            'invoice_line_ids': [{
                'product_id': self.product_a.id,
                'price_unit': self.product_a.standard_price,
                'quantity': 1,
                'tax_ids': self.tax_15.ids + retention_tax.ids,
            }]
        }

        self._test_document_generation(
            document_type='invoice',
            test_file_path='l10n_sa_edi/tests/compliance/standard/invoice.xml',
            expected_xpath=self.invoice_applied_xpath,
            move_data=move_data,
            freeze_time_at=datetime(2022, 9, 5, 8, 20, 2, tzinfo=timezone('Etc/GMT-3'))
        )
