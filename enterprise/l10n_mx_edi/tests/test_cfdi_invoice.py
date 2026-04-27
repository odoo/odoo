# -*- coding: utf-8 -*-
from .common import TestMxEdiCommon, EXTERNAL_MODE
from odoo import fields, Command
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import misc
from odoo.tools.misc import file_open

import base64

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
                        # Product with Predial Account
                        Command.create({
                            'product_id': self._create_product(l10n_mx_edi_predial_account='123456789').id,
                            'quantity': 3.0,
                            'tax_ids': [],
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

    def test_customer_mx_incomplete_address(self):
        with self.mx_external_setup(self.frozen_today):
            for zip_code, country in (['33826', None], [None, self.env.ref('base.mx')], [None, None]):
                self.partner_mx.zip = zip_code
                self.partner_mx.country_id = country
                invoice = self._create_invoice()
                with self.with_mocked_pac_sign_success():
                    invoice._l10n_mx_edi_cfdi_invoice_try_send()
                self.assertTrue(invoice.l10n_mx_edi_cfdi_to_public)
                self._assert_invoice_cfdi(invoice, 'test_customer_mx_incomplete_address')

    def test_invoice_taxes_no_tax(self):
        with self.mx_external_setup(self.frozen_today):
            # Test the invoice CFDI.
            invoice = self._create_invoice(
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 1000.0,
                        'quantity': 5,
                        'discount': 20.0,
                        'tax_ids': [],
                    })
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_invoice_taxes_no_tax_invoice')

            # Test the payment CFDI.
            payment = self._create_payment(invoice)
            with self.with_mocked_pac_sign_success():
                payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment.move_id, 'test_invoice_taxes_no_tax_payment')

    def test_invoice_taxes_exento_and_zero(self):
        with self.mx_external_setup(self.frozen_today):
            # Test the invoice CFDI.
            invoice = self._create_invoice(
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 1000.0,
                        'tax_ids': [Command.set(self.tax_0_exento.ids)],
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 2000.0,
                        'tax_ids': [Command.set(self.tax_0.ids)],
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 3000.0,
                        'tax_ids': [Command.set(self.tax_16.ids)],
                    }),
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_invoice_taxes_exento_and_zero_invoice')

            # Test the payment CFDI.
            payment = self._create_payment(invoice)
            with self.with_mocked_pac_sign_success():
                payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment.move_id, 'test_invoice_taxes_exento_and_zero_payment')

    def test_invoice_taxes_withholding(self):
        with self.mx_external_setup(self.frozen_today):
            # Test the invoice CFDI.
            invoice = self._create_invoice(
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 1000.0,
                        'tax_ids': [Command.set((self.tax_16 + self.tax_10_ret_isr + self.tax_10_67_ret).ids)],
                    }),
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_invoice_taxes_withholding_invoice')

            # Test the payment CFDI.
            payment = self._create_payment(invoice)
            with self.with_mocked_pac_sign_success():
                payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment.move_id, 'test_invoice_taxes_withholding_payment')

    def test_invoice_taxes_ieps(self):
        with self.mx_external_setup(self.frozen_today):
            # Test the invoice CFDI.
            invoice = self._create_invoice(
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 1000.0,
                        'tax_ids': [Command.set((self.tax_8_ieps + self.tax_0).ids)],
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 2000.0,
                        'tax_ids': [Command.set((self.tax_53_ieps + self.tax_16).ids)],
                    }),
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_invoice_taxes_ieps_invoice')

            # Test the payment CFDI.
            payment = self._create_payment(invoice)
            with self.with_mocked_pac_sign_success():
                payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment.move_id, 'test_invoice_taxes_ieps_payment')

    def test_invoice_taxes_local(self):
        local_fixed_tax = self.env['account.tax'].create({
            'name': 'local fixed tax',
            'amount': 5.0,
            'amount_type': 'fixed',
            'l10n_mx_tax_type': 'local',
            'l10n_mx_factor_type': 'Cuota',
            'tax_group_id': self.local_tax_group.id,
        })
        with self.mx_external_setup(self.frozen_today):
            # Test the invoice CFDI.
            invoice = self._create_invoice(
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 1000.0,
                        'tax_ids': [Command.set(self.local_tax_16_transferred.ids)],
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 2000.0,
                        'tax_ids': [Command.set(self.local_tax_8_withholding.ids)],
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 3000.0,
                        'tax_ids': [Command.set(self.local_tax_3_5_withholding.ids)],
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 4000.0,
                        'tax_ids': [Command.set(self.tax_16.ids)],
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 2500.0,
                        'quantity': 2.0,
                        'tax_ids': [Command.set(local_fixed_tax.ids)],
                    }),
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_invoice_taxes_local_invoice')

            # Test the payment CFDI.
            payment = self._create_payment(invoice)
            with self.with_mocked_pac_sign_success():
                payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment.move_id, 'test_invoice_taxes_local_payment')

    def test_invoice_taxes_cuota(self):
        self.env['decimal.precision'].search([('name', '=', 'Product Price')]).digits = 6
        tax_cuota = self.fixed_tax(
            name="Cuota 14.0163",
            amount=14.0163,
            l10n_mx_factor_type='Cuota',
            l10n_mx_tax_type='ieps',
        )

        with self.mx_external_setup(self.frozen_today):
            # Test the invoice CFDI.
            invoice = self._create_invoice(
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 523.448276,
                        'tax_ids': [Command.set(tax_cuota.ids)],
                    })
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_invoice_taxes_cuota_invoice')

            # Test the payment CFDI.
            payment = self._create_payment(invoice)
            with self.with_mocked_pac_sign_success():
                payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment.move_id, 'test_invoice_taxes_cuota_payment')

    def test_invoice_taxes_cuota_with_custom_tax(self):
        account_tax_python = self.env['ir.module.module']._get('account_tax_python')
        if account_tax_python.state != 'installed':
            return

        tax_cuota = self.python_tax(
            formula="6.4555 * quantity",
            l10n_mx_factor_type='Cuota',
            l10n_mx_tax_type='ieps',
            price_include_override='tax_included',
            include_base_amount=True,
            sequence=1,
        )
        self.tax_16.price_include_override = 'tax_included'
        self.tax_16.sequence = 2

        with self.mx_external_setup(self.frozen_today):
            # Test the invoice CFDI.
            invoice = self._create_invoice(
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'quantity': 43775.0,
                        'price_unit': 18.33,
                        'tax_ids': [Command.set((tax_cuota + self.tax_16).ids)],
                    })
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_invoice_taxes_cuota_with_custom_tax_invoice')

            # Test the payment CFDI.
            payment = self._create_payment(invoice)
            with self.with_mocked_pac_sign_success():
                payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment.move_id, 'test_invoice_taxes_cuota_with_custom_tax_payment')

    def test_invoice_addenda(self):
        with self.mx_external_setup(self.frozen_today):
            addenda = self.env['l10n_mx_edi.addenda'].create({
                'name': 'test_invoice_cfdi_addenda',
                'arch': """
                    <t t-name="l10n_mx_edi.test_invoice_cfdi_addenda">
                        <test info="this is an addenda"/>
                    </t>
                """
            })
            self.partner_mx.l10n_mx_edi_addenda_id = addenda

            invoice = self._create_invoice()
            self.assertEqual(invoice.l10n_mx_edi_addenda_id, addenda)
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
                self.env['account.move.send.wizard']\
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
        with self.mx_external_setup(self.frozen_today - relativedelta(hours=1)):
            self.env.company.write({
                'child_ids': [Command.create({
                    'name': 'Branch A',
                    'zip': '85120',
                })],
            })
            branch = self.env.company.child_ids
            key = self.env['certificate.key'].create({
                'content': base64.encodebytes(misc.file_open('l10n_mx_edi/demo/pac_credentials/certificate.key', 'rb').read()),
                'password': '12345678a',
                'company_id': branch.id,
            })
            certificate = self.env['certificate.certificate'].create({
                'content': base64.encodebytes(misc.file_open('l10n_mx_edi/demo/pac_credentials/certificate.cer', 'rb').read()),
                'private_key_id': key.id,
                'company_id': branch.id,
            })
            branch.l10n_mx_edi_certificate_ids = certificate
            self.cr.precommit.run()  # load the CoA

            self.assertRecordValues(self.env.company, [{
                'l10n_mx_edi_global_invoice_sequence_id': False,
                'l10n_mx_edi_global_invoice_sequence_prefix': 'GINV/',
            }])

            self.assertRecordValues(branch, [{
                'l10n_mx_edi_global_invoice_sequence_id': False,
                'l10n_mx_edi_global_invoice_sequence_prefix': 'GINV/',
            }])

            self.product.company_id = branch

            # Invoice.
            invoice = self._create_invoice(company_id=branch.id)
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_invoice_company_branch_inv')

            # Global invoice using the sequence of the root company.
            invoice = self._create_invoice(company_id=branch.id, l10n_mx_edi_cfdi_to_public=True)
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_global_invoice_try_send()
            self._assert_global_invoice_cfdi_from_invoices(invoice, 'test_invoice_company_branch_ginvoice_1')

            # Global invoice with a custom global invoice sequence on the branch.
            branch.l10n_mx_edi_global_invoice_sequence_prefix = "SAL/"

            self.assertRecordValues(branch, [{
                'l10n_mx_edi_global_invoice_sequence_prefix': 'SAL/',
            }])
            self.assertTrue(branch.l10n_mx_edi_global_invoice_sequence_id)

            invoice = self._create_invoice(company_id=branch.id, l10n_mx_edi_cfdi_to_public=True)
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_global_invoice_try_send()
            self._assert_global_invoice_cfdi_from_invoices(invoice, 'test_invoice_company_branch_ginvoice_2')

    def test_invoice_then_refund(self):
        # Create an invoice then sign it.
        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(l10n_mx_edi_cfdi_to_public=True)
            with self.with_mocked_pac_sign_success():
                wizard = self.env['account.move.send.wizard']\
                    .with_context(active_model=invoice._name, active_ids=invoice.ids)\
                    .create({})
                wizard.action_send_and_print()
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
                self.env['account.move.send.wizard']\
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
            wizard = self.env['account.move.send.wizard']\
                .with_context(active_model=invoice._name, active_ids=invoice.ids)\
                .create({})
            self.assertFalse(wizard.extra_edi_checkboxes and wizard.extra_edi_checkboxes.get('mx_cfdi'))

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
                self.env['account.move.send.wizard']\
                    .with_context(active_model=refund._name, active_ids=refund.ids)\
                    .create({})\
                    .action_send_and_print()
            self._assert_invoice_cfdi(refund, 'test_global_invoice_then_refund_2')

    def test_global_invoice_foreign_currency(self):
        with self.mx_external_setup(self.frozen_today):
            usd = self.setup_other_currency('USD', rates=[(self.frozen_today, 1 / 17.0398)])
            invoice1 = self._create_invoice(currency_id=usd.id, l10n_mx_edi_cfdi_to_public=True)
            invoice2 = self._create_invoice(l10n_mx_edi_cfdi_to_public=True)
            invoices = invoice1 + invoice2

            with self.with_mocked_pac_sign_success():
                self.assertRaisesRegex(UserError, "You can only process invoices sharing the same currency.", invoices._l10n_mx_edi_cfdi_global_invoice_try_send)
                invoice1._l10n_mx_edi_cfdi_global_invoice_try_send()
                invoice2._l10n_mx_edi_cfdi_global_invoice_try_send()
            self._assert_global_invoice_cfdi_from_invoices(invoice1, "test_global_invoice_foreign_currency")

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
            invoice.with_context(skip_invoice_sync=True)._generate_and_send(allow_fallback_pdf=True)
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
                    'l10n_mx_edi_cfdi_to_public': True,
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
                    })
                ] + [
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 31.9,
                        'tax_ids': [Command.set(self.tax_16.ids)],
                    }),
                ] * 12,
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_cfdi_rounding_1_inv')

            payment = self._create_payment(invoice)
            with self.with_mocked_pac_sign_success():
                payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment.move_id, 'test_cfdi_rounding_1_pay')

    def test_cfdi_rounding_2(self):
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
            self._assert_invoice_cfdi(invoice, 'test_cfdi_rounding_2_inv')

            payment = self._create_payment(invoice, currency_id=self.comp_curr.id)
            with self.with_mocked_pac_sign_success():
                payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment.move_id, 'test_cfdi_rounding_2_pay')

    def test_cfdi_rounding_3(self):
        today = self.frozen_today
        today_minus_1 = self.frozen_today - relativedelta(days=1)
        usd = self.setup_other_currency('USD', rates=[(today_minus_1, 1 / 17.187), (today, 1 / 17.0357)])

        with self.mx_external_setup(today_minus_1):
            invoice = self._create_invoice(
                currency_id=usd.id,
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
            self._assert_invoice_cfdi(invoice, 'test_cfdi_rounding_3_inv')

        with self.mx_external_setup(today):
            payment = self._create_payment(
                invoice,
                payment_date=today,
                currency_id=usd.id,
            )
            with self.with_mocked_pac_sign_success():
                payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment.move_id, 'test_cfdi_rounding_3_pay')

    def test_cfdi_rounding_4(self):
        today = self.frozen_today
        today_minus_1 = self.frozen_today - relativedelta(days=1)
        usd = self.setup_other_currency('USD', rates=[(today_minus_1, 1 / 16.9912), (today, 1 / 17.068)])

        with self.mx_external_setup(today_minus_1):
            invoice1 = self._create_invoice(
                currency_id=usd.id,
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
            self._assert_invoice_cfdi(invoice1, 'test_cfdi_rounding_4_inv_1')

        with self.mx_external_setup(today):
            invoice2 = self._create_invoice(
                currency_id=usd.id,
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
            self._assert_invoice_cfdi(invoice2, 'test_cfdi_rounding_4_inv_2')

            invoices = invoice1 + invoice2
            with self.mx_external_setup(today):
                payment = self._create_payment(
                    invoices,
                    amount=7276.68,
                    currency_id=usd.id,
                    payment_date=today,
                )
                with self.with_mocked_pac_sign_success():
                    payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
                self._assert_invoice_payment_cfdi(payment.move_id, 'test_cfdi_rounding_4_pay')

    def test_cfdi_rounding_5(self):
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
            self._assert_invoice_cfdi(invoice, 'test_cfdi_rounding_5_inv')

            payment = self._create_payment(invoice)
            with self.with_mocked_pac_sign_success():
                payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment.move_id, 'test_cfdi_rounding_5_pay')

    def test_cfdi_rounding_6(self):
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
            self._assert_invoice_cfdi(invoice, 'test_cfdi_rounding_6_inv')

            payment = self._create_payment(invoice)
            with self.with_mocked_pac_sign_success():
                payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment.move_id, 'test_cfdi_rounding_6_pay')

    def test_cfdi_rounding_7(self):
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
            self._assert_invoice_cfdi(invoice, 'test_cfdi_rounding_7_inv')

            payment = self._create_payment(invoice)
            with self.with_mocked_pac_sign_success():
                payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment.move_id, 'test_cfdi_rounding_7_pay')

    def test_cfdi_rounding_8(self):
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
            self._assert_invoice_cfdi(invoice, 'test_cfdi_rounding_8_inv')

            payment = self._create_payment(invoice)
            with self.with_mocked_pac_sign_success():
                payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment.move_id, 'test_cfdi_rounding_8_pay')

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
            usd = self.setup_other_currency('USD', rates=[(self.frozen_today, rate)])
            invoice = self._create_invoice(
                currency_id=usd.id,
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
            return invoice

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

            self.setup_other_currency('USD', rates=[(self.frozen_today, usd_exchange_rates[5])])
            payment = self._create_payment(
                invoice1 + invoice2 + invoice3 + invoice4 + invoice5 + invoice6,
                currency_id=self.env.company.currency_id.id,
            )
            with self.with_mocked_pac_sign_success():
                payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment.move_id, 'test_cfdi_rounding_9_pay')

    def test_cfdi_rounding_10(self):
        def create_invoice(**kwargs):
            return self._create_invoice(
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': price_unit,
                        'tax_ids': [Command.set(taxes.ids)],
                    })
                    for price_unit, taxes in (
                        (550.0, self.tax_0),
                        (505.0, self.tax_16),
                        (495.0, self.tax_16),
                        (560.0, self.tax_0),
                        (475.0, self.tax_16),
                    )
                ],
                **kwargs,
            )

        self.tax_16.price_include_override = 'tax_included'
        with self.mx_external_setup(self.frozen_today):
            invoice = create_invoice()
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_cfdi_rounding_10_inv')

            payment = self._create_payment(invoice)
            with self.with_mocked_pac_sign_success():
                payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment.move_id, 'test_cfdi_rounding_10_pay')

            invoice = create_invoice(l10n_mx_edi_cfdi_to_public=True)
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_global_invoice_try_send()
            self._assert_global_invoice_cfdi_from_invoices(invoice, 'test_cfdi_rounding_10_ginvoice')

    def test_cfdi_rounding_11(self):
        self.tax_16.price_include_override = 'tax_included'
        with self.mx_external_setup(self.frozen_today):
            invoices = self.env['account.move']
            for price_unit in (2803.0, 1842.0, 2798.0, 3225.0, 3371.0):
                invoices += self._create_invoice(
                    l10n_mx_edi_cfdi_to_public=True,
                    invoice_line_ids=[
                         Command.create({
                             'product_id': self.product.id,
                             'price_unit': price_unit,
                             'tax_ids': [Command.set(self.tax_16.ids)],
                         }),
                    ],
                )
            with self.with_mocked_pac_sign_success():
                invoices._l10n_mx_edi_cfdi_global_invoice_try_send()
            self._assert_global_invoice_cfdi_from_invoices(invoices, 'test_cfdi_rounding_11_ginvoice')

    def test_cfdi_rounding_12(self):
        def create_invoice(**kwargs):
            return self._create_invoice(
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': price_unit,
                        'tax_ids': [Command.set(taxes.ids)],
                    })
                    for price_unit, taxes in (
                        (7.54, self.tax_8_ieps),
                        (7.41, self.tax_8_ieps),
                        (5.27, self.tax_16),
                        (5.21, self.tax_16),
                    )
                ],
                **kwargs,
            )

        with self.mx_external_setup(self.frozen_today):
            invoice = create_invoice()
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_cfdi_rounding_12_inv')

            payment = self._create_payment(invoice)
            with self.with_mocked_pac_sign_success():
                payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment.move_id, 'test_cfdi_rounding_12_pay')

            invoice = create_invoice(l10n_mx_edi_cfdi_to_public=True)
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_global_invoice_try_send()
            self._assert_global_invoice_cfdi_from_invoices(invoice, 'test_cfdi_rounding_12_ginvoice')

    def test_cfdi_rounding_13(self):
        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(
                invoice_line_ids=[
                     Command.create({
                         'product_id': self.product.id,
                         'price_unit': 4000.0,
                         'tax_ids': [Command.set((self.tax_16 + self.local_tax_3_5_withholding).ids)],
                     }),
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_cfdi_rounding_13_inv')

    def test_cfdi_rounding_14(self):
        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(
                invoice_line_ids=[
                     Command.create({
                         'product_id': self.product.id,
                         'price_unit': 100.05,
                         'discount': 50.0,
                         'tax_ids': [Command.set(self.tax_16.ids)],
                     }),
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_cfdi_rounding_14_inv')

    def test_cfdi_rounding_15(self):
        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(
                invoice_line_ids=[
                     Command.create({
                         'product_id': self.product.id,
                         'price_unit': 18103.45,
                         'discount': 50.0,
                         'tax_ids': [Command.set(self.tax_16.ids)],
                     }),
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_cfdi_rounding_15_inv')

    def test_cfdi_rounding_16(self):
        (self.tax_8_ieps + self.tax_26_5_ieps + self.tax_30_ieps + self.tax_53_ieps + self.tax_16).write({
            'active': True,
            'price_include_override': 'tax_included',
            'include_base_amount': True,
        })
        product1 = self._create_product(
            lst_price=489.57,
            taxes_id=[Command.set((self.tax_26_5_ieps + self.tax_16).ids)],
        )
        product2 = self._create_product(
            lst_price=789.57,
            taxes_id=[Command.set((self.tax_30_ieps + self.tax_16).ids)],
        )
        product3 = self._create_product(
            lst_price=7989.57,
            taxes_id=[Command.set((self.tax_53_ieps + self.tax_16).ids)],
        )
        product4 = self._create_product(
            lst_price=289.57,
            taxes_id=[Command.set((self.tax_8_ieps + self.tax_16).ids)],
        )
        product5 = self._create_product(
            lst_price=378.0,
            taxes_id=[Command.set(self.tax_0.ids)],
        )
        product6 = self._create_product(
            lst_price=1000.0,
            taxes_id=[Command.set(self.tax_16.ids)],
        )
        with self.mx_external_setup(self.frozen_today):
            invoices = self._create_invoice(
                l10n_mx_edi_cfdi_to_public=True,
                invoice_line_ids=[
                    Command.create({
                        'product_id': product.id,
                        'quantity': quantity,
                    })
                    for product, quantity in (
                        (product1, 3),
                        (product2, 4),
                        (product3, 3),
                        (product4, 2),
                        (product5, 1),
                        (product6, 3),
                    )
                ],
            )
            invoices += self._create_invoice(
                l10n_mx_edi_cfdi_to_public=True,
                invoice_line_ids=[
                    Command.create({
                        'product_id': product.id,
                        'quantity': quantity,
                    })
                    for product, quantity in (
                        (product1, 3),
                        (product2, 4),
                        (product3, 2),
                        (product4, 2),
                        (product5, 1),
                        (product6, 3),
                    )
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoices._l10n_mx_edi_cfdi_global_invoice_try_send()
            self._assert_global_invoice_cfdi_from_invoices(invoices, 'test_cfdi_rounding_16_ginvoice')

    def test_cfdi_rounding_17(self):
        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 3163.79,
                        'discount': 25.0,
                        'tax_ids': [Command.set(self.tax_16.ids)],
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 2992.41,
                        'discount': 25.0,
                        'tax_ids': [Command.set(self.tax_16.ids)],
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 3025.86,
                        'discount': 25.0,
                        'tax_ids': [Command.set(self.tax_16.ids)],
                    })
                ])
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_cfdi_rounding_17_inv')

    def test_cfdi_rounding_18(self):
        with self.mx_external_setup(self.frozen_today):
            self.partner_mx.l10n_mx_edi_no_tax_breakdown = True
            invoice = self._create_invoice(
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 50.00,
                        'tax_ids': [Command.set(self.tax_1_25_sale_withholding.ids)],
                    }),
                ])
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_cfdi_rounding_18_inv')
    
    def test_cfdi_rounding_19(self):
        with self.mx_external_setup(self.frozen_today):
            self.partner_mx.l10n_mx_edi_no_tax_breakdown = True
            invoice = self._create_invoice(
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 7.00,
                        'tax_ids': [Command.set(self.tax_1_25_sale_withholding.ids)],
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 43.00,
                        'tax_ids': [Command.set(self.tax_1_25_sale_withholding.ids)],
                    }),
                ])
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_cfdi_rounding_19_inv')

    def test_cfdi_rounding_20(self):
        with self.mx_external_setup(self.frozen_today):
            self.partner_mx.l10n_mx_edi_no_tax_breakdown = True
            invoice = self._create_invoice(
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 17.00,
                        'tax_ids': [Command.set(self.tax_1_25_sale_withholding.ids)],
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 33.00,
                        'tax_ids': [Command.set(self.tax_1_25_sale_withholding.ids)],
                    }),
                ])
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_cfdi_rounding_20_inv')

    def test_cfdi_rounding_21(self):
        rate = 1 / 20.4277
        usd = self.setup_other_currency('USD', rates=[(self.frozen_today, rate)])
        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 93.76,
                        'quantity': 172,
                        'tax_ids': [Command.set(self.tax_16.ids)],
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 74.18,
                        'quantity': 161,
                        'tax_ids': [Command.set(self.tax_16.ids)],
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 74.18,
                        'quantity': 162,
                        'tax_ids': [Command.set(self.tax_16.ids)],
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 93.76,
                        'quantity': 384,
                        'tax_ids': [Command.set(self.tax_16.ids)],
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 111.28,
                        'quantity': 178,
                        'tax_ids': [Command.set(self.tax_16.ids)],
                    }),
                ])

            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_cfdi_rounding_21_inv')

            payment = self._create_payment(invoice, currency_id=usd.id)
            with self.with_mocked_pac_sign_success():
                payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment.move_id, 'test_cfdi_rounding_21_pay')

    def test_cfdi_rounding_22(self):
        today = self.frozen_today
        today_minus_1 = self.frozen_today - relativedelta(days=1)
        usd = self.setup_other_currency('USD', rates=[
            (today_minus_1, 0.049216958195),
            (today, 0.053418803419),
        ])
        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(
                currency_id=usd.id,
                date=today_minus_1,
                invoice_date=today_minus_1,
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 91,
                        'quantity': 64,
                        'tax_ids': [Command.set(self.tax_16.ids)],
                    }),
                ])
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self._assert_invoice_cfdi(invoice, 'test_cfdi_rounding_22_inv')

            payment = self._create_payment(invoice, payment_date=today)
            with self.with_mocked_pac_sign_success():
                payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment.move_id, 'test_cfdi_rounding_22_pay')

    def test_cfdi_rounding_23(self):
        self.tax_16.price_include_override = 'tax_excluded'
        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(
                l10n_mx_edi_cfdi_to_public=True,
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 47.25,
                        'tax_ids': [Command.set(self.tax_16.ids)],
                        'discount': 50,
                    }),
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_global_invoice_try_send()
            self._assert_global_invoice_cfdi_from_invoices(invoice, 'test_cfdi_rounding_23_ginvoice')

    def test_cfdi_rounding_24(self):
        invoices = self.env['account.move']
        with self.mx_external_setup(self.frozen_today):
            for _ in range(12):
                invoices |= self._create_invoice(
                    l10n_mx_edi_cfdi_to_public=True,
                    invoice_line_ids=[
                        Command.create({
                            'product_id': self.product.id,
                            'price_unit': 72.89,
                            'tax_ids': [Command.set(self.tax_16.ids)],
                            'discount': 10,
                        }),
                    ],
                )
            with self.with_mocked_pac_sign_success():
                invoices._l10n_mx_edi_cfdi_global_invoice_try_send()
            self._assert_global_invoice_cfdi_from_invoices(invoices, 'test_cfdi_rounding_24_ginvoice')

    def test_partial_payment_1(self):
        date1 = self.frozen_today - relativedelta(days=2)
        date2 = self.frozen_today - relativedelta(days=1)
        date3 = self.frozen_today
        chf = self.setup_other_currency('CHF', rates=[(date1, 16.0), (date2, 17.0), (date3, 18.0)])

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
                currency_id=chf.id,
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
                currency_id=chf.id,
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
                currency_id=chf.id,
                payment_date=date3,
            )
            with self.with_mocked_pac_sign_success():
                payment4.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment4.move_id, 'test_partial_payment_1_pay4')

    def test_partial_payment_2(self):
        date1 = self.frozen_today - relativedelta(days=2)
        date2 = self.frozen_today - relativedelta(days=1)
        date3 = self.frozen_today
        chf = self.setup_other_currency('CHF', rates=[(date1, 16.0), (date2, 17.0), (date3, 18.0)])
        usd = self.setup_other_currency('USD', rates=[(date1, 17.0), (date2, 16.5), (date3, 16.0)])

        with self.mx_external_setup(date1):
            invoice = self._create_invoice(
                currency_id=chf.id,
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
                currency_id=usd.id,
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
                currency_id=usd.id,
                payment_date=date3,
            )
            with self.with_mocked_pac_sign_success():
                payment4.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment4.move_id, 'test_partial_payment_2_pay4')

    def test_partial_payment_3(self):
        """ Test a reconciliation chain with reconciliation with credit note in between. """
        date1 = self.frozen_today - relativedelta(days=2)
        date2 = self.frozen_today - relativedelta(days=1)
        date3 = self.frozen_today
        usd = self.setup_other_currency('USD', rates=[(date1, 17.0), (date2, 16.5), (date3, 17.5)])

        with self.mx_external_setup(date1):
            # MXN invoice at rate 19720 USD = 1160 MXN (1:17)
            invoice = self._create_invoice(
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 1000.0,
                    }),
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()

        with self.mx_external_setup(date2):
            # Pay 1914 USD = 116 MXN (1:16.5)
            payment1 = self._create_payment(
                invoice,
                amount=1914.0,
                currency_id=usd.id,
                payment_date=date2,
            )
            with self.with_mocked_pac_sign_success():
                payment1.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment1.move_id, 'test_partial_payment_3_pay1')
            self.assertRecordValues(invoice, [{'amount_residual': 1044.0}])

            # USD Credit note at rate 1914 USD = 116 MXN (1:16.5)
            refund = self._create_invoice(
                move_type='out_refund',
                currency_id=usd.id,
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 1650.0,
                    }),
                ],
            )
            (refund + invoice).line_ids.filtered(lambda line: line.display_type == 'payment_term').reconcile()
            self.assertRecordValues(invoice + refund, [
                # The refund reconciled 116 MXN:
                # - 112.59 MXN with the invoice.
                # - 3.41 MXN as an exchange difference (1972 - 1914) / 17 ~= 3.41)
                {'amount_residual': 931.41},
                {'amount_residual': 0.0},
            ])

            # Pay 1914 USD = 116 MXN (1:16.5)
            # The credit note should be subtracted from the residual chain.
            payment2 = self._create_payment(
                invoice,
                amount=1914.0,
                currency_id=usd.id,
                payment_date=date2,
            )
            with self.with_mocked_pac_sign_success():
                payment2.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment2.move_id, 'test_partial_payment_3_pay2')
            self.assertRecordValues(invoice, [{'amount_residual': 815.41}])

        with self.mx_external_setup(date3):
            # Pay 10% in USD at rate 1:17.5
            payment3 = self._create_payment(
                invoice,
                amount=2030.0,
                currency_id=usd.id,
                payment_date=date3,
            )
            with self.with_mocked_pac_sign_success():
                payment3.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment3.move_id, 'test_partial_payment_3_pay3')
            self.assertRecordValues(invoice, [{'amount_residual': 699.41}])

            # USD Credit note at rate 2030 USD = 116 MXN (1:17.5)
            refund = self._create_invoice(
                move_type='out_refund',
                currency_id=usd.id,
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 1750.0,
                    }),
                ],
            )
            (refund + invoice).line_ids.filtered(lambda line: line.display_type == 'payment_term').reconcile()
            self.assertRecordValues(invoice + refund, [
                # The refund reconciled 116 MXN with the invoice.
                # An exchange difference of (2030 - 1972) / 17 ~= 3.41 has been created.
                {'amount_residual': 580.0},
                {'amount_residual': 0.0},
            ])

            # Pay 10% in USD at rate 1:17.5
            # The credit note should be subtracted from the residual chain.
            payment4 = self._create_payment(
                invoice,
                amount=2030.0,
                currency_id=usd.id,
                payment_date=date3,
            )
            with self.with_mocked_pac_sign_success():
                payment4.move_id._l10n_mx_edi_cfdi_payment_try_send()
            self._assert_invoice_payment_cfdi(payment4.move_id, 'test_partial_payment_3_pay4')
            self.assertRecordValues(invoice, [{'amount_residual': 464.0}])

    def test_full_payment_rate(self):
        date1 = fields.Date.today() - relativedelta(days=1)
        date2 = fields.Date.today()
        usd = self.setup_other_currency('USD', rates=[(date1, 0.049905678268), (date2, 0.049073733284)])

        with self.mx_external_setup(date1):
            invoice = self._create_invoice(
                date=date1,
                currency_id=usd.id,
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 5490.00,
                        'quantity': 1,
                        'discount': 0.0,
                        'tax_ids': [Command.set(self.tax_16.ids)],
                    })],
                )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            self.assertEqual(invoice.l10n_mx_edi_cfdi_state, 'sent', f'Error: {invoice.l10n_mx_edi_document_ids.message}')

        with self.mx_external_setup(date2):
            payment = self._create_payment(
                invoice,
                amount=129772.07,
                payment_date=date2,
                currency_id=self.env.ref('base.MXN').id,
            )
            with self.with_mocked_pac_sign_success():
                invoice.l10n_mx_edi_cfdi_invoice_try_update_payments()
            self.assertEqual(payment.move_id.l10n_mx_edi_cfdi_state, 'sent', f'Error: {payment.move_id.l10n_mx_edi_document_ids.message}')
            self._assert_invoice_payment_cfdi(payment.move_id, 'test_full_payment_rate')

    def test_foreign_curr_statement_and_invoice_modify_exchange_move(self):
        """ Test a bank reconciliation multi currency reconcliation with remaining amount in company currency """
        date1 = self.frozen_today - relativedelta(days=1)
        date2 = self.frozen_today
        # Rates for how much USD for 1 MXN
        usd = self.setup_other_currency('USD', rates=[(date1, 1.5), (date2, 2.0001)])

        with self.mx_external_setup(date1):
            # 2 MXN invoices at rate 100 USD + 16% = 116 USD = 77.3 MXN (1:1.5)
            invoice1 = self._create_invoice(
                currency_id=usd.id,
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 100,
                    }),
                ],
            )
            invoice2 = self._create_invoice(
                currency_id=usd.id,
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 100,
                    }),
                ],
            )

            with self.with_mocked_pac_sign_success():
                invoice1._l10n_mx_edi_cfdi_invoice_try_send()
                invoice2._l10n_mx_edi_cfdi_invoice_try_send()

        bank_journal = self.env['account.journal'].create({
            'name': 'Bank 123456',
            'code': 'BNK67',
            'type': 'bank',
            'bank_acc_number': '1234567890',
            'currency_id': self.env.ref('base.USD').id,
            'l10n_mx_edi_payment_method_id': self.env.ref('l10n_mx_edi.payment_method_transferencia').id,  # To default to this payment method
        })

        with self.mx_external_setup(date2):
            # Bank transaction 232 USD = 115.9942 MXN ≃ 115.99 MXN (1:2.0001)
            # At this rate 116 USD = 57.9971 MXN ≃ 58.00 MXN which is not half of 115.99 MXN
            # => create a 0.01 MXN auto balance line

            statement_line1 = self.env['account.bank.statement.line'].create({
                'journal_id': bank_journal.id,
                'amount': 232.0,
                'date': date2,
                'payment_ref': 'test'
            })

            # Open bank reconciliation widget
            wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=statement_line1.id).new({})

            invoice_lines = (invoice1 | invoice2).line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
            wizard._action_add_new_amls(invoice_lines)

            self.assertRecordValues(wizard.line_ids, [
                # pylint: disable=C0326
                {'flag': 'liquidity',       'amount_currency': 232.0,      'currency_id': usd.id,   'balance': 115.99},
                {'flag': 'new_aml',         'amount_currency': -116.0,     'currency_id': usd.id,   'balance': -77.34},
                {'flag': 'exchange_diff',   'amount_currency': 0.0,        'currency_id': usd.id,   'balance': 19.34},
                {'flag': 'new_aml',         'amount_currency': -116.0,     'currency_id': usd.id,   'balance': -77.34},
                {'flag': 'exchange_diff',   'amount_currency': 0.0,        'currency_id': usd.id,   'balance': 19.34},
                {'flag': 'auto_balance',    'amount_currency': 0.00,       'currency_id': usd.id,   'balance': 0.01},
            ])

            # Remove 0.01 in the balance of first exchange line
            first_exchange_line = wizard.line_ids.filtered(lambda x: x.flag == 'exchange_diff')[:1]
            wizard._js_action_mount_line_in_edit(first_exchange_line.index)
            first_exchange_line.balance = 19.35
            wizard._line_value_changed_balance(first_exchange_line)

            # Every line balance so no 'auto_balance' is generated
            self.assertRecordValues(wizard.line_ids, [
                # pylint: disable=C0326
                {'flag': 'liquidity',       'amount_currency': 232.0,      'currency_id': usd.id,   'balance': 115.99},
                {'flag': 'new_aml',         'amount_currency': -116.0,     'currency_id': usd.id,   'balance': -77.34},
                {'flag': 'exchange_diff',   'amount_currency': 0.0,        'currency_id': usd.id,   'balance': 19.35},
                {'flag': 'new_aml',         'amount_currency': -116.0,     'currency_id': usd.id,   'balance': -77.34},
                {'flag': 'exchange_diff',   'amount_currency': 0.0,        'currency_id': usd.id,   'balance': 19.34},
            ])

            self.assertRecordValues(wizard, [{'state': 'valid'}])

            wizard._action_validate()

            self.assertRecordValues(statement_line1, [{'is_reconciled': True}])
            self.assertRecordValues(invoice1, [{'payment_state': 'paid'}])
            self.assertRecordValues(invoice2, [{'payment_state': 'paid'}])

            with self.with_mocked_pac_sign_success():
                statement_line1.move_id._l10n_mx_edi_cfdi_payment_try_send()

            self._assert_invoice_payment_cfdi(statement_line1.move_id, 'test_foreign_curr_statement_and_invoice_modify_exchange_move')

    def test_sw_finkok_CRP20211_usd_statement_in_mxn_journal_rounded_exchange_rate(self):
        """ Test rounding of exchange rate in payment cfdi of a statement line with foreign currency
        using Finkok, SW, or Solucion Factible does not trigger the CRP20211 error.
        """
        payment_date = self.frozen_today
        # Rates for how much USD for 1 MXN
        usd = self.setup_other_currency('USD', rates=[(payment_date, 0.05)])

        bank_journal = self.env['account.journal'].create({
            'name': 'Bank 123456',
            'code': 'BNK67',
            'type': 'bank',
            'bank_acc_number': '1234567890',
            'l10n_mx_edi_payment_method_id': self.env.ref('l10n_mx_edi.payment_method_transferencia').id,  # To default to this payment method
        })

        for pac in ['finkok', 'solfact']:
            self.env.company.l10n_mx_edi_pac = pac

            with self.mx_external_setup(payment_date):
                invoice = self._create_invoice(
                    currency_id=usd.id,
                    invoice_line_ids=[
                        Command.create({
                            'product_id': self.product.id,
                            'price_unit': 11396.55,  # + tax(16%) = 13220.0 USD
                        }),
                    ],
                )

                with self.with_mocked_pac_sign_success():
                    invoice._l10n_mx_edi_cfdi_invoice_try_send()

            with self.mx_external_setup(payment_date):
                # Those are the important amount because
                # 305147.51 MXN / 13220.0 USD = 23.082262481 ≃ 23.082262 MXN/USD
                # 13220.0 USD * 23.082262 MXN/USD = 305147.50 MXN which is not 305147.51 MXN
                st_line = self.env['account.bank.statement.line'].create({
                    'journal_id': bank_journal.id,
                    'amount_currency': 13220.00,  # USD
                    'amount': 305147.51,  # MXN
                    'foreign_currency_id': self.env.ref('base.USD').id,
                    'date': payment_date,
                    'payment_ref': 'test'
                })

                # Open bank reconciliation widget and reconcile bank transaction with invoice
                wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
                receivable_line = invoice.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
                wizard._action_add_new_amls(receivable_line)
                self.assertRecordValues(wizard, [{'state': 'valid'}])
                wizard._action_validate()
                self.assertRecordValues(st_line, [{'is_reconciled': True}])
                self.assertRecordValues(invoice, [{'payment_state': 'paid'}])

                # Generate payment cfdi file
                with self.with_mocked_pac_sign_success():
                    st_line.move_id._l10n_mx_edi_cfdi_payment_try_send()

                # Without fix, the generated cfdi payment file will be refused by Quadrum (finkok) due to CRP20211
                self._assert_invoice_payment_cfdi(st_line.move_id, 'test_sw_finkok_CRP20211_usd_statement_in_mxn_journal_rounded_exchange_rate_pay')

    def test_foreign_curr_payment_comp_curr_invoice_forced_balance(self):
        date1 = self.frozen_today - relativedelta(days=1)
        date2 = self.frozen_today
        chf = self.setup_other_currency('CHF', rates=[(date1, 16.0), (date2, 17.0)])

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
                    'currency_id': chf.id,
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
        chf = self.setup_other_currency('CHF', rates=[(date1, 16.0), (date2, 17.0)])

        with self.mx_external_setup(date1):
            invoice = self._create_invoice(
                currency_id=chf.id,
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

                # Invoice created in the past with a date which was then in the future,
                # which was already attempted to be sent in the past and which we try to resend today
                with self.mx_external_setup(self.frozen_today):
                    invoice = self._create_invoice(invoice_date=date_in_the_past)
                    previous_send_time = (self.frozen_today - relativedelta(days=2)).replace(tzinfo=None)
                    invoice.l10n_mx_edi_post_time = previous_send_time
                    with self.with_mocked_pac_sign_success():
                        invoice._l10n_mx_edi_cfdi_invoice_try_send()
                    document = invoice.l10n_mx_edi_invoice_document_ids.filtered(lambda x: x.state == 'invoice_sent')[:1]
                    assert_cfdi_date(document, tz, expected_datetime=previous_send_time)

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

    def test_invoice_negative_lines_cfdi_amounts(self):
        """ Ensure the base amounts are correct in CFDI xml after dispatching the negative lines. """
        product1 = self._create_product(name='product_1')
        product2 = self._create_product(name='product_2')
        product3 = self._create_product(name='product_3')
        downpayment = self._create_product(name='down_payment')
        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(
                invoice_line_ids=[
                    Command.create({
                        'product_id': product1.id,
                        'price_unit': 1000.0,
                        'quantity': 1.0,
                    }),
                    Command.create({
                        'product_id': product2.id,
                        'price_unit': 1500.0,
                        'quantity': 1.0,
                    }),
                    Command.create({
                        'product_id': product3.id,
                        'price_unit': 3000.0,
                        'quantity': 1.0,
                    }),
                    Command.create({
                        'product_id': downpayment.id,
                        'price_unit': 4950.0,   # It represents a 90% down payment
                        'quantity': -1.0,
                    }),
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            # The down payment line should be dispatched to the 3 other lines, removing the 2
            # biggest ones and generating a discount of 450 on the lowest one
            self._assert_invoice_cfdi(invoice, 'test_invoice_negative_lines_cfdi_amounts')

    def test_vendor_bill_payment_production_sign_flow_cancel_from_the_sat(self):
        """ Test the case where the vendor bill is manually canceled from the SAT portal by the user (production environment). """
        self.env.company.l10n_mx_edi_pac_test_env = False
        self.env.company.l10n_mx_edi_pac_username = 'test'
        self.env.company.l10n_mx_edi_pac_password = 'test'

        file_name = "test_import_bill"
        full_file_path = misc.file_path(f'{self.test_module}/tests/test_files/{file_name}.xml')
        self.env.company.partner_id.company_id = self.env.company
        with file_open(full_file_path, "rb") as file:
            file_content = file.read()
        new_bill = self._upload_document_on_journal(
            journal=self.company_data['default_journal_purchase'],
            content=file_content,
            filename=file_name,
        )

        # Not checking bill values since they are already checked in a different test, only SAT
        self.assertEqual(new_bill.l10n_mx_edi_invoice_document_ids.state, 'invoice_received')
        new_bill.action_post()
        self.assertTrue(new_bill.l10n_mx_edi_update_sat_needed)
        with self.with_mocked_sat_call(lambda _x: 'valid'):
            new_bill.l10n_mx_edi_cfdi_try_sat()
        self.assertTrue(new_bill.l10n_mx_edi_update_sat_needed)

        # Manual cancellation from the SAT portal
        with self.with_mocked_sat_call(lambda _x: 'cancelled'):
            new_bill.l10n_mx_edi_cfdi_try_sat()

        inv_cancel_doc_values = {
            'move_id': new_bill.id,
            'state': 'invoice_cancel',
            'sat_state': 'cancelled',
        }
        inv_sent_doc_values = {
            'move_id': new_bill.id,
            'state': 'invoice_received',
            'sat_state': 'valid',
        }
        self.assertRecordValues(new_bill.l10n_mx_edi_invoice_document_ids.sorted(), [
            inv_cancel_doc_values,
            inv_sent_doc_values,
        ])
        self.assertRecordValues(new_bill, [{
            'state': 'cancel',
            'need_cancel_request': False,
            'show_reset_to_draft_button': True,
            'l10n_mx_edi_update_sat_needed': False,
            'l10n_mx_edi_cfdi_sat_state': 'cancelled',
            'l10n_mx_edi_cfdi_state': 'cancel',
        }])

    def test_cfdi_to_public_credit_note_g02_usage(self):
        with self.mx_external_setup(self.frozen_today):
            credit_note = self._create_invoice(
                move_type='out_refund',
                l10n_mx_edi_cfdi_to_public=True,
                l10n_mx_edi_usage='G02',
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 500.0,
                    }),
                ],
            )
            with self.with_mocked_pac_sign_success():
                credit_note._l10n_mx_edi_cfdi_invoice_try_send()

            document = credit_note.l10n_mx_edi_invoice_document_ids.filtered(lambda x: x.state == 'invoice_sent')
            cfdi_infos = self.env['l10n_mx_edi.document']._decode_cfdi_attachment(document.attachment_id.raw)
            self.assertEqual(cfdi_infos['usage'], 'G02')

    def test_extra_invoice_report_values(self):
        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(invoice_date_due=self.frozen_today + relativedelta(months=1))
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            report_values = invoice._l10n_mx_edi_get_extra_invoice_report_values()
            self.assertEqual(report_values['payment_method'], 'PPD')
            self.assertEqual(report_values['payment_way'], '99 - Por definir')

    def test_cfdi_future_payment(self):
        """
        Ensure the l10n_mx_edi_update_payments_needed field is False
        when having only payments in the future. It means that the 'Update Payments'
        button will be invisible in the view.
        """
        with self.mx_external_setup(self.frozen_today):
            # Create a PDD invoice
            invoice = self._create_invoice(
                invoice_date_due=self.frozen_today + relativedelta(months=1, days=1),
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'quantity': 1.0,
                    }),
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()

            # create a payment in the future
            self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
                'amount': invoice.amount_total / 2,
                'payment_date': self.frozen_today + relativedelta(days=1)
            })._create_payments()

            self.assertFalse(invoice.l10n_mx_edi_update_payments_needed)

            # create a payment today
            self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
                'payment_date': self.frozen_today
            })._create_payments()

            invoice.invalidate_recordset(['l10n_mx_edi_update_payments_needed'])
            self.assertTrue(invoice.l10n_mx_edi_update_payments_needed)
