from odoo import Command
from odoo.tests import tagged
from odoo.tools.float_utils import float_compare, float_round
from odoo.addons.l10n_jo_edi.tests.jo_edi_common import JoEdiCommon
from odoo.addons.l10n_jo_edi.models.account_edi_xml_ubl_21_jo import JO_MAX_DP


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestJoEdiPrecision(JoEdiCommon):
    def _equality_check(self, vals_dict, up_to_jo_max_dp=True):
        def equal_strict(val1, val2):
            return val1 == val2

        def equal_jo_max_dp(val1, val2):
            return float_compare(val1, val2, JO_MAX_DP) == 0

        equals = equal_jo_max_dp if up_to_jo_max_dp else equal_strict
        first_tuple = None
        error_message = ""
        for label, value in vals_dict.items():
            if not first_tuple:
                first_tuple = (label, value)
            else:
                if not equals(value, first_tuple[1]):
                    error_message += f"{label} ({value}) != {first_tuple[0]} ({first_tuple[1]})\n"
        return error_message

    def _extract_vals_from_subtotals(self, subtotals, defaults):
        for subtotal in subtotals:
            tax_percent = float(subtotal.findtext('{*}TaxCategory/{*}Percent', default=-1))
            if tax_percent == -1:  # special (fixed amount) tax
                defaults.update({
                    'taxable_amount_special': float(subtotal.findtext('{*}TaxableAmount')),
                    'tax_amount_special': float(subtotal.findtext('{*}TaxAmount')),
                })
                defaults['total_tax_amount'] += defaults['tax_amount_special']
            else:
                defaults.update({
                    'taxable_amount_general': float(subtotal.findtext('{*}TaxableAmount')),
                    'tax_amount_general_subtotal': float(subtotal.findtext('{*}TaxAmount')),
                    'tax_percent': tax_percent / 100,
                })
                defaults['total_tax_amount'] += defaults['tax_amount_general_subtotal']

        return defaults

    def _round_max_dp(self, value):
        return float_round(value, JO_MAX_DP)

    def _validate_jo_edi_numbers(self, xml_string, invoice):
        """
        TLDR: This method checks that units sum up to total values.
        ===================================================================================================
        Problem statement:
        When an EDI is submitted to JoFotara portal, multiple validations are executed to ensure invoice data integrity.
        The most important ones of these validations are the following:-
        --------------------------- ▼ invoice line level ▼  ---------------------------
        1. line_extension_amount = (price_unit * quantity) - discount
        2. taxable_amount = line_extension_amount
        3. rounding_amount = line_extension_amount + general_tax_amount + special_tax_amount
        --------------------------- ▼ invoice level ▼ ---------------------------------
        4. tax_exclusive_amount = sum(price_unit * quantity)
        5. tax_inclusive_amount = sum(price_unit * quantity - discount + general_tax_amount + special_tax_amount)
        6. payable_amount = tax_inclusive_amount
        -------------------------------------------------------------------------------
        The JoFotara portal, however, has no tolerance with rounding errors up to 9 decimal places.
        Hence, the reported values are expected to be up to 9 decimal places,
        and the aggregated units should match reported totals up to 9 decimal places.
        Moreover, reported totals have to equal (or at least be as close as possible) to totals stored in Odoo.
        And since the JOD has precision of 3 decimal places, everything is stored in Odoo approximated to 3 decimal places.
        -------------------------------------------------------------------------------
        This method runs validations in a fashion similar to those running on the JoFotara portal.
        It returns all the errors encountered as a string.
        """
        root = self.get_xml_tree_from_string(xml_string)
        error_message = ""

        total_discount = float(root.findtext('./{*}AllowanceCharge/{*}Amount'))
        total_tax = float(root.findtext('./{*}TaxTotal/{*}TaxAmount', default=0))

        tax_exclusive_amount = float(root.findtext('./{*}LegalMonetaryTotal/{*}TaxExclusiveAmount'))
        tax_inclusive_amount = float(root.findtext('./{*}LegalMonetaryTotal/{*}TaxInclusiveAmount'))
        self.assertEqual(float_compare(tax_inclusive_amount, invoice.amount_total, 2), 0, f'{tax_inclusive_amount} != {invoice.amount_total}')
        monetary_values_discount = float(root.findtext('./{*}LegalMonetaryTotal/{*}AllowanceTotalAmount'))
        payable_amount = float(root.findtext('./{*}LegalMonetaryTotal/{*}PayableAmount'))

        error_message += self._equality_check({  # They have to be exactly the same, no decimal difference is tolerated
            'Monetary Values discount': monetary_values_discount,
            'Total Discount': total_discount,
        }, up_to_jo_max_dp=False)
        error_message += self._equality_check({  # They have to be exactly the same, no decimal difference is tolerated
            'Payable Amount': payable_amount,
            'Tax Inclusive Amount': tax_inclusive_amount,
        }, up_to_jo_max_dp=False)

        lines = []
        for xml_line in root.findall('./{*}InvoiceLine'):
            line_extension_amount = float(xml_line.findtext('{*}LineExtensionAmount'))
            line = {
                'id': xml_line.findtext('{*}ID'),
                'quantity': float(xml_line.findtext('{*}InvoicedQuantity')),
                'line_extension_amount': line_extension_amount,
                'tax_amount_general': float(xml_line.findtext('{*}TaxTotal/{*}TaxAmount', default=0)),
                'rounding_amount': float(xml_line.findtext('{*}TaxTotal/{*}RoundingAmount', default=line_extension_amount)),  # defaults to line_extension_amount in the absence of taxes
                **self._extract_vals_from_subtotals(
                    subtotals=xml_line.findall('{*}TaxTotal/{*}TaxSubtotal'),
                    defaults={
                        'taxable_amount_general': line_extension_amount,
                        'tax_amount_general_subtotal': 0,
                        'tax_percent': 0,
                        'taxable_amount_special': line_extension_amount,
                        'tax_amount_special': 0,
                        'total_tax_amount': 0,
                    }),
                'price_unit': float(xml_line.findtext('{*}Price/{*}PriceAmount')),
                'discount': float(xml_line.findtext('{*}Price/{*}AllowanceCharge/{*}Amount')),
            }
            lines.append(line)
            line_errors = self._equality_check({
                # taxable_amount = line_extension_amount = price_unit * quantity - discount
                'General Taxable Amount': line['taxable_amount_general'],
                'Special Taxable Amount': line['taxable_amount_special'],
                'Line Extension Amount': line['line_extension_amount'],
                'Price Unit * Quantity - Discount': line['price_unit'] * line['quantity'] - line['discount'],
            }) + self._equality_check({
                # rounding_amount = line_extension_amount + total_tax_amount
                'Rounding Amount': line['rounding_amount'],
                'Line Extension Amount + Total Tax': line['line_extension_amount'] + line['total_tax_amount'],
            }) + self._equality_check({
                'General Tax Amount': line['tax_amount_general'],
                'General Tax Amount in subtotal': line['tax_amount_general_subtotal'],
                'Taxable Amount * Tax Percent': (line['taxable_amount_general'] + line['tax_amount_special']) * line['tax_percent'],
            })
            if line_errors:
                error_message += f"Errors on the line {line['id']}\n"
                error_message += line_errors
                error_message += "-------------------------------------------------------------------------\n"

        aggregated_tax_exclusive_amount = sum(self._round_max_dp(line['price_unit'] * line['quantity']) for line in lines)
        aggregated_tax_inclusive_amount = sum(self._round_max_dp(line['price_unit'] * line['quantity'] - line['discount'] + line['total_tax_amount']) for line in lines)
        aggregated_tax_amount = sum(line['tax_amount_general'] for line in lines)
        aggregated_discount_amount = sum(line['discount'] for line in lines)

        error_message += self._equality_check({
            'Tax Exclusive Amount': tax_exclusive_amount,
            'Aggregated Tax Exclusive Amount': aggregated_tax_exclusive_amount,
        }) + self._equality_check({
            'Tax Inclusive Amount': tax_inclusive_amount,
            'Aggregated Tax Inclusive Amount': aggregated_tax_inclusive_amount,
            'Tax Exclusive Amount - Total Discount + Total Tax': tax_exclusive_amount - total_discount + sum(line['total_tax_amount'] for line in lines),
        }) + self._equality_check({
            'Tax Amount': total_tax,
            'Aggregated Tax Amount': aggregated_tax_amount,
        }) + self._equality_check({
            'Discount Amount': total_discount,
            'Aggregated Discount Amount': aggregated_discount_amount,
        })

        return error_message

    def _validate_invoice_vals_jo_edi_numbers(self, invoice_vals):
        with self.subTest(sub_test_name=invoice_vals['name']):
            invoice = self._l10n_jo_create_invoice(invoice_vals)
            generated_file = self.env['account.edi.xml.ubl_21.jo']._export_invoice(invoice)[0]
            errors = self._validate_jo_edi_numbers(generated_file, invoice)
            self.assertFalse(errors, errors)

    def test_jo_sales_invoice_precision(self):
        eur = self.env.ref('base.EUR')
        self.setup_currency_rate(eur, 1.41)
        self.company.l10n_jo_edi_taxpayer_type = 'sales'
        self.company.l10n_jo_edi_sequence_income_source = '16683693'

        self._validate_invoice_vals_jo_edi_numbers({
            'name': 'TestEIN022',
            'currency_id': eur.id,
            'date': '2023-11-12',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 3.48,
                    'price_unit': 1.56,
                    'discount': 2.5,
                    'tax_ids': [Command.set(self.jo_general_tax_16_included.ids)],
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'quantity': 6.02,
                    'price_unit': 2.79,
                    'discount': 2.5,
                    'tax_ids': [Command.set(self.jo_general_tax_16_included.ids)],
                }),
            ],
        })

        self._validate_invoice_vals_jo_edi_numbers({
            'name': 'TestEIN023',
            'date': '2023-11-12',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 5,
                    'price_unit': 206.25,
                    'discount': 12.73,
                    'tax_ids': [Command.set(self.jo_general_tax_16.ids)],
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 5,
                    'price_unit': 195,
                    'discount': 15.39,
                    'tax_ids': [Command.set(self.jo_general_tax_16.ids)],
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 5,
                    'price_unit': 206.25,
                    'discount': 14.55,
                    'tax_ids': [Command.set(self.jo_general_tax_16.ids)],
                }),
            ],
        })

        self._validate_invoice_vals_jo_edi_numbers({
            'name': 'TestEIN024',
            'date': '2023-11-12',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 10,
                    'price_unit': 206.25,
                    'discount': 12.72,
                    'tax_ids': [Command.set(self.jo_general_tax_16.ids)],
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 7,
                    'price_unit': 187.5,
                    'discount': 16,
                    'tax_ids': [Command.set(self.jo_general_tax_16.ids)],
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 10,
                    'price_unit': 66.25,
                    'discount': 8.3,
                    'tax_ids': [Command.set(self.jo_general_tax_16.ids)],
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 6,
                    'price_unit': 33,
                    'discount': 0,
                    'tax_ids': [Command.set(self.jo_general_tax_16.ids)],
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'price_unit': 206.25,
                    'discount': 14.45,
                    'tax_ids': [Command.set(self.jo_general_tax_16.ids)],
                }),
            ],
        })

        self._validate_invoice_vals_jo_edi_numbers({
            'name': 'TestEIN025',
            'date': '2023-11-12',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'price_unit': 3.75,
                    'discount': 25,
                    'tax_ids': [Command.set(self.jo_general_tax_16.ids)],
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 0.2,
                    'price_unit': 13.75,
                    'discount': 25,
                    'tax_ids': [Command.set(self.jo_general_tax_16.ids)],
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 0.5,
                    'price_unit': 5.85,
                    'discount': 25,
                    'tax_ids': [Command.set(self.jo_general_tax_16.ids)],
                }),
            ],
        })

        self._validate_invoice_vals_jo_edi_numbers({
            'name': 'TestEIN026',
            'date': '2023-11-12',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 30,
                    'price_unit': 22.2,
                    'discount': 0,
                    'tax_ids': [Command.set(self.jo_general_tax_16.ids)],
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 3,
                    'price_unit': 22.2,
                    'discount': 100,
                    'tax_ids': [Command.set(self.jo_general_tax_16.ids)],
                }),
            ],
        })

    def test_jo_special_invoice_precision(self):
        self.company.l10n_jo_edi_taxpayer_type = 'special'
        self.company.l10n_jo_edi_sequence_income_source = '16683693'
        self._validate_invoice_vals_jo_edi_numbers({
            'name': 'TestEIN014',
            'invoice_date': '2023-11-10',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_b.id,
                    'price_unit': 100,
                    'quantity': 1,
                    'tax_ids': [Command.set((self.jo_general_tax_10 | self.jo_special_tax_10).ids)],
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100,
                    'quantity': 1,
                    'tax_ids': [Command.set((self.jo_general_tax_10 | self.jo_special_tax_5).ids)],
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100,
                    'quantity': 1,
                    'tax_ids': [Command.set((self.jo_general_tax_16 | self.jo_special_tax_5).ids)],
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'price_unit': 100,
                    'quantity': 1,
                    'tax_ids': [Command.set((self.jo_general_tax_16 | self.jo_special_tax_10).ids)],
                }),
            ],
        })

    def test_jo_credit_notes_price_unit(self):
        def get_price_units(xml_string):
            root = self.get_xml_tree_from_string(xml_string)
            for xml_line in root.findall('./{*}InvoiceLine'):
                yield float(xml_line.findtext('{*}Price/{*}PriceAmount'))
        self.company.l10n_jo_edi_taxpayer_type = 'sales'
        self.company.l10n_jo_edi_sequence_income_source = '16683693'
        invoice = self._l10n_jo_create_invoice({
            'name': 'TestEIN014',
            'invoice_date': '2023-11-10',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_b.id,
                    'price_unit': 11.11,
                    'quantity': 9833,
                    'discount': 3.12,
                    'tax_ids': [Command.set((self.jo_general_tax_16_included).ids)],
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 10000.01,
                    'quantity': 93333,
                    'discount': 99.71,
                    'tax_ids': [Command.set((self.jo_general_tax_16_included).ids)],
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 0.01,
                    'quantity': 0.11,
                    'discount': 2,
                    'tax_ids': [Command.set((self.jo_general_tax_16_included).ids)],
                }),
            ],
        })
        refund = self._l10n_jo_create_refund(invoice, 'return reason', {
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_b.id,
                    'price_unit': 11.11,
                    'quantity': 3.11,
                    'discount': 3.12,
                    'tax_ids': [Command.set((self.jo_general_tax_16_included).ids)],
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 10000.01,
                    'quantity': 2.02,
                    'discount': 99.71,
                    'tax_ids': [Command.set((self.jo_general_tax_16_included).ids)],
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 0.01,
                    'quantity': 0.1,
                    'discount': 2,
                    'tax_ids': [Command.set((self.jo_general_tax_16_included).ids)],
                }),
            ],
        })
        invoice_file = self.env['account.edi.xml.ubl_21.jo']._export_invoice(invoice)[0]
        refund_file = self.env['account.edi.xml.ubl_21.jo']._export_invoice(refund)[0]
        for invoice_price_unit, refund_price_unit in zip(get_price_units(invoice_file), get_price_units(refund_file)):
            self.assertEqual(invoice_price_unit, refund_price_unit)
