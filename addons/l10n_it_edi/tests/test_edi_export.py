# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import freeze_time, tagged
from odoo.addons.l10n_it_edi.tests.common import TestItEdi


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItEdiExport(TestItEdi):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.italian_partner_b = cls.env['res.partner'].create({
            'name': 'pa partner',
            'vat': 'IT06655971007',
            'l10n_it_codice_fiscale': '06655971007',
            'l10n_it_pa_index': '123456',
            'country_id': cls.env.ref('base.it').id,
            'street': 'Via Test PA',
            'zip': '32121',
            'city': 'PA Town',
            'is_company': True
        })

        cls.italian_partner_no_address_codice = cls.env['res.partner'].create({
            'name': 'Alessi',
            'l10n_it_codice_fiscale': '00465840031',
            'is_company': True,
        })

        cls.italian_partner_no_address_VAT = cls.env['res.partner'].create({
            'name': 'Alessi',
            'vat': 'IT00465840031',
            'is_company': True,
        })

        cls.american_partner = cls.env['res.partner'].create({
            'name': 'Alessi',
            'vat': '00465840031',
            'country_id': cls.env.ref('base.us').id,
            'is_company': True,
        })

    def test_vat_not_equals_codice(self):
        self.company.partner_id.vat = '01698911003'
        self.company.l10n_it_codice_fiscale = '07149930583'

        invoice = self.env['account.move'].with_company(self.company).create({
            'move_type': 'out_invoice',
            'invoice_date': '2022-03-24',
            'invoice_date_due': '2022-03-24',
            'partner_id': self.italian_partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'line1',
                    'price_unit': 800.40,
                    'tax_ids': [Command.set(self.default_tax.ids)],
                }),
            ],
        })
        invoice.action_post()
        self._assert_export_invoice(invoice, 'invoice_vat_not_equals_codice.xml')

    def test_export_invoice_price_included_taxes(self):
        """ When the tax is price included, there should be a rounding value added to the xml, if the
        sum(subtotals) * tax_rate is not equal to taxable base * tax rate (there is a constraint in the edi where
        taxable base * tax rate = tax amount, but also taxable base = sum(subtotals) + rounding amount).
        """
        tax_included = self.env['account.tax'].with_company(self.company).create({
            'name': "22% price included tax",
            'amount': 22.0,
            'amount_type': 'percent',
            'price_include_override': 'tax_included',
        })

        invoice = self.env['account.move'].with_company(self.company).create({
            'move_type': 'out_invoice',
            'invoice_date': '2022-03-24',
            'invoice_date_due': '2022-03-24',
            'partner_id': self.italian_partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': "something price included",
                    'price_unit': 800.40,
                    'tax_ids': [Command.set(tax_included.ids)],
                }),
                Command.create({
                    'name': "something else price included",
                    'price_unit': 800.40,
                    'tax_ids': [Command.set(tax_included.ids)],
                }),
                Command.create({
                    'name': "something not price included",
                    'price_unit': 800.40,
                    'tax_ids': [Command.set(self.default_tax.ids)],
                }),
            ],
        })
        invoice.action_post()
        self._assert_export_invoice(invoice, 'invoice_price_included_taxes.xml')

    def test_export_invoice_partially_discounted(self):
        invoice = self.env['account.move'].with_company(self.company).create({
            'move_type': 'out_invoice',
            'invoice_date': '2022-03-24',
            'invoice_date_due': '2022-03-24',
            'partner_id': self.italian_partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'no discount',
                    'price_unit': 800.40,
                    'tax_ids': [Command.set(self.default_tax.ids)],
                }),
                Command.create({
                    'name': 'special discount',
                    'price_unit': 800.40,
                    'discount': 50,
                    'tax_ids': [Command.set(self.default_tax.ids)],
                }),
                Command.create({
                    'name': "an offer you can't refuse",
                    'price_unit': 800.40,
                    'discount': 100,
                    'tax_ids': [Command.set(self.default_tax.ids)],
                }),
            ],
        })
        invoice.action_post()
        self._assert_export_invoice(invoice, 'invoice_partially_discounted.xml')

    def test_invoice_fully_discounted(self):
        invoice = self.env['account.move'].with_company(self.company).create({
            'move_type': 'out_invoice',
            'invoice_date': '2022-03-24',
            'invoice_date_due': '2022-03-24',
            'partner_id': self.italian_partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'nothing shady just a gift for my friend',
                    'price_unit': 800.40,
                    'discount': 100,
                    'tax_ids': [Command.set(self.default_tax.ids)],
                }),
            ],
        })
        invoice.action_post()
        self._assert_export_invoice(invoice, 'invoice_fully_discounted.xml')

    def test_invoice_non_latin_and_latin(self):
        invoice = self.env['account.move'].with_company(self.company).create({
            'move_type': 'out_invoice',
            'invoice_date': '2022-03-24',
            'invoice_date_due': '2022-03-24',
            'partner_id': self.italian_partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'ʢ◉ᴥ◉ʡ',
                    'price_unit': 800.40,
                    'tax_ids': [Command.set(self.default_tax.ids)],
                }),
                Command.create({
                    'name': '--',
                    'price_unit': 800.40,
                    'tax_ids': [Command.set(self.default_tax.ids)],
                }),
                Command.create({
                    'name': 'this should be the same as it was',
                    'price_unit': 800.40,
                    'tax_ids': [Command.set(self.default_tax.ids)],
                }),
            ],
        })
        invoice.action_post()
        self._assert_export_invoice(invoice, 'invoice_non_latin_and_latin.xml')

    def test_invoice_below_400_codice_simplified(self):
        invoice = self.env['account.move'].with_company(self.company).create({
            'move_type': 'out_invoice',
            'invoice_date': '2022-03-24',
            'invoice_date_due': '2022-03-24',
            'partner_id': self.italian_partner_no_address_codice.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'cheap_line',
                    'price_unit': 100.00,
                    'tax_ids': [Command.set(self.default_tax.ids)],
                }),
                Command.create({
                    'name': 'cheap_line_2',
                    'quantity': 2,
                    'price_unit': 10.0,
                    'tax_ids': [Command.set(self.default_tax.ids)],
                }),
            ],
        })
        invoice.action_post()
        self._assert_export_invoice(invoice, 'invoice_below_400_codice_simplified.xml')

    def test_invoice_total_400_VAT_simplified(self):
        self.company.l10n_it_codice_fiscale = '07149930583'
        invoice = self.env['account.move'].with_company(self.company).create({
            'move_type': 'out_invoice',
            'invoice_date': '2022-03-24',
            'invoice_date_due': '2022-03-24',
            'partner_id': self.italian_partner_no_address_VAT.id,
            'invoice_line_ids': [
                Command.create({
                    'name': '400_line',
                    'price_unit': 327.87,
                    'tax_ids': [Command.set(self.default_tax.ids)],
                }),
            ],
        })
        invoice.action_post()
        self._assert_export_invoice(invoice, 'invoice_total_400_VAT_simplified.xml')

    def test_invoice_more_400_simplified(self):
        invoice = self.env['account.move'].with_company(self.company).create({
            'move_type': 'out_invoice',
            'invoice_date': '2022-03-24',
            'invoice_date_due': '2022-03-24',
            'partner_id': self.italian_partner_no_address_codice.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'standard_line',
                    'price_unit': 800.40,
                    'tax_ids': [Command.set(self.default_tax.ids)],
                }),
            ],
        })
        self.assertEqual(['l10n_it_edi_partner_address_missing'], list(invoice._l10n_it_edi_export_data_check().keys()))

    def test_invoice_non_domestic_simplified(self):
        invoice = self.env['account.move'].with_company(self.company).create({
            'move_type': 'out_invoice',
            'invoice_date': '2022-03-24',
            'invoice_date_due': '2022-03-24',
            'partner_id': self.american_partner.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'cheap_line',
                    'price_unit': 100.00,
                    'tax_ids': [Command.set(self.default_tax.ids)],
                }),
            ],
        })
        self.assertEqual(['l10n_it_edi_partner_address_missing'], list(invoice._l10n_it_edi_export_data_check().keys()))

    def test_bill_refund_no_reconcile(self):
        Move = self.env['account.move'].with_company(self.company)
        purchase_tax = self.env['account.tax'].with_company(self.company).create({
            'name': 'Tax 4%',
            'amount': 4.0,
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'invoice_repartition_line_ids': self.repartition_lines(
                self.RepartitionLine(100, 'base', ('+03', )),
                self.RepartitionLine(100, 'tax', ('+5v', ))),
            'refund_repartition_line_ids': self.repartition_lines(
                self.RepartitionLine(100, 'base', ('-03', )),
                self.RepartitionLine(100, 'tax', False))
        })
        values = {
            'invoice_date': '2022-03-24',
            'invoice_date_due': '2022-03-24',
            'partner_id': self.italian_partner_a.id,
            'partner_bank_id': self.test_bank.id,
            'invoice_line_ids': [
                Command.create({
                    'name': "Product A",
                    'price_unit': 800.40,
                    'tax_ids': [Command.set(purchase_tax.ids)],
                })
            ]
        }

        bill = Move.create({'move_type': 'in_invoice', **values})
        credit_note = Move.create({'move_type': 'in_refund', **values})
        (bill + credit_note).action_post()
        credit_note.reversed_entry_id = bill
        self._assert_export_invoice(credit_note, 'credit_note_refund_no_reconcile.xml')

    def test_invoice_negative_price(self):
        tax_10 = self.env['account.tax'].create({
            'name': '10% tax',
            'amount': 10.0,
            'amount_type': 'percent',
            'company_id': self.company.id,
        })

        invoice = self.env['account.move'].with_company(self.company).create({
            'move_type': 'out_invoice',
            'invoice_date': '2022-03-24',
            'invoice_date_due': '2022-03-24',
            'partner_id': self.italian_partner_a.id,
            'partner_bank_id': self.test_bank.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'standard_line',
                    'quantity': 2,
                    'price_unit': 800.40,
                    'tax_ids': [Command.set(self.default_tax.ids)],
                }),
                Command.create({
                    'name': 'negative_line',
                    'price_unit': -100.0,
                    'tax_ids': [Command.set(self.default_tax.ids)],
                }),
            ],
        })
        invoice.action_post()

        with self.subTest('invoice'):
            self._assert_export_invoice(invoice, 'invoice_negative_price.xml')

        credit_note = invoice._reverse_moves([{
            'invoice_date': '2022-03-24',
        }])
        credit_note.action_post()

        with self.subTest('credit note'):
            self._assert_export_invoice(credit_note, 'credit_note_negative_price.xml')

    def test_invoice_more_decimal_price_unit(self):
        decimal_precision_name = self.env['account.move.line']._fields['price_unit']._digits
        decimal_precision = self.env['decimal.precision'].search([('name', '=', decimal_precision_name)])
        decimal_precision.digits = 4
        invoice = self.env['account.move'].with_company(self.company).create({
            'move_type': 'out_invoice',
            'invoice_date': '2022-03-24',
            'invoice_date_due': '2022-03-24',
            'partner_id': self.italian_partner_a.id,
            'partner_bank_id': self.test_bank.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'standard_line',
                    'price_unit': 3.156,
                    'quantity': 10,
                    'tax_ids': [Command.set(self.default_tax.ids)],
                }),
            ],
        })
        invoice.action_post()

        self._assert_export_invoice(invoice, 'invoice_decimal_precision_product.xml')

    def test_send_and_print_invoice_with_fallback_pdf(self):
        self.italian_partner_a.zip = False  # invalid configuration for partner -> proforma pdf
        invoice = self.env['account.move'].with_company(self.company).create({
            'partner_id': self.italian_partner_a.id,
            'invoice_date': '2024-03-24',
            'move_type': 'out_invoice',
            'invoice_line_ids': [
                Command.create({
                    'name': 'Example Product',
                    'price_unit': 500,
                    'tax_ids': [Command.set(self.default_tax.ids)],
                }),
            ],
        })
        invoice.action_post()
        invoice._generate_and_send()
        self.assertIn(
            'INV_2024_00001_proforma.pdf',
            invoice.attachment_ids.mapped('name'),
            "The proforma PDF should have been generated.",
        )

    def test_export_foreign_currency(self):

        tax_zero_percent_us = self.env['account.tax'].with_company(self.company).create({
            'name': '0 % US',
            'amount': 0.0,
            'amount_type': 'percent',
            'l10n_it_exempt_reason': 'N3.1',
            'l10n_it_law_reference': 'Art. 8, c.1, lett.a - D.P.R. 633/1972',
        })

        american_partner_b = self.env['res.partner'].create({
            'name': 'US Partner',
            'city': 'Test city',
            'country_id': self.env.ref('base.us').id,
            'zip': '12345',
            'street': '123 Rainbow Road',
            'is_company': True,
        })

        # =============== create invoices ===============
        usd = self.env.ref('base.USD')

        self.env['res.currency.rate'].create({
            'name': '2024-08-06',
            'rate': 1.0789,
            'currency_id': usd.id,
            'company_id': self.company.id,
        })

        # usd simple discount % on the product
        invoice = self.env['account.move'].with_company(self.company).create({
            'move_type': 'out_invoice',
            'invoice_date': '2024-08-07',
            'invoice_date_due': '2024-08-07',
            'partner_id': american_partner_b.id,
            'currency_id': usd.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'A productive product',
                    'price_unit': 1068.11,
                    'quantity': 1,
                    'tax_ids': [Command.set(tax_zero_percent_us.ids)],
                    'discount': 15,
                }),
            ],
        })
        invoice.action_post()
        self._assert_export_invoice(invoice, 'export_foreign_currency_simple_discount.xml')

        # usd discount both on product in % + a global one (negative aml)
        invoice = self.env['account.move'].with_company(self.company).create({
            'move_type': 'out_invoice',
            'invoice_date': '2024-08-06',
            'invoice_date_due': '2024-08-06',
            'partner_id': american_partner_b.id,
            'currency_id': usd.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'A productive product',
                    'price_unit': 712.07,
                    'quantity': 1,
                    'tax_ids': [Command.set(tax_zero_percent_us.ids)],
                    'discount': 15,
                }),
                Command.create({
                    'name': 'A global discount',
                    'price_unit': -100,
                    'quantity': 1,
                    'tax_ids': [Command.set(tax_zero_percent_us.ids)],
                }),
            ],
        })
        invoice.action_post()
        self._assert_export_invoice(invoice, 'export_foreign_currency_global_simple_discount.xml')

        # usd discount global (negative aml)
        invoice = self.env['account.move'].with_company(self.company).create({
            'move_type': 'out_invoice',
            'invoice_date': '2024-08-07',
            'invoice_date_due': '2024-08-07',
            'partner_id': american_partner_b.id,
            'currency_id': usd.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'A productive product',
                    'price_unit': 712.07,
                    'quantity': 1,
                    'tax_ids': [Command.set(tax_zero_percent_us.ids)],
                }),
                Command.create({
                    'name': 'A global discount',
                    'price_unit': -200,
                    'quantity': 1,
                    'tax_ids': [Command.set(tax_zero_percent_us.ids)],
                }),
            ],
        })
        invoice.action_post()
        self._assert_export_invoice(invoice, 'export_foreign_currency_global_discount.xml')

    @freeze_time("2025-02-03")
    def test_export_invoice_with_two_downpayments(self):
        if self.env['ir.module.module']._get('sale').state != 'installed':
            self.skipTest("sale module is not installed")

        sale_order = self.env['sale.order'].with_company(self.company).create({
            'partner_id': self.italian_partner_a.id,
            'order_line': [
                Command.create({'product_id': self.service_product.id, 'price_unit': 200.00}),
            ],
        })
        sale_order.action_confirm()

        for amount in (50, 100):
            self.env['account.move'].with_company(self.company).browse(
                self.env['sale.advance.payment.inv'].create([{
                    'advance_payment_method': 'fixed',
                    'fixed_amount': amount,
                    'sale_order_ids': [Command.link(sale_order.id)],
                }]).create_invoices()['res_id']
            ).action_post()

        invoice = self.env['account.move'].with_company(self.company).browse(
            self.env['sale.advance.payment.inv'].create([{
                'advance_payment_method': 'delivered',
                'sale_order_ids': [Command.link(sale_order.id)],
            }]).create_invoices()['res_id']
        )
        invoice.action_post()
        self._assert_export_invoice(invoice, 'test_export_invoice_with_two_downpayments.xml')

    @freeze_time('2025-03-07')
    def test_send_prezzo_unitario_converted_to_company_currency(self):
        """
        Test that the prezzo unitario is converted to the company currency when the invoice is in a foreign currency
        """
        usd = self.env.ref('base.USD')
        self.env['res.currency.rate'].create({
            'name': '2025-01-01',
            'rate': 1.54639273,
            'currency_id': usd.id,
            'company_id': self.company.id,
        })

        invoice = self.init_invoice(
            move_type='out_invoice',
            partner=self.italian_partner_a,
            invoice_date='2025-02-24',
            post=True,
            amounts=[100],
            taxes=[self.default_tax],
            company=self.company,
            currency=usd,
        )

        self._assert_export_invoice(invoice, 'prezzio_unitario_converted_company_currency.xml')

    def test_export_XML_lowercase_fields(self):
        partner = self.env['res.partner'].create({
            'name': 'Alessi',
            'l10n_it_codice_fiscale': 'Mrtmtt91d08f205j',
            'l10n_it_pa_index': 'N8mimm9',
            'is_company': False,
        })

        invoice = self.env['account.move'].with_company(self.company).create({
            'move_type': 'out_invoice',
            'invoice_date': '2022-03-24',
            'invoice_date_due': '2022-03-24',
            'partner_id': partner.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'line1',
                    'price_unit': 800.40,
                    'tax_ids': [Command.set(self.default_tax.ids)],
                }),
            ],
        })
        invoice.action_post()
        self._assert_export_invoice(invoice, 'invoice_lowercase_fields.xml')

    def test_export_invoice_with_rounding_lines_value(self):
        """Test that invoices with rounding lines are correctly exported with exempt tax 'N2.2'."""
        self.env['res.config.settings'].create({
            'company_id': self.company.id,
            'group_cash_rounding': True
        })

        cash_rounding_add_invoice_line = self.env['account.cash.rounding'].with_company(self.company).create({
            'name': 'Rounding to 0.05',
            'rounding': 0.05,
            'strategy': 'add_invoice_line',
            'profit_account_id': self.company_data_2['default_account_revenue'].id,
            'loss_account_id': self.company_data_2['default_account_expense'].id,
            'rounding_method': 'HALF-UP',
        })

        invoice = self.env['account.move'].with_company(self.company).create({
            'move_type': 'out_invoice',
            'partner_id': self.italian_partner_a.id,
            'invoice_date': '2022-03-24',
            'invoice_date_due': '2022-03-24',
            'invoice_cash_rounding_id': cash_rounding_add_invoice_line.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'standard_line',
                    'price_unit': 100.02,
                    'tax_ids': [Command.set(self.default_tax.ids)],
                }),
            ]
        })
        invoice.action_post()

        self._assert_export_invoice(invoice, 'invoice_with_rounding_line.xml')
