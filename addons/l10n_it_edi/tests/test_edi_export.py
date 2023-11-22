# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged
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
            'price_include': True,
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

        expected = ['Alessi must have a street.', 'Alessi must have a country.', 'Alessi must have a post code.', 'Alessi must have a city.']
        actual = invoice._l10n_it_edi_export_data_check()
        self.assertEqual(expected, actual)

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
        expected = ['Alessi must have a street.', 'Alessi must have a post code.', 'Alessi must have a city.']
        actual = invoice._l10n_it_edi_export_data_check()
        self.assertEqual(expected, actual)

    def test_invoice_zero_percent_taxes(self):
        tax_zero_percent_hundred_percent_repartition = self.env['account.tax'].with_company(self.company).create({
            'name': 'all of nothing',
            'amount': 0.0,
            'amount_type': 'percent',
            'l10n_it_exempt_reason': 'N1',
            'l10n_it_law_reference': 'test',
        })

        tax_zero_percent_zero_percent_repartition = self.env['account.tax'].with_company(self.company).create({
            'name': 'none of nothing',
            'amount': 0,
            'amount_type': 'percent',
            'l10n_it_exempt_reason': 'N1',
            'l10n_it_law_reference': 'test',
            'invoice_repartition_line_ids': [
                Command.create({'factor_percent': 100, 'repartition_type': 'base'}),
                Command.create({'factor_percent': 0, 'repartition_type': 'tax'}),
            ],
            'refund_repartition_line_ids': [
                Command.create({'factor_percent': 100, 'repartition_type': 'base'}),
                Command.create({'factor_percent': 0, 'repartition_type': 'tax'}),
            ],
        })

        invoice = self.env['account.move'].with_company(self.company).create({
            'move_type': 'out_invoice',
            'invoice_date': '2022-03-24',
            'invoice_date_due': '2022-03-24',
            'partner_id': self.italian_partner_a.id,
            'partner_bank_id': self.test_bank.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'line with tax of 0% with repartition line of 100% ',
                    'price_unit': 800.40,
                    'tax_ids': [Command.set(tax_zero_percent_hundred_percent_repartition.ids)],
                }),
                Command.create({
                    'name': 'line with tax of 0% with repartition line of 0% ',
                    'price_unit': 800.40,
                    'tax_ids': [Command.set(tax_zero_percent_zero_percent_repartition.ids)],
                }),
            ],
        })
        invoice.action_post()
        self._assert_export_invoice(invoice, 'invoice_zero_percent_taxes.xml')

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
                    'price_unit': 800.40,
                    'tax_ids': [Command.set(self.default_tax.ids)],
                }),
                Command.create({
                    'name': 'negative_line',
                    'price_unit': -100.0,
                    'tax_ids': [Command.set(self.default_tax.ids)],
                }),
                Command.create({
                    'name': 'negative_line_different_tax',
                    'price_unit': -50.0,
                    'tax_ids': [Command.set(tax_10.ids)],
                    }),
            ],
        })
        invoice.action_post()

        with self.subTest('invoice'):
            self._assert_export_invoice(invoice, 'invoice_negative_price.xml')

        credit_note = invoice._reverse_moves([{
            'invoice_date': '2022-03-24',
        }])

        with self.subTest('credit note'):
            self._assert_export_invoice(credit_note, 'credit_note_negative_price.xml')
