# -*- coding: utf-8 -*-
from .common import TestMxEdiCommon, EXTERNAL_MODE
from odoo import fields, Command
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import misc
from odoo.tools.misc import file_open

from datetime import datetime
from dateutil.relativedelta import relativedelta
from lxml import etree
from pytz import timezone

from odoo.addons.l10n_mx_edi.models.l10n_mx_edi_document import CFDI_DATE_FORMAT


@tagged('post_install_l10n', 'post_install', '-at_install', *(['-standard', 'external'] if EXTERNAL_MODE else []))
class TestCFDIInvoice(TestMxEdiCommon):

    def test_invoice_misc_business_values(self):
        for move_type, output_file in (
            ('out_invoice', 'test_misc_business_values_invoice'),
            ('out_refund', 'test_misc_business_values_credit_note')
        ):
            with self.mx_external_setup(self.frozen_today), self.subTest(move_type=move_type):
                invoice = self._create_invoice(
                    invoice_incoterm_id=self.env.ref('account.incoterm_FCA').id,
                    invoice_line_ids=[
                        Command.create({
                            'product_id': self.product.id,
                            'price_unit': 2000.0,
                            'quantity': 5,
                            'discount': 20.0,
                        }),
                        # Ignored lines by the CFDI:
                        Command.create({
                            'product_id': self.product.id,
                            'price_unit': 2000.0,
                            'quantity': 0.0,
                        }),
                        Command.create({
                            'product_id': self.product.id,
                            'price_unit': 0.0,
                            'quantity': 10.0,
                        }),
                    ],
                )
                with self.with_mocked_pac_sign_success():
                    invoice._l10n_mx_edi_cfdi_invoice_try_send()
                self._assert_invoice_cfdi(invoice, output_file)

    def test_customer_in_mx(self):
        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice()
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_customer_in_mx_inv')

            payment = self._create_payment(invoice)
            with self.with_mocked_pac_sign_success():
                payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment.move_id, 'test_customer_in_mx_pay')

    def test_customer_in_us(self):
        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(partner_id=self.partner_us.id)
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_customer_in_us_inv')

            payment = self._create_payment(invoice)
            with self.with_mocked_pac_sign_success():
                payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment.move_id, 'test_customer_in_us_pay')

    def test_customer_no_country(self):
        with self.mx_external_setup(self.frozen_today):
            self.partner_us.country_id = None
            invoice = self._create_invoice(partner_id=self.partner_us.id)
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_customer_no_country_inv')

    def test_customer_in_mx_to_public(self):
        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(l10n_mx_edi_cfdi_to_public=True)
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_customer_in_mx_to_public_inv')

    def test_invoice_taxes(self):
        def create_invoice(taxes_list, l10n_mx_edi_cfdi_to_public=False):
            invoice_line_ids = []
            for i, taxes in enumerate(taxes_list, start=1):
                invoice_line_ids.append(Command.create({
                    'product_id': self.product.id,
                    'price_unit': 1000.0 * i,
                    'quantity': 5,
                    'discount': 20.0,
                    'tax_ids': [Command.set(taxes.ids)],
                }))
                # Full discounted line:
                invoice_line_ids.append(Command.create({
                    'product_id': self.product.id,
                    'price_unit': 1000.0 * i,
                    'discount': 100.0,
                    'tax_ids': [Command.set(taxes.ids)],
                }))
            return self._create_invoice(
                invoice_line_ids=invoice_line_ids,
                l10n_mx_edi_cfdi_to_public=l10n_mx_edi_cfdi_to_public,
            )

        with self.mx_external_setup(self.frozen_today):
            for index, taxes_list in enumerate(self.existing_taxes_combinations_to_test, start=1):
                with self.subTest(index=index):
                    # Test the invoice CFDI.
                    self.partner_mx.l10n_mx_edi_no_tax_breakdown = False
                    invoice = create_invoice(taxes_list)
                    with self.with_mocked_pac_sign_success():
                        invoice._l10n_mx_edi_cfdi_invoice_try_send()
                    self._assert_invoice_cfdi(invoice, f'test_invoice_taxes_{index}_invoice')

                    # Test the payment CFDI.
                    payment = self._create_payment(invoice)
                    with self.with_mocked_pac_sign_success():
                        payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
                    self._assert_invoice_payment_cfdi(payment.move_id, f'test_invoice_taxes_{index}_payment')

                    # Test the global invoice CFDI.
                    invoice = create_invoice(taxes_list, l10n_mx_edi_cfdi_to_public=True)
                    with self.with_mocked_pac_sign_success():
                        invoice._l10n_mx_edi_cfdi_global_invoice_try_send()
                    self._assert_global_invoice_cfdi_from_invoices(invoice, f'test_invoice_taxes_{index}_ginvoice')

                    # Test the invoice with no tax breakdown.
                    self.partner_mx.l10n_mx_edi_no_tax_breakdown = True
                    invoice = create_invoice(taxes_list)
                    with self.with_mocked_pac_sign_success():
                        invoice._l10n_mx_edi_cfdi_invoice_try_send()
                    self._assert_invoice_cfdi(invoice, f'test_invoice_taxes_{index}_invoice_no_tax_breakdown')

    def test_invoice_addenda(self):
        with self.mx_external_setup(self.frozen_today):
            self.partner_mx.l10n_mx_edi_addenda = self.env['ir.ui.view'].create({
                'name': 'test_invoice_cfdi_addenda',
                'type': 'qweb',
                'arch': """
                    <t t-name="l10n_mx_edi.test_invoice_cfdi_addenda">
                        <test info="this is an addenda"/>
                    </t>
                """
            })

            invoice = self._create_invoice()
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_invoice_addenda')

    def test_invoice_negative_lines_dispatch_same_product(self):
        """ Ensure the distribution of negative lines is done on the same product first. """
        product1 = self.product
        product2 = self._create_product()

        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(
                invoice_line_ids=[
                    Command.create({
                        'product_id': product1.id,
                        'quantity': 5.0,
                        'tax_ids': [],
                    }),
                    Command.create({
                        'product_id': product2.id,
                        'quantity': -5.0,
                        'tax_ids': [],
                    }),
                    Command.create({
                        'product_id': product2.id,
                        'quantity': 12.0,
                        'tax_ids': [],
                    }),
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_invoice_negative_lines_dispatch_same_product')

    def test_invoice_negative_lines_dispatch_same_amount(self):
        """ Ensure the distribution of negative lines is done on the same amount. """
        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'quantity': 12.0,
                        'tax_ids': [],
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'quantity': 3.0,
                        'tax_ids': [],
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'quantity': 6.0,
                        'tax_ids': [],
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'quantity': -3.0,
                        'tax_ids': [],
                    }),
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_invoice_negative_lines_dispatch_same_amount')

    def test_invoice_negative_lines_dispatch_same_taxes(self):
        """ Ensure the distribution of negative lines is done exclusively on lines having the same taxes. """
        product1 = self.product
        product2 = self._create_product()

        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(
                invoice_line_ids=[
                    Command.create({
                        'product_id': product1.id,
                        'quantity': 12.0,
                        'tax_ids': [],
                    }),
                    Command.create({
                        'product_id': product1.id,
                        'quantity': 3.0,
                        'tax_ids': [],
                    }),
                    Command.create({
                        'product_id': product2.id,
                        'quantity': 6.0,
                        'tax_ids': [Command.set(self.tax_16.ids)],
                    }),
                    Command.create({
                        'product_id': product1.id,
                        'quantity': -3.0,
                        'tax_ids': [Command.set(self.tax_16.ids)],
                    }),
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_invoice_negative_lines_dispatch_same_taxes')

    def test_invoice_negative_lines_dispatch_biggest_amount(self):
        """ Ensure the distribution of negative lines is done on the biggest amount. """
        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'quantity': 3.0,
                        'tax_ids': [],
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'quantity': 12.0,
                        'discount': 10.0,  # price_subtotal: 10800
                        'tax_ids': [],
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'quantity': 8.0,
                        'discount': 20.0,  # price_subtotal: 6400
                        'tax_ids': [],
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'quantity': -22.0,
                        'discount': 22.0,  # price_subtotal: 17160
                        'tax_ids': [],
                    }),
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_invoice_negative_lines_dispatch_biggest_amount')

    def test_invoice_negative_lines_zero_total(self):
        """ Test an invoice completely refunded by the negative lines. """
        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'quantity': 12.0,
                        'tax_ids': [],
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'quantity': -12.0,
                        'tax_ids': [],
                    }),
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids, [{
                'move_id': invoice.id,
                'state': 'invoice_sent',
                'attachment_id': False,
                'cancel_button_needed': False,
            }])

    def test_invoice_negative_lines_orphan_negative_line(self):
        """ Test an invoice in which a negative line failed to be distributed. """
        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'quantity': 12.0,
                        'tax_ids': [Command.set(self.tax_16.ids)],
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'quantity': -2.0,
                        'tax_ids': [],
                    }),
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids, [{
                'move_id': invoice.id,
                'state': 'invoice_sent_failed',
            }])

    def test_global_invoice_negative_lines_zero_total(self):
        """ Test an invoice completely refunded by the negative lines. """
        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'quantity': 12.0,
                        'tax_ids': [],
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'quantity': -12.0,
                        'tax_ids': [],
                    }),
                ],
            )

            with self.with_mocked_pac_sign_success():
                self.env['l10n_mx_edi.global_invoice.create'] \
                    .with_context(invoice.l10n_mx_edi_action_create_global_invoice()['context']) \
                    .create({})\
                    .action_create_global_invoice()
            self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids, [{
                'invoice_ids': invoice.ids,
                'state': 'ginvoice_sent',
                'attachment_id': False,
                'cancel_button_needed': False,
            }])

    def test_global_invoice_negative_lines_orphan_negative_line(self):
        """ Test a global invoice containing an invoice having a negative line that failed to be distributed. """
        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'quantity': 12.0,
                        'tax_ids': [Command.set(self.tax_16.ids)],
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'quantity': -2.0,
                        'tax_ids': [],
                    }),
                ],
            )

            with self.with_mocked_pac_sign_success():
                self.env['l10n_mx_edi.global_invoice.create'] \
                    .with_context(invoice.l10n_mx_edi_action_create_global_invoice()['context']) \
                    .create({})\
                    .action_create_global_invoice()
            self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids, [{
                'invoice_ids': invoice.ids,
                'state': 'ginvoice_sent_failed',
            }])

    def test_global_invoice_including_partial_refund(self):
        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(
                l10n_mx_edi_cfdi_to_public=True,
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'quantity': 10.0,
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'quantity': -2.0,
                    }),
                ],
            )
            refund = self._create_invoice(
                l10n_mx_edi_cfdi_to_public=True,
                move_type='out_refund',
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'quantity': 3.0,
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'quantity': -1.0,
                    }),
                ],
                reversed_entry_id=invoice.id,
            )

            invoices = invoice + refund
            with self.with_mocked_pac_sign_success():
                # Calling the global invoice on the invoice will include the refund automatically.
                self.env['l10n_mx_edi.global_invoice.create']\
                    .with_context(invoice.l10n_mx_edi_action_create_global_invoice()['context'])\
                    .create({})\
                    .action_create_global_invoice()
            self._assert_global_invoice_cfdi_from_invoices(invoices, 'test_global_invoice_including_partial_refund')

            self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids, [{
                'invoice_ids': invoices.ids,
                'state': 'ginvoice_sent',
            }])

    def test_global_invoice_including_full_refund(self):
        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(
                l10n_mx_edi_cfdi_to_public=True,
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'quantity': 10.0,
                    }),
                ],
            )
            refund = self._create_invoice(
                l10n_mx_edi_cfdi_to_public=True,
                move_type='out_refund',
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'quantity': 10.0,
                    }),
                ],
                reversed_entry_id=invoice.id,
            )

            invoices = invoice + refund
            with self.with_mocked_pac_sign_success():
                self.env['l10n_mx_edi.global_invoice.create']\
                    .with_context(invoices.l10n_mx_edi_action_create_global_invoice()['context'])\
                    .create({})\
                    .action_create_global_invoice()

            self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids, [{
                'invoice_ids': invoices.ids,
                'state': 'ginvoice_sent',
                'attachment_id': False,
            }])

    def test_global_invoice_not_allowed_refund(self):
        with self.mx_external_setup(self.frozen_today):
            refund = self._create_invoice(
                l10n_mx_edi_cfdi_to_public=True,
                move_type='out_refund',
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'quantity': 3.0,
                    }),
                ],
            )
            with self.assertRaises(UserError):
                self.env['l10n_mx_edi.global_invoice.create']\
                    .with_context(refund.l10n_mx_edi_action_create_global_invoice()['context'])\
                    .create({})\
                    .action_create_global_invoice()

    def test_global_invoice_refund_after(self):
        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(
                l10n_mx_edi_cfdi_to_public=True,
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'quantity': 10.0,
                    }),
                ],
            )

            with self.with_mocked_pac_sign_success():
                self.env['l10n_mx_edi.global_invoice.create']\
                    .with_context(invoice.l10n_mx_edi_action_create_global_invoice()['context'])\
                    .create({})\
                    .action_create_global_invoice()

            self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids, [{
                'invoice_ids': invoice.ids,
                'state': 'ginvoice_sent',
            }])

            refund = self._create_invoice(
                l10n_mx_edi_cfdi_to_public=True,
                move_type='out_refund',
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'quantity': 3.0,
                    }),
                ],
                reversed_entry_id=invoice.id,
            )
            with self.assertRaises(UserError):
                self.env['l10n_mx_edi.global_invoice.create'] \
                    .with_context(invoice.l10n_mx_edi_action_create_global_invoice()['context']) \
                    .create({})
            with self.with_mocked_pac_sign_success():
                self.env['account.move.send']\
                    .with_context(active_model=refund._name, active_ids=refund.ids)\
                    .create({})\
                    .action_send_and_print()
            self._assert_invoice_cfdi(refund, 'test_global_invoice_refund_after')

            self.assertRecordValues(refund.l10n_mx_edi_invoice_document_ids, [{
                'move_id': refund.id,
                'invoice_ids': refund.ids,
                'state': 'invoice_sent',
            }])

    def test_invoice_company_branch(self):
        self.env.company.write({
            'child_ids': [Command.create({
                'name': 'Branch A',
                'zip': '85120',
            })],
        })
        self.cr.precommit.run()  # load the CoA

        branch = self.env.company.child_ids
        self.product.company_id = branch
        with self.mx_external_setup(self.frozen_today - relativedelta(hours=1)):
            invoice = self._create_invoice(company_id=branch.id)
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_invoice_company_branch')

    def test_invoice_then_refund(self):
        # Create an invoice then sign it.
        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(l10n_mx_edi_cfdi_to_public=True)
            with self.with_mocked_pac_sign_success():
                self.env['account.move.send']\
                    .with_context(active_model=invoice._name, active_ids=invoice.ids)\
                    .create({})\
                    .action_send_and_print()
            self._assert_invoice_cfdi(invoice, 'test_invoice_then_refund_1')

            # You are no longer able to create a global invoice.
            with self.assertRaises(UserError):
                self.env['l10n_mx_edi.global_invoice.create']\
                    .with_context(invoice.l10n_mx_edi_action_create_global_invoice()['context'])\
                    .create({})

            # Create a refund.
            results = self.env['account.move.reversal']\
                .with_context(active_model='account.move', active_ids=invoice.ids)\
                .create({
                    'reason': "turlututu",
                    'journal_id': invoice.journal_id.id,
                })\
                .refund_moves()
            refund = self.env['account.move'].browse(results['res_id'])
            refund.auto_post = 'no'
            refund.action_post()

            # You can't make a global invoice for it.
            with self.assertRaises(UserError):
                self.env['l10n_mx_edi.global_invoice.create']\
                    .with_context(refund.l10n_mx_edi_action_create_global_invoice()['context'])\
                    .create({})

            # Create the CFDI and sign it.
            with self.with_mocked_pac_sign_success():
                self.env['account.move.send']\
                    .with_context(active_model=refund._name, active_ids=refund.ids)\
                    .create({})\
                    .action_send_and_print()
            self._assert_invoice_cfdi(refund, 'test_invoice_then_refund_2')
            self.assertRecordValues(refund, [{
                'l10n_mx_edi_cfdi_origin': f'01|{invoice.l10n_mx_edi_cfdi_uuid}',
            }])

    def test_global_invoice_then_refund(self):
        # Create a global invoice and sign it.
        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(l10n_mx_edi_cfdi_to_public=True)
            with self.with_mocked_pac_sign_success():
                self.env['l10n_mx_edi.global_invoice.create']\
                    .with_context(invoice.l10n_mx_edi_action_create_global_invoice()['context'])\
                    .create({})\
                    .action_create_global_invoice()
            self._assert_global_invoice_cfdi_from_invoices(invoice, 'test_global_invoice_then_refund_1')

            # You are not able to create an invoice for it.
            wizard = self.env['account.move.send']\
                .with_context(active_model=invoice._name, active_ids=invoice.ids)\
                .create({})
            self.assertRecordValues(wizard, [{'l10n_mx_edi_enable_cfdi': False}])

            # Refund the invoice.
            results = self.env['account.move.reversal']\
                .with_context(active_model='account.move', active_ids=invoice.ids)\
                .create({
                    'reason': "turlututu",
                    'journal_id': invoice.journal_id.id,
                })\
                .refund_moves()
            refund = self.env['account.move'].browse(results['res_id'])
            refund.auto_post = 'no'
            refund.action_post()

            # You can't do a global invoice for a refund
            with self.assertRaises(UserError):
                self.env['l10n_mx_edi.global_invoice.create']\
                    .with_context(refund.l10n_mx_edi_action_create_global_invoice()['context'])\
                    .create({})

            # Sign the refund.
            with self.with_mocked_pac_sign_success():
                self.env['account.move.send']\
                    .with_context(active_model=refund._name, active_ids=refund.ids)\
                    .create({})\
                    .action_send_and_print()
            self._assert_invoice_cfdi(refund, 'test_global_invoice_then_refund_2')

    def test_invoice_send_and_print_fallback_pdf(self):
        # Trigger an error when generating the CFDI
        self.product.unspsc_code_id = False

        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 1000.0,
                        'tax_ids': [Command.set(self.tax_0.ids)],
                    }),
                ],
            )
            template = self.env.ref(invoice._get_mail_template())
            invoice.with_context(skip_invoice_sync=True)._generate_pdf_and_send_invoice(template, force_synchronous=True, allow_fallback_pdf=True)
            self.assertFalse(invoice.invoice_pdf_report_id, "invoice_pdf_report_id shouldn't be set with the proforma PDF.")

    def test_import_invoice(self):
        file_name = "test_import_bill"
        full_file_path = misc.file_path(f'{self.test_module}/tests/test_files/{file_name}.xml')

        self.partner_mx.company_id = self.env.company

        # Read the problematic xml file that kept causing crash on bill uploads
        with file_open(full_file_path, "rb") as file:
            new_invoice = self._upload_document_on_journal(
                journal=self.company_data['default_journal_sale'],
                content=file.read(),
                filename=file_name,
            )

        self.assertRecordValues(new_invoice, [{
            'currency_id': self.comp_curr.id,
            'partner_id': self.partner_mx.id,
            'amount_tax': 80.0,
            'amount_untaxed': 500.0,
            'amount_total': 580.0,
            'invoice_date': fields.Date.from_string('2024-04-08'),
            'l10n_mx_edi_payment_method_id': self.env.ref('l10n_mx_edi.payment_method_efectivo').id,
            'l10n_mx_edi_usage': 'G03',
            'l10n_mx_edi_cfdi_uuid': '8CA06290-4800-4F93-8B1B-25B208BB1AFF',
        }])
        self.assertRecordValues(new_invoice.invoice_line_ids, [{
            'quantity': 1.0,
            'price_unit': 500.0,
            'discount': 0.0,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_po_id.id,
            'tax_ids': self.tax_16.ids,
        }])

        # The state of the document should be "Sent".
        self.assertEqual(new_invoice.l10n_mx_edi_invoice_document_ids.state, 'invoice_sent')

        # The "Update SAT" button should appear continuously (after posting).
        new_invoice.action_post()
        self.assertRecordValues(new_invoice, [{
            'need_cancel_request': True,
            'l10n_mx_edi_update_sat_needed': True,
        }])

    def test_import_bill(self):
        # Invoice with payment policy = PUE, otherwise 'FormaPago' (payment method) is set to '99' ('Por Definir')
        # and the initial payment method cannot be backtracked at import
        file_name = "test_import_bill"
        full_file_path = misc.file_path(f'{self.test_module}/tests/test_files/{file_name}.xml')

        # company's partner is not linked by default to its company.
        self.env.company.partner_id.company_id = self.env.company

        # Read the problematic xml file that kept causing crash on bill uploads
        with file_open(full_file_path, "rb") as file:
            file_content = file.read()
        new_bill = self._upload_document_on_journal(
            journal=self.company_data['default_journal_purchase'],
            content=file_content,
            filename=file_name,
        )

        self.assertRecordValues(new_bill, [{
            'currency_id': self.comp_curr.id,
            'partner_id': self.env.company.partner_id.id,
            'amount_tax': 80.0,
            'amount_untaxed': 500.0,
            'amount_total': 580.0,
            'invoice_date': fields.Date.from_string('2024-04-08'),
            'l10n_mx_edi_payment_method_id': self.env.ref('l10n_mx_edi.payment_method_efectivo').id,
            'l10n_mx_edi_usage': 'G03',
            'l10n_mx_edi_cfdi_uuid': '8CA06290-4800-4F93-8B1B-25B208BB1AFF',
        }])
        self.assertRecordValues(new_bill.invoice_line_ids, [{
            'quantity': 1.0,
            'price_unit': 500.0,
            'discount': 0.0,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_po_id.id,
            'tax_ids': self.tax_16_purchase.ids,
        }])

        # The state of the document should be "Sent".
        self.assertEqual(new_bill.l10n_mx_edi_invoice_document_ids.state, 'invoice_received')

        # The "Update SAT" button should appear continuously (after posting).
        new_bill.action_post()
        self.assertTrue(new_bill.l10n_mx_edi_update_sat_needed)
        with self.with_mocked_sat_call(lambda _x: 'valid'):
            new_bill.l10n_mx_edi_cfdi_try_sat()
        self.assertTrue(new_bill.l10n_mx_edi_update_sat_needed)

        # Check the error about duplicated fiscal folio.
        new_bill_same_folio = self._upload_document_on_journal(
            journal=self.company_data['default_journal_purchase'],
            content=file_content,
            filename=file_name,
        )
        new_bill_same_folio.action_post()
        self.assertRecordValues(new_bill_same_folio, [{'duplicated_ref_ids': new_bill.ids}])

    def test_add_cfdi_on_existing_bill_without_cfdi(self):
        file_name = 'test_add_cfdi_on_existing_bill'
        file_path = f'{self.test_module}/tests/test_files/{file_name}.xml'
        with file_open(file_path, 'rb') as file:
            cfdi_invoice = file.read()
        attachment = self.env['ir.attachment'].create({
            'mimetype': 'application/xml',
            'name': f'{file_name}.xml',
            'raw': cfdi_invoice,
        })
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_mx.id,
            'date': self.frozen_today.date(),
            'invoice_date': self.frozen_today.date(),
            'invoice_line_ids': [Command.create({'product_id': self.product.id})],
        })
        prev_invoice_line_ids = bill.invoice_line_ids
        # Bill was created without a cfdi invoice
        self.assertRecordValues(bill, [{
            'l10n_mx_edi_cfdi_attachment_id': None,
            'l10n_mx_edi_cfdi_uuid': None,
        }])
        # post message with the cfdi invoice attached
        bill.message_post(attachment_ids=attachment.ids)
        # check that the uuid is now set and the cfdi attachment is linked but the invoice lines did not change
        self.assertRecordValues(bill, [{
            'l10n_mx_edi_cfdi_attachment_id': attachment.id,
            'l10n_mx_edi_cfdi_uuid': '42000000-0000-0000-0000-000000000001',
            'invoice_line_ids': prev_invoice_line_ids.ids,
        }])

    def test_add_cfdi_on_existing_bill_with_cfdi(self):
        # Check that uploading a CFDI on a bill with an existing CFDI doesn't change the fiscal
        # folio or CFDI document
        file_name = "test_import_bill"
        full_file_path = misc.file_path(f'{self.test_module}/tests/test_files/{file_name}.xml')
        self.env.company.partner_id.company_id = self.env.company
        with file_open(full_file_path, "rb") as file:
            file_content = file.read()
        bill = self._upload_document_on_journal(
            journal=self.company_data['default_journal_purchase'],
            content=file_content,
            filename=file_name,
        )

        file_name = 'test_add_cfdi_on_existing_bill'
        file_path = f'{self.test_module}/tests/test_files/{file_name}.xml'
        with file_open(file_path, 'rb') as file:
            cfdi_invoice = file.read()
        attachment = self.env['ir.attachment'].create({
            'mimetype': 'application/xml',
            'name': f'{file_name}.xml',
            'raw': cfdi_invoice,
        })

        initial_uuid = bill.l10n_mx_edi_cfdi_uuid
        initial_attachment_id = bill.l10n_mx_edi_document_ids.attachment_id.id
        # post message with a different cfdi invoice attached
        bill.message_post(attachment_ids=attachment.ids)
        # check that the uuid and attachment have not changed to those of the attachment
        self.assertRecordValues(bill, [{
            'l10n_mx_edi_cfdi_uuid': initial_uuid,
            'l10n_mx_edi_cfdi_attachment_id': initial_attachment_id,
        }])

    def test_import_bill_with_extento(self):
        file_name = "test_import_bill_with_extento"
        full_file_path = misc.file_path(f'{self.test_module}/tests/test_files/{file_name}.xml')

        # Read the problematic xml file that kept causing crash on bill uploads
        with file_open(full_file_path, "rb") as file:
            new_bill = self._upload_document_on_journal(
                journal=self.company_data['default_journal_purchase'],
                content=file.read(),
                filename=file_name,
            )

        self.assertRecordValues(new_bill.invoice_line_ids, (
            {
                'quantity': 1,
                'price_unit': 54017.48,
                'tax_ids': self.tax_16_purchase.ids,
            },
            {
                'quantity': 1,
                'price_unit': 17893.00,
                'tax_ids': self.tax_0_exento_purchase.ids,
            }
        ))

    def test_import_bill_without_tax(self):
        file_name = "test_import_bill_without_tax"
        full_file_path = misc.file_path(f'{self.test_module}/tests/test_files/{file_name}.xml')

        # Read the problematic xml file that kept causing crash on bill uploads
        with file_open(full_file_path, "rb") as file:
            new_bill = self._upload_document_on_journal(
                journal=self.company_data['default_journal_purchase'],
                content=file.read(),
                filename=file_name,
            )

        self.assertRecordValues(new_bill.invoice_line_ids, (
            {
                'quantity': 1,
                'price_unit': 54017.48,
                'tax_ids': self.tax_16_purchase.ids,
            },
            {
                'quantity': 1,
                'price_unit': 17893.00,
                # This should be empty due to the error causing missing attribute 'TasaOCuota' to result in empty tax_ids
                'tax_ids': [],
            }
        ))

    def test_import_bill_with_withholding(self):
        file_name = "test_import_bill_with_withholding"
        full_file_path = misc.file_path(f'{self.test_module}/tests/test_files/{file_name}.xml')

        # Read the problematic xml file that kept causing crash on bill uploads
        with file_open(full_file_path, "rb") as file:
            new_invoice = self._upload_document_on_journal(
                journal=self.company_data['default_journal_purchase'],
                content=file.read(),
                filename=file_name,
            )

        self.assertRecordValues(new_invoice.line_ids.sorted(), (
            {
                'balance': 147.0,
                'tax_ids': (self.tax_16_purchase + self.tax_4_purchase_withholding).ids,
                'display_type': 'product',
                'tax_line_id': False,
            },
            {
                'balance': -5.88,
                'tax_ids': [],
                'display_type': 'tax',
                'tax_line_id': self.tax_4_purchase_withholding.id,
            },
            {
                'balance': 23.52,
                'tax_ids': [],
                'display_type': 'tax',
                'tax_line_id': self.tax_16_purchase.id,
            },
            {
                'balance': -164.64,
                'tax_ids': [],
                'display_type': 'payment_term',
                'tax_line_id': False,
            },
        ))

    def test_import_invoice_cfdi_unknown_partner(self):
        '''Test the import of invoices with unknown partners:
            * The partner should be created correctly
            * On the created move the "CFDI to Public" field (l10n_mx_edi_cfdi_to_public) should be set correctly.
        '''
        mx = self.env.ref('base.mx')
        subtests = [
            {
                'xml_file': 'test_import_invoice_cfdi_unknown_partner_1',
                'expected_invoice_vals': {
                    'l10n_mx_edi_cfdi_to_public': False,
                },
                'expected_partner_vals': {
                    'name': "INMOBILIARIA CVA",
                    'vat': 'ICV060329BY0',
                    'country_id': mx.id,
                    'property_account_position_id': False,
                    'zip': '26670',
                },
            },
            {
                'xml_file': 'test_import_invoice_cfdi_unknown_partner_2',
                'expected_invoice_vals': {
                    'l10n_mx_edi_cfdi_to_public': False,
                },
                'expected_partner_vals': {
                    'name': "PARTNER_US",
                    'vat': False,
                    'country_id': False,
                    'property_account_position_id': self.env['account.chart.template'].ref('account_fiscal_position_foreign').id,
                    'zip': False,
                },
            },
            {
                'xml_file': 'test_import_invoice_cfdi_unknown_partner_3',
                'expected_invoice_vals': {
                    'l10n_mx_edi_cfdi_to_public': True,
                },
                'expected_partner_vals': {
                    'name': "INMOBILIARIA CVA",
                    'vat': False,
                    'country_id': mx.id,
                    'property_account_position_id': False,
                    'zip': False,
                },
            },
        ]
        for subtest in subtests:
            xml_file = subtest['xml_file']

            with self.subTest(msg=xml_file), self.mocked_retrieve_partner():
                full_file_path = misc.file_path(f'{self.test_module}/tests/test_files/{xml_file}.xml')
                with file_open(full_file_path, "rb") as file:
                    invoice = self._upload_document_on_journal(
                        journal=self.company_data['default_journal_sale'],
                        content=file.read(),
                        filename=f'{xml_file}.xml',
                    )

                self.assertRecordValues(invoice, [subtest['expected_invoice_vals']])

                # field 'property_account_position_id' is company dependant
                partner = invoice.partner_id.with_company(company=invoice.company_id)
                self.assertRecordValues(partner, [subtest['expected_partner_vals']])

    def test_upload_xml_to_generate_invoice_with_exento_tax(self):
        self.env['account.tax'].search([('name', '=', 'Exento')]).unlink()
        self.env['account.tax.group'].search([('name', '=', 'Exento')]).unlink()

        file_name = "test_import_bill_with_extento"
        full_file_path = misc.file_path(f'{self.test_module}/tests/test_files/{file_name}.xml')

        with file_open(full_file_path, "rb") as file:
            new_bill = self._upload_document_on_journal(
                journal=self.company_data['default_journal_purchase'],
                content=file.read(),
                filename=file_name,
            )

        self.assertRecordValues(new_bill.invoice_line_ids, (
            {
                'quantity': 1,
                'price_unit': 54017.48,
            },
            {
                'quantity': 1,
                'price_unit': 17893.00,
            }
        ))

    def test_cfdi_rounding_1(self):
        def run(rounding_method):
            with self.mx_external_setup(self.frozen_today):
                invoice = self._create_invoice(
                    invoice_line_ids=[
                        Command.create({
                            'product_id': self.product.id,
                            'price_unit': 398.28,
                            'tax_ids': [Command.set(self.tax_16.ids)],
                        }),
                        Command.create({
                            'product_id': self.product.id,
                            'price_unit': 108.62,
                            'tax_ids': [Command.set(self.tax_16.ids)],
                        }),
                        Command.create({
                            'product_id': self.product.id,
                            'price_unit': 362.07,
                            'tax_ids': [Command.set(self.tax_16.ids)],
                        })] + [
                        Command.create({
                            'product_id': self.product.id,
                            'price_unit': 31.9,
                            'tax_ids': [Command.set(self.tax_16.ids)],
                        }),
                    ] * 12,
                )
                with self.with_mocked_pac_sign_success():
                    invoice._l10n_mx_edi_cfdi_invoice_try_send()
                self._assert_invoice_cfdi(invoice, f'test_cfdi_rounding_1_{rounding_method}_inv')

                payment = self._create_payment(invoice)
                with self.with_mocked_pac_sign_success():
                    payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
                self._assert_invoice_payment_cfdi(payment.move_id, f'test_cfdi_rounding_1_{rounding_method}_pay')

        self._test_cfdi_rounding(run)

    def test_cfdi_rounding_2(self):
        def run(rounding_method):
            with self.mx_external_setup(self.frozen_today):
                invoice = self._create_invoice(
                    invoice_line_ids=[
                        Command.create({
                            'product_id': self.product.id,
                            'quantity': quantity,
                            'price_unit': price_unit,
                            'discount': discount,
                            'tax_ids': [Command.set(self.tax_16.ids)],
                        })
                        for quantity, price_unit, discount in (
                            (30, 84.88, 13.00),
                            (30, 18.00, 13.00),
                            (3, 564.32, 13.00),
                            (33, 7.00, 13.00),
                            (20, 49.88, 13.00),
                            (100, 3.10, 13.00),
                            (2, 300.00, 13.00),
                            (36, 36.43, 13.00),
                            (36, 15.00, 13.00),
                            (2, 61.08, 0),
                            (2, 13.05, 0),
                        )
                    ])
                with self.with_mocked_pac_sign_success():
                    invoice._l10n_mx_edi_cfdi_invoice_try_send()
                self._assert_invoice_cfdi(invoice, f'test_cfdi_rounding_2_{rounding_method}_inv')

                payment = self._create_payment(invoice, currency_id=self.comp_curr.id)
                with self.with_mocked_pac_sign_success():
                    payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
                self._assert_invoice_payment_cfdi(payment.move_id, f'test_cfdi_rounding_2_{rounding_method}_pay')

        self._test_cfdi_rounding(run)

    def test_cfdi_rounding_3(self):
        today = self.frozen_today
        today_minus_1 = self.frozen_today - relativedelta(days=1)
        self.setup_rates(self.usd, (today_minus_1, 1 / 17.187), (today, 1 / 17.0357))

        def run(rounding_method):
            with self.mx_external_setup(today_minus_1):
                invoice = self._create_invoice(
                    currency_id=self.usd.id,
                    invoice_line_ids=[
                        Command.create({
                            'product_id': self.product.id,
                            'price_unit': 7.34,
                            'quantity': 200,
                            'tax_ids': [Command.set(self.tax_16.ids)],
                        }),
                    ],
                )
                with self.with_mocked_pac_sign_success():
                    invoice._l10n_mx_edi_cfdi_invoice_try_send()
                self._assert_invoice_cfdi(invoice, f'test_cfdi_rounding_3_{rounding_method}_inv')

            with self.mx_external_setup(today):
                payment = self._create_payment(
                    invoice,
                    payment_date=today,
                    currency_id=self.usd.id,
                )
                with self.with_mocked_pac_sign_success():
                    payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
                self._assert_invoice_payment_cfdi(payment.move_id, f'test_cfdi_rounding_3_{rounding_method}_pay')

        self._test_cfdi_rounding(run)

    def test_cfdi_rounding_4(self):
        today = self.frozen_today
        today_minus_1 = self.frozen_today - relativedelta(days=1)
        self.setup_rates(self.usd, (today_minus_1, 1 / 16.9912), (today, 1 / 17.068))

        def run(rounding_method):
            with self.mx_external_setup(today_minus_1):
                invoice1 = self._create_invoice(
                    currency_id=self.usd.id,
                    invoice_line_ids=[
                        Command.create({
                            'product_id': self.product.id,
                            'price_unit': 68.0,
                            'quantity': 68.25,
                            'tax_ids': [Command.set(self.tax_16.ids)],
                        }),
                    ],
                )
                with self.with_mocked_pac_sign_success():
                    invoice1._l10n_mx_edi_cfdi_invoice_try_send()
                self._assert_invoice_cfdi(invoice1, f'test_cfdi_rounding_4_{rounding_method}_inv_1')

            with self.mx_external_setup(today):
                invoice2 = self._create_invoice(
                    currency_id=self.usd.id,
                    invoice_line_ids=[
                        Command.create({
                            'product_id': self.product.id,
                            'price_unit': 68.0,
                            'quantity': 24.0,
                            'tax_ids': [Command.set(self.tax_16.ids)],
                        }),
                    ],
                )
                with self.with_mocked_pac_sign_success():
                    invoice2._l10n_mx_edi_cfdi_invoice_try_send()
                self._assert_invoice_cfdi(invoice2, f'test_cfdi_rounding_4_{rounding_method}_inv_2')

            invoices = invoice1 + invoice2
            with self.mx_external_setup(today):
                payment = self._create_payment(
                    invoices,
                    amount=7276.68,
                    currency_id=self.usd.id,
                    payment_date=today,
                )
                with self.with_mocked_pac_sign_success():
                    payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
                self._assert_invoice_payment_cfdi(payment.move_id, f'test_cfdi_rounding_4_{rounding_method}_pay')

        self._test_cfdi_rounding(run)

    def test_cfdi_rounding_5(self):
        def run(rounding_method):
            with self.mx_external_setup(self.frozen_today):
                invoice = self._create_invoice(
                    invoice_line_ids=[
                        Command.create({
                            'product_id': self.product.id,
                            'price_unit': price_unit,
                            'quantity': quantity,
                        })
                        for quantity, price_unit in (
                            (412.0, 43.65),
                            (412.0, 43.65),
                            (90.0, 50.04),
                            (500.0, 11.77),
                            (500.0, 34.93),
                            (90.0, 50.04),
                        )
                    ],
                )
                with self.with_mocked_pac_sign_success():
                    invoice._l10n_mx_edi_cfdi_invoice_try_send()
                self._assert_invoice_cfdi(invoice, f'test_cfdi_rounding_5_{rounding_method}_inv')

                payment = self._create_payment(invoice)
                with self.with_mocked_pac_sign_success():
                    payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
                self._assert_invoice_payment_cfdi(payment.move_id, f'test_cfdi_rounding_5_{rounding_method}_pay')

        self._test_cfdi_rounding(run)

    def test_cfdi_rounding_6(self):
        def run(rounding_method):
            with self.mx_external_setup(self.frozen_today):
                invoice = self._create_invoice(
                    invoice_line_ids=[
                        Command.create({
                            'product_id': self.product.id,
                            'price_unit': price_unit,
                            'quantity': quantity,
                            'discount': 30.0,
                        })
                        for quantity, price_unit in (
                            (7.0, 724.14),
                            (4.0, 491.38),
                            (2.0, 318.97),
                            (7.0, 224.14),
                            (6.0, 206.90),
                            (6.0, 129.31),
                            (6.0, 189.66),
                            (16.0, 775.86),
                            (2.0, 7724.14),
                            (2.0, 1172.41),
                        )
                    ],
                )
                with self.with_mocked_pac_sign_success():
                    invoice._l10n_mx_edi_cfdi_invoice_try_send()
                self._assert_invoice_cfdi(invoice, f'test_cfdi_rounding_6_{rounding_method}_inv')

                payment = self._create_payment(invoice)
                with self.with_mocked_pac_sign_success():
                    payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
                self._assert_invoice_payment_cfdi(payment.move_id, f'test_cfdi_rounding_6_{rounding_method}_pay')

        self._test_cfdi_rounding(run)

    def test_cfdi_rounding_7(self):
        def run(rounding_method):
            with self.mx_external_setup(self.frozen_today):
                invoice = self._create_invoice(
                    invoice_line_ids=[
                        Command.create({
                            'product_id': self.product.id,
                            'price_unit': price_unit,
                            'quantity': quantity,
                            'tax_ids': [Command.set(taxes.ids)],
                        })
                        for quantity, price_unit, taxes in (
                            (12.0, 457.92, self.tax_26_5_ieps + self.tax_16),
                            (12.0, 278.04, self.tax_26_5_ieps + self.tax_16),
                            (12.0, 539.76, self.tax_26_5_ieps + self.tax_16),
                            (36.0, 900.0, self.tax_16),
                        )
                    ],
                )
                with self.with_mocked_pac_sign_success():
                    invoice._l10n_mx_edi_cfdi_invoice_try_send()
                self._assert_invoice_cfdi(invoice, f'test_cfdi_rounding_7_{rounding_method}_inv')

                payment = self._create_payment(invoice)
                with self.with_mocked_pac_sign_success():
                    payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
                self._assert_invoice_payment_cfdi(payment.move_id, f'test_cfdi_rounding_7_{rounding_method}_pay')

        self._test_cfdi_rounding(run)

    def test_cfdi_rounding_8(self):
        def run(rounding_method):
            with self.mx_external_setup(self.frozen_today):
                invoice = self._create_invoice(
                    invoice_line_ids=[
                        Command.create({
                            'product_id': self.product.id,
                            'price_unit': price_unit,
                            'quantity': quantity,
                            'tax_ids': [Command.set(taxes.ids)],
                        })
                        for quantity, price_unit, taxes in (
                            (1.0, 244.0, self.tax_0_ieps + self.tax_0),
                            (8.0, 244.0, self.tax_0_ieps + self.tax_0),
                            (1.0, 2531.0, self.tax_0),
                            (1.0, 2820.75, self.tax_6_ieps + self.tax_0),
                            (1.0, 2531.0, self.tax_0),
                            (8.0, 468.0, self.tax_0_ieps + self.tax_0),
                            (1.0, 2820.75, self.tax_6_ieps + self.tax_0),
                            (1.0, 210.28, self.tax_7_ieps),
                            (1.0, 2820.75, self.tax_6_ieps + self.tax_0),
                        )
                    ],
                )
                with self.with_mocked_pac_sign_success():
                    invoice._l10n_mx_edi_cfdi_invoice_try_send()
                self._assert_invoice_cfdi(invoice, f'test_cfdi_rounding_8_{rounding_method}_inv')

                payment = self._create_payment(invoice)
                with self.with_mocked_pac_sign_success():
                    payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
                self._assert_invoice_payment_cfdi(payment.move_id, f'test_cfdi_rounding_8_{rounding_method}_pay')

        self._test_cfdi_rounding(run)

    def test_cfdi_rounding_9(self):
        usd_exchange_rates = (
            1 / 17.1325,
            1 / 17.1932,
            1 / 17.0398,
            1 / 17.1023,
            1 / 17.1105,
            1 / 16.7457,
        )

        def quick_create_invoice(rate, quantity_and_price_unit):
            # Only one rate is allowed per day and to make the test working in external_mode, we need to create 6 rates in less than
            # 3 days. So let's create/unlink the rate.
            rate = self.setup_rates(self.usd, (self.frozen_today, rate))
            invoice = self._create_invoice(
                currency_id=self.usd.id,
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': price_unit,
                        'quantity': quantity,
                        'tax_ids': [Command.set(self.tax_16.ids)],
                    })
                    for quantity, price_unit in quantity_and_price_unit
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            rate.unlink()
            return invoice

        def run(rounding_method):
            with self.mx_external_setup(self.frozen_today):
                invoice1 = quick_create_invoice(
                    usd_exchange_rates[0],
                    [(80.0, 21.9)],
                )
                invoice2 = quick_create_invoice(
                    usd_exchange_rates[1],
                    [(200.0, 13.36)],
                )
                invoice3 = quick_create_invoice(
                    usd_exchange_rates[1],
                    [(1200.0, 0.36), (1000.0, 0.44), (800.0, 0.44), (800.0, 0.23)],
                )
                invoice4 = quick_create_invoice(
                    usd_exchange_rates[2],
                    [(200.0, 21.9)],
                )
                invoice5 = quick_create_invoice(
                    usd_exchange_rates[3],
                    [(1000.0, 0.36), (500.0, 0.44), (500.0, 0.23), (400.0, 0.87), (200.0, 0.44)],
                )
                invoice6 = quick_create_invoice(
                    usd_exchange_rates[4],
                    [(200.0, 14.4)],
                )

                self.setup_rates(self.usd, (self.frozen_today, usd_exchange_rates[5]))
                payment = self._create_payment(
                    invoice1 + invoice2 + invoice3 + invoice4 + invoice5 + invoice6,
                    currency_id=self.env.company.currency_id.id,
                )
                with self.with_mocked_pac_sign_success():
                    payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
                self._assert_invoice_payment_cfdi(payment.move_id, f'test_cfdi_rounding_9_{rounding_method}_pay')

        self._test_cfdi_rounding(run)

    def test_partial_payment_1(self):
        date1 = self.frozen_today - relativedelta(days=2)
        date2 = self.frozen_today - relativedelta(days=1)
        date3 = self.frozen_today
        self.setup_rates(self.chf, (date1, 16.0), (date2, 17.0), (date3, 18.0))

        with self.mx_external_setup(date1):
            invoice = self._create_invoice()  # 1160 MXN
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()

            # Pay 10% in MXN.
            payment1 = self._create_payment(
                invoice,
                amount=116.0,
                currency_id=self.comp_curr.id,
                payment_date=date1,
            )
            with self.with_mocked_pac_sign_success():
                payment1.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment1.move_id, 'test_partial_payment_1_pay1')

            # Pay 10% in CHF (rate 1:16)
            payment2 = self._create_payment(
                invoice,
                amount=1856.0,
                currency_id=self.chf.id,
                payment_date=date1,
            )
            with self.with_mocked_pac_sign_success():
                payment2.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment2.move_id, 'test_partial_payment_1_pay2')

        with self.mx_external_setup(date2):
            # Pay 10% in CHF (rate 1:17).
            payment3 = self._create_payment(
                invoice,
                amount=1972.0,
                currency_id=self.chf.id,
                payment_date=date2,
            )
            with self.with_mocked_pac_sign_success():
                payment3.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment3.move_id, 'test_partial_payment_1_pay3')

        with self.mx_external_setup(date3):
            # Pay 10% in CHF (rate 1:18).
            payment4 = self._create_payment(
                invoice,
                amount=2088.0,
                currency_id=self.chf.id,
                payment_date=date3,
            )
            with self.with_mocked_pac_sign_success():
                payment4.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment4.move_id, 'test_partial_payment_1_pay4')

    def test_partial_payment_2(self):
        date1 = self.frozen_today - relativedelta(days=2)
        date2 = self.frozen_today - relativedelta(days=1)
        date3 = self.frozen_today
        self.setup_rates(self.chf, (date1, 16.0), (date2, 17.0), (date3, 18.0))
        self.setup_rates(self.usd, (date1, 17.0), (date2, 16.5), (date3, 16.0))

        with self.mx_external_setup(date1):
            invoice = self._create_invoice(
                currency_id=self.chf.id,
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 16000.0,
                    }),
                ],
            )  # 18560 CHF = 1160 MXN
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()

        with self.mx_external_setup(date2):
            # Pay 10% in MXN (116 MXN = 1972 CHF).
            payment1 = self._create_payment(
                invoice,
                amount=116.0,
                currency_id=self.comp_curr.id,
                payment_date=date2,
            )
            with self.with_mocked_pac_sign_success():
                payment1.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment1.move_id, 'test_partial_payment_2_pay1')

            # Pay 10% in USD (rate 1:16.5)
            payment2 = self._create_payment(
                invoice,
                amount=1914.0,
                currency_id=self.usd.id,
                payment_date=date2,
            )
            with self.with_mocked_pac_sign_success():
                payment2.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment2.move_id, 'test_partial_payment_2_pay2')

        with self.mx_external_setup(date3):
            # Pay 10% in MXN (116 MXN = 2088 CHF).
            payment3 = self._create_payment(
                invoice,
                amount=116.0,
                currency_id=self.comp_curr.id,
                payment_date=date3,
            )
            with self.with_mocked_pac_sign_success():
                payment3.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment3.move_id, 'test_partial_payment_2_pay3')

            # Pay 10% in USD (rate 1:16)
            payment4 = self._create_payment(
                invoice,
                amount=1856.0,
                currency_id=self.usd.id,
                payment_date=date3,
            )
            with self.with_mocked_pac_sign_success():
                payment4.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment4.move_id, 'test_partial_payment_2_pay4')

    def test_foreign_curr_payment_comp_curr_invoice_forced_balance(self):
        date1 = self.frozen_today - relativedelta(days=1)
        date2 = self.frozen_today
        self.setup_rates(self.chf, (date1, 16.0), (date2, 17.0))

        with self.mx_external_setup(date1):
            invoice = self._create_invoice(
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 1000.0,  # = 62.5 CHF
                    }),
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()

        with self.mx_external_setup(date2):
            payment = self.env['account.payment.register'] \
                .with_context(active_model='account.move', active_ids=invoice.ids) \
                .create({
                    'payment_date': date2,
                    'currency_id': self.chf.id,
                    'amount': 62.0,  # instead of 62.5 CHF
                    'payment_difference_handling': 'reconcile',
                    'writeoff_account_id': self.env.company.expense_currency_exchange_account_id.id,
                }) \
                ._create_payments()
            with self.with_mocked_pac_sign_success():
                payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(
                payment.move_id,
                'test_foreign_curr_payment_comp_curr_invoice_forced_balance',
            )

    def test_comp_curr_payment_foreign_curr_invoice_forced_balance(self):
        date1 = self.frozen_today - relativedelta(days=1)
        date2 = self.frozen_today
        self.setup_rates(self.chf, (date1, 16.0), (date2, 17.0))

        with self.mx_external_setup(date1):
            invoice = self._create_invoice(
                currency_id=self.chf.id,
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 62.5,  # = 1000 MXN
                    }),
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()

        with self.mx_external_setup(date2):
            payment = self.env['account.payment.register'] \
                .with_context(active_model='account.move', active_ids=invoice.ids) \
                .create({
                    'payment_date': date2,
                    'currency_id': self.comp_curr.id,
                    'amount': 998.0,  # instead of 1000.0 MXN
                    'payment_difference_handling': 'reconcile',
                    'writeoff_account_id': self.env.company.expense_currency_exchange_account_id.id,
                }) \
                ._create_payments()
            with self.with_mocked_pac_sign_success():
                payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(
                payment.move_id,
                'test_comp_curr_payment_foreign_curr_invoice_forced_balance',
            )

    def test_cfdi_date_with_timezone(self):

        def assert_cfdi_date(document, tz, expected_datetime=None):
            self.assertTrue(document)
            cfdi_node = etree.fromstring(document.attachment_id.raw)
            cfdi_date_str = cfdi_node.get('Fecha')
            expected_datetime = (expected_datetime or self.frozen_today.astimezone(tz).replace(tzinfo=None)).replace(microsecond=0)
            current_date = datetime.strptime(cfdi_date_str, CFDI_DATE_FORMAT).replace(microsecond=0)
            self.assertEqual(current_date, expected_datetime)

        addresses = [
            # America/Tijuana UTC-8 (-7 DST)
            {
                'state_id': self.env.ref('base.state_mx_bc').id,
                'zip': '22750',
                'timezone': timezone('America/Tijuana'),
            },
            # America/Bogota UTC-5
            {
                'state_id': self.env.ref('base.state_mx_q_roo').id,
                'zip': '77890',
                'timezone': timezone('America/Bogota'),
            },
            # America/Boise UTC-7 (-6 DST)
            {
                'state_id': self.env.ref('base.state_mx_chih').id,
                'zip': '31820',
                'timezone': timezone('America/Boise'),
            },
            # America/Guatemala (Tiempo del centro areas)
            {
                'state_id': self.env.ref('base.state_mx_nay').id,
                'zip': '63726',
                'timezone': timezone('America/Guatemala'),
            },
            # America/Matamoros UTC-6 (-5 DST)
            {
                'state_id': self.env.ref('base.state_mx_tamps').id,
                'zip': '87300',
                'timezone': timezone('America/Matamoros'),
            },
            # Pacific area
            {
                'state_id': self.env.ref('base.state_mx_son').id,
                'zip': '83530',
                'timezone': timezone('America/Hermosillo'),
            },
            # America/Guatemala UTC-6
            {
                'state_id': self.env.ref('base.state_mx_ags').id,
                'zip': '20914',
                'timezone': timezone('America/Guatemala'),
            },
        ]

        for address in addresses:
            tz = address.pop('timezone')
            with self.subTest(zip=address['zip']):
                self.env.company.partner_id.write(address)

                # Invoice on the future.
                with self.mx_external_setup(self.frozen_today):
                    invoice = self._create_invoice(
                        invoice_date=self.frozen_today + relativedelta(days=2),
                        invoice_line_ids=[Command.create({'product_id': self.product.id})],
                    )
                    with self.with_mocked_pac_sign_success():
                        invoice._l10n_mx_edi_cfdi_invoice_try_send()
                    document = invoice.l10n_mx_edi_invoice_document_ids.filtered(lambda x: x.state == 'invoice_sent')[:1]
                    assert_cfdi_date(document, tz)

                # Invoice on the past.
                date_in_the_past = self.frozen_today - relativedelta(days=2)
                with self.mx_external_setup(self.frozen_today):
                    invoice = self._create_invoice(
                        invoice_date=date_in_the_past,
                        invoice_line_ids=[Command.create({'product_id': self.product.id})],
                    )
                    with self.with_mocked_pac_sign_success():
                        invoice._l10n_mx_edi_cfdi_invoice_try_send()
                    document = invoice.l10n_mx_edi_invoice_document_ids.filtered(lambda x: x.state == 'invoice_sent')[:1]
                    assert_cfdi_date(document, tz, expected_datetime=date_in_the_past.replace(hour=23, minute=59, second=0))

                with self.mx_external_setup(self.frozen_today):
                    invoice = self._create_invoice(invoice_line_ids=[Command.create({'product_id': self.product.id})])
                    with self.with_mocked_pac_sign_success():
                        invoice._l10n_mx_edi_cfdi_invoice_try_send()
                    document = invoice.l10n_mx_edi_invoice_document_ids.filtered(lambda x: x.state == 'invoice_sent')[:1]
                    assert_cfdi_date(document, tz)

                    # Test an immediate payment.
                    payment = self.env['account.payment.register'] \
                        .with_context(active_model='account.move', active_ids=invoice.ids) \
                        .create({'amount': 100.0}) \
                        ._create_payments()
                    with self.with_mocked_pac_sign_success():
                        payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
                    document = payment.l10n_mx_edi_payment_document_ids.filtered(lambda x: x.state == 'payment_sent')[:1]
                    assert_cfdi_date(document, tz)

                # Test a payment made 10 days ago but send today.
                with self.mx_external_setup(self.frozen_today - relativedelta(days=10)):
                    payment = self.env['account.payment.register'] \
                        .with_context(active_model='account.move', active_ids=invoice.ids) \
                        .create({'amount': 100.0}) \
                        ._create_payments()
                with self.mx_external_setup(self.frozen_today):
                    with self.with_mocked_pac_sign_success():
                        payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
                    document = payment.l10n_mx_edi_payment_document_ids.filtered(lambda x: x.state == 'payment_sent')[:1]
                    assert_cfdi_date(document, tz)
