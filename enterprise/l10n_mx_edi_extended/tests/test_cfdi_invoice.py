# -*- coding: utf-8 -*-
from .common import TestMxExtendedEdiCommon
from odoo import Command
from odoo.addons.l10n_mx_edi.tests.common import EXTERNAL_MODE, RATE_WITH_USD, TEST_RATE_WITH_USD
from odoo.tests import tagged
from odoo.exceptions import ValidationError


@tagged('post_install_l10n', 'post_install', '-at_install', *(['-standard', 'external'] if EXTERNAL_MODE else []))
class TestCFDIInvoice(TestMxExtendedEdiCommon):

    def test_invoice_external_trade(self):
        chf = self.setup_other_currency('CHF', rates=[(self.frozen_today, 17.0)])

        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(
                l10n_mx_edi_external_trade_type='02',
                currency_id=chf.id,
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 17000.0,
                        'quantity': 5,
                        'discount': 20.0,
                        'l10n_mx_edi_qty_umt': 5.0,
                        'l10n_mx_edi_price_unit_umt': self.product.lst_price,
                        'tax_ids': [Command.set(self.tax_0.ids)],
                    }),
                ],
            )
            # The format of the customs number is incorrect.
            with self.assertRaises(ValidationError):
                invoice.invoice_line_ids.l10n_mx_edi_customs_number = '15  48  30  001234'

            invoice.invoice_line_ids.l10n_mx_edi_customs_number = '15  48  3009  0001234,15  48  3009  0001235'
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()

            if RATE_WITH_USD == TEST_RATE_WITH_USD or not EXTERNAL_MODE:
                self._assert_invoice_cfdi(invoice, 'test_invoice_external_trade')

    def test_invoice_external_trade_delivery_address(self):
        chf = self.setup_other_currency('CHF', rates=[(self.frozen_today, 17.0)])

        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(
                l10n_mx_edi_external_trade_type='02',
                currency_id=chf.id,
                partner_shipping_id=self.partner_us.id,
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 2000.0,
                        'quantity': 5,
                        'discount': 20.0,
                        'l10n_mx_edi_qty_umt': 5.0,
                        'l10n_mx_edi_price_unit_umt': self.product.lst_price,
                        'tax_ids': [Command.set(self.tax_0.ids)],
                    }),
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()

            if RATE_WITH_USD == TEST_RATE_WITH_USD or not EXTERNAL_MODE:
                self._assert_invoice_cfdi(invoice, 'test_invoice_external_trade_delivery_address')

    def test_invoice_external_trade_two_lines_same_product(self):
        """
        Check that the unit price (ValorUnitarioAduana) is well calculated in case
        of having two lines with same product but different price and/or quantity.
        """
        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(
                l10n_mx_edi_external_trade_type='02',
                currency_id=self.usd.id,
                partner_shipping_id=self.partner_us.id,
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 2000.0,
                        'quantity': 3,
                        'l10n_mx_edi_qty_umt': 3.0,
                        'l10n_mx_edi_price_unit_umt': 2000.0,
                        'tax_ids': [Command.set(self.tax_0.ids)],
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 4000.0,
                        'quantity': 5,
                        'l10n_mx_edi_qty_umt': 5.0,
                        'l10n_mx_edi_price_unit_umt': 4000.0,
                        'tax_ids': [Command.set(self.tax_0.ids)],
                    }),
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()

            if RATE_WITH_USD == TEST_RATE_WITH_USD or not EXTERNAL_MODE:
                self._assert_invoice_cfdi(invoice, 'test_invoice_external_trade_two_lines_same_product')

    def test_invoice_external_trade_more_digits(self):
        self.env.ref('product.decimal_price').digits = 6
        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(
                l10n_mx_edi_external_trade_type='02',
                currency_id=self.usd.id,
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 3114.515000,
                        'quantity': 1,
                        'l10n_mx_edi_qty_umt': 11.0,
                        'l10n_mx_edi_price_unit_umt': 283.137727,
                        'tax_ids': [Command.set(self.tax_0.ids)],
                    }),
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()

            if RATE_WITH_USD == TEST_RATE_WITH_USD or not EXTERNAL_MODE:
                self._assert_invoice_cfdi(invoice, 'test_invoice_external_trade_more_digits')

    def test_invoice_external_trade_null_qty(self):
        chf = self.setup_other_currency('CHF', rates=[(self.frozen_today, 17.0)])

        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(
                l10n_mx_edi_external_trade_type='02',
                currency_id=chf.id,
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 17000.0,
                        'quantity': 5,
                        'discount': 20.0,
                        'l10n_mx_edi_qty_umt': 0.0,
                        'l10n_mx_edi_price_unit_umt': self.product.lst_price,
                        'tax_ids': [Command.set(self.tax_0.ids)],
                    }),
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()

            if RATE_WITH_USD == TEST_RATE_WITH_USD or not EXTERNAL_MODE:
                self._assert_invoice_cfdi(invoice, 'test_invoice_external_trade_null_qty')

    def test_global_invoice_with_issued_address_on_journal(self):
        branch_address = self.env['res.partner'].create({
            'name': 'Sucursal Mexico City',
            'street': 'Paseo de la Reforma 222',
            'zip': '06600',
            'city': 'Cuauhtémoc',
            'state_id': self.env.ref('base.state_mx_mex').id,
            'country_id': self.env.ref('base.mx').id,
            'type': 'other',
        })

        with self.mx_external_setup(self.frozen_today):
            invoice = self._create_invoice(
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 17000.0,
                        'quantity': 5,
                        'discount': 20.0,
                        'l10n_mx_edi_qty_umt': 0.0,
                        'l10n_mx_edi_price_unit_umt': self.product.lst_price,
                        'tax_ids': [Command.set(self.tax_0.ids)],
                    }),
                ],
            )
            invoice.journal_id.l10n_mx_address_issued_id = branch_address

            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_global_invoice_try_send()

            self._assert_global_invoice_cfdi_from_invoices(invoice, "test_global_invoice_with_issued_address_on_journal")
