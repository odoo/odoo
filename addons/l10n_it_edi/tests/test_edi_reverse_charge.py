# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import namedtuple

from odoo import Command, fields
from odoo.tests import tagged
from odoo.addons.l10n_it_edi.tests.common import TestItEdi


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItEdiReverseCharge(TestItEdi):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Helper functions -----------
        def get_tag_ids(tag_codes):
            """ Helper function to define tag ids for taxes """
            return cls.env['account.account.tag'].search([
                ('applicability', '=', 'taxes'),
                ('country_id.code', '=', 'IT'),
                ('name', 'in', tag_codes)]).ids

        RepartitionLine = namedtuple('Line', 'factor_percent repartition_type tag_ids')
        def repartition_lines(*lines):
            """ Helper function to define repartition lines in taxes """
            return [(5, 0, 0)] + [(0, 0, {**line._asdict(), 'tag_ids': get_tag_ids(line[2])}) for line in lines]

        # Company -----------
        cls.company.partner_id.l10n_it_pa_index = "0803HR0"

        # Partner -----------
        cls.french_partner = cls.env['res.partner'].create({
            'name': 'Alessi',
            'vat': 'FR15437982937',
            'country_id': cls.env.ref('base.fr').id,
            'street': 'Avenue Test rue',
            'zip': '84000',
            'city': 'Avignon',
            'is_company': True
        })

        cls.san_marino_partner = cls.env['res.partner'].create({
            'name': 'Prospectra',
            'vat': 'SM6784',
            'country_id': cls.env.ref('base.sm').id,
            'street': 'Via Ventotto Luglio 212 Centro Uffici',
            'zip': '47893',
            'city': 'San Marino',
            'company_id': cls.company.id,
            'is_company': True,
        })

        # Taxes -----------
        tax_data = {
            'name': 'Tax 4% (Goods) Reverse Charge',
            'amount': 4.0,
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'invoice_repartition_line_ids': repartition_lines(
                RepartitionLine(100, 'base', ('+03', '+vj9')),
                RepartitionLine(100, 'tax', ('+5v',)),
                RepartitionLine(-100, 'tax', ('-4v',))),
            'refund_repartition_line_ids': repartition_lines(
                RepartitionLine(100, 'base', ('-03', '-vj9')),
                RepartitionLine(100, 'tax', False),
                RepartitionLine(-100, 'tax', False)),
        }
        # Purchase tax 4% with Reverse Charge
        cls.purchase_tax_4p = cls.env['account.tax'].with_company(cls.company).create(tax_data)

        # Purchase tax 4% with External Reverse Charge, targeting the tax grid for import of goods
        # already in Italy in a VAT deposit
        cls.purchase_tax_4p_already_in_italy = cls.env['account.tax'].with_company(cls.company).create({
            **tax_data,
            'name': 'Tax 4% purchase Reverse Charge, in Italy',
            'invoice_repartition_line_ids': repartition_lines(
                RepartitionLine(100, 'base', ('+03', '+vj3')),
                RepartitionLine(100, 'tax', ('+5v',)),
                RepartitionLine(-100, 'tax', ('-4v',))),
            'refund_repartition_line_ids': repartition_lines(
                RepartitionLine(100, 'base', ('-03', '-vj3')),
                RepartitionLine(100, 'tax', False),
                RepartitionLine(-100, 'tax', False)),
        })

        # Purchase tax 22% with Reverse Charge, targeting the tax grid for Construction Subcontractors
        # already in Italy in a VAT deposit
        cls.purchase_tax_vj12 = cls.env['account.tax'].with_company(cls.company).create({
            **tax_data,
            'name': '22% purchase RC Construction Subcontractors',
            'amount': 22.0,
            'invoice_repartition_line_ids': repartition_lines(
                RepartitionLine(100, 'base', ('+03', '+vj12')),
                RepartitionLine(100, 'tax', ('+5v',)),
                RepartitionLine(-100, 'tax', ('-4v',))),
            'refund_repartition_line_ids': repartition_lines(
                RepartitionLine(100, 'base', ('-03', '-vj12')),
                RepartitionLine(100, 'tax', False),
                RepartitionLine(-100, 'tax', False)),
        })

        # Purchase tax 22% with Reverse Charge
        cls.purchase_tax_22p = cls.env['account.tax'].with_company(cls.company).create({
            **tax_data,
            'name': 'Tax 22% purchase Reverse Charge',
            'amount': 22.0,
        })

        # Export tax 0%
        cls.sale_tax_0v = cls.env['account.tax'].with_company(cls.company).create({
            **tax_data,
            'type_tax_use': 'sale',
            'amount': 0.0,
            'amount_type': 'percent',
            'l10n_it_exempt_reason': 'N1',
            'l10n_it_law_reference': 'test',
        })

        # Export tax 0% Internal Reverse Charge
        cls.sale_tax_n63 = cls.env['account.tax'].with_company(cls.company).create({
            **tax_data,
            'name': 'Construction subcontractors',
            'type_tax_use': 'sale',
            'amount': 0.0,
            'amount_type': 'percent',
            'l10n_it_exempt_reason': 'N6.3',
            'l10n_it_law_reference': 'test',
        })

    def test_invoice_external_reverse_charge(self):
        invoice = self.env['account.move'].with_company(self.company).create({
            'move_type': 'out_invoice',
            'invoice_date': '2022-03-24',
            'invoice_date_due': '2022-03-24',
            'partner_id': self.french_partner.id,
            'partner_bank_id': self.test_bank.id,
            'invoice_line_ids': [
                Command.create({
                    'name': "Product A",
                    'product_id': self.product_a.id,
                    'price_unit': 800.40,
                    'tax_ids': [Command.set(self.sale_tax_0v.ids)],
                }),
                Command.create({
                    'name': "Product B",
                    'product_id': self.product_b.id,
                    'price_unit': 800.40,
                    'tax_ids': [Command.set(self.sale_tax_0v.ids)],
                }),
            ],
        })
        invoice.action_post()
        self._assert_export_invoice(invoice, 'invoice_external_reverse_charge.xml')

    def test_invoice_internal_reverse_charge(self):
        invoice = self.env['account.move'].with_company(self.company).create({
            'move_type': 'out_invoice',
            'invoice_date': '2022-03-24',
            'invoice_date_due': '2022-03-24',
            'partner_id': self.italian_partner_a.id,
            'partner_bank_id': self.test_bank.id,
            'invoice_line_ids': [
                Command.create({
                    'name': f"Construction subcontracting service {month}",
                    'product_id': self.product_a.id,
                    'price_unit': price,
                    'tax_ids': [Command.set(self.sale_tax_n63.ids)],
                }) for month, price in [("January", 350.0), ("February", 300.0), ("March", 50.0), ("April", 50.0)]
            ],
        })
        invoice.action_post()
        self._assert_export_invoice(invoice, 'invoice_internal_reverse_charge.xml')

    def test_bill_reverse_charge_and_refund(self):
        bill = self.env['account.move'].with_company(self.company).create({
            'move_type': 'in_invoice',
            'invoice_date': '2022-03-24',
            'invoice_date_due': '2022-03-24',
            'partner_id': self.french_partner.id,
            'partner_bank_id': self.test_bank.id,
            'invoice_line_ids': [
                Command.create({
                    'name': "Product A",
                    'product_id': self.product_a.id,
                    'price_unit': 800.40,
                    'tax_ids': [Command.set(self.purchase_tax_22p.ids)],
                }),
                Command.create({
                    'name': "Product B, taxed 4%",
                    'product_id': self.product_b.id,
                    'price_unit': 800.40,
                    'tax_ids': [Command.set(self.purchase_tax_4p.ids)],
                }),
            ],
        })
        bill.action_post()
        self._assert_export_invoice(bill, 'bill_reverse_charge.xml')

        credit_note = bill._reverse_moves([{'invoice_date': '2022-03-24', 'invoice_date_due': '2022-03-25'}])
        credit_note.action_post()
        self._assert_export_invoice(credit_note, 'credit_note_reverse_charge.xml')

    def test_reverse_charge_bill_2(self):
        bill = self.env['account.move'].with_company(self.company).create({
            'move_type': 'in_invoice',
            'invoice_date': '2022-03-24',
            'invoice_date_due': '2022-03-24',
            'partner_id': self.french_partner.id,
            'partner_bank_id': self.test_bank.id,
            'invoice_line_ids': [
                Command.create({
                    'name': "Product A",
                    'product_id': self.product_a.id,
                    'price_unit': 800.40,
                    'tax_ids': [Command.set(self.purchase_tax_22p.ids)],
                }),
                Command.create({
                    'name': "Product B, taxed 4% Already in Italy",
                    'product_id': self.product_b.id,
                    'price_unit': 800.40,
                    'tax_ids': [Command.set(self.purchase_tax_4p_already_in_italy.ids)],
                }),
            ],
        })
        bill.action_post()
        self._assert_export_invoice(bill, 'bill_reverse_charge_2.xml')

    def test_bill_reverse_charge_san_marino(self):
        bill = self.env['account.move'].with_company(self.company).create({
            'move_type': 'in_invoice',
            'invoice_date': '2022-03-24',
            'invoice_date_due': '2022-03-24',
            'partner_id': self.san_marino_partner.id,
            'partner_bank_id': self.test_bank.id,
            'invoice_line_ids': [
                Command.create({
                    'name': "Product A",
                    'product_id': self.product_a.id,
                    'price_unit': 800.40,
                    'tax_ids': [Command.set(self.purchase_tax_22p.ids)],
                }),
                Command.create({
                    'name': "Product B, taxed 4%",
                    'product_id': self.product_b.id,
                    'price_unit': 800.40,
                    'tax_ids': [Command.set(self.purchase_tax_4p.ids)],
                }),
            ],
        })
        bill.action_post()
        self._assert_export_invoice(bill, 'bill_reverse_charge_san_marino.xml')

    def test_receive_bill_reverse_charge_internal(self):
        """ Imported Internal Reverse Charge bill about Construction Subcontractors
            has the Sale 0% RC Tax Exemption N6.3 tax turned into Purchase 22% RC tax,
            targeting tag +VJ12
        """
        invoice = self._assert_import_invoice('IT01234567891_FPR01.xml', [{
            'invoice_date': fields.Date.from_string('2022-03-24'),
            'amount_untaxed': 750.0,
            'amount_tax': 0.0,
            'invoice_line_ids': [{
                'name': 'Construction subcontracting service January',
                'price_unit': 350.0,
            }, {
                'name': 'Construction subcontracting service February',
                'price_unit': 300.0,
            }, {
                'name': 'Construction subcontracting service March',
                'price_unit': 50.0,
            }, {
                'name': 'Construction subcontracting service April',
                'price_unit': 50.0,
            }]
        }])
        for line in invoice.invoice_line_ids:
            self.assertEqual(len(line.tax_ids), 1)
            rc_tax = line.tax_ids[0]
            self.assertEqual(rc_tax.amount, 22.0)
            self.assertTrue('+vj12' in rc_tax.invoice_repartition_line_ids[0].tag_ids.mapped("name"))
