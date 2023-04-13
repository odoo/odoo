# -*- coding: utf-8 -*-
#pylint: disable=too-many-lines
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo import Command


@tagged('post_install', '-at_install')
class TestAccountTaxDetailsReport(AccountTestInvoicingCommon):

    def _dispatch_move_lines(self, moves):
        base_lines = moves.line_ids\
            .filtered(lambda x: x.tax_ids and not x.tax_line_id)\
            .sorted(lambda x: (x.move_id.id, x.id, -abs(x.amount_currency)))
        tax_lines = moves.line_ids\
            .filtered(lambda x: x.tax_line_id)\
            .sorted(lambda x: (x.move_id.id, x.tax_line_id.id, x.tax_ids.ids, x.tax_repartition_line_id.id))
        return base_lines, tax_lines

    def _get_tax_details(self, fallback=False, extra_domain=None):
        domain = [('company_id', '=', self.env.company.id)] + (extra_domain or [])
        tax_details_query, tax_details_params = self.env['account.move.line']._get_query_tax_details_from_domain(domain, fallback=fallback)
        self.env['account.move.line'].flush_model()
        self.cr.execute(tax_details_query, tax_details_params)
        tax_details_res = self.cr.dictfetchall()
        return sorted(tax_details_res, key=lambda x: (x['base_line_id'], abs(x['base_amount']), abs(x['tax_amount'])))

    def assertTaxDetailsValues(self, tax_details, expected_values_list):
        self.assertEqual(len(tax_details), len(expected_values_list))

        for i, expected_values in enumerate(expected_values_list):
            keys = set(expected_values.keys())
            tax_detail = tax_details[i]
            self.assertDictEqual({k: v for k, v in tax_detail.items() if k in keys}, expected_values)

    def assertTotalAmounts(self, moves, tax_details):
        tax_lines = moves.line_ids.filtered('tax_line_id')
        taxes = tax_lines.mapped(lambda x: x.group_tax_id or x.tax_line_id)
        for tax in taxes:
            lines = tax_lines.filtered(lambda x: (x.group_tax_id or x.tax_line_id) == tax)
            tax_amount = sum(lines.mapped('balance'))
            tax_details_amount = sum(x['tax_amount']
                                     for x in tax_details
                                     if (x['group_tax_id'] or x['tax_id']) == tax.id)
            self.assertAlmostEqual(tax_amount, tax_details_amount)

    def test_affect_base_amount_1(self):
        tax_20_affect = self.env['account.tax'].create({
            'name': "tax_20_affect",
            'amount_type': 'percent',
            'amount': 20.0,
            'include_base_amount': True,
        })
        tax_10 = self.env['account.tax'].create({
            'name': "tax_10",
            'amount_type': 'percent',
            'amount': 10.0,
        })
        tax_5 = self.env['account.tax'].create({
            'name': "tax_5",
            'amount_type': 'percent',
            'amount': 5.0,
        })

        invoice_create_values = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'line1',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set((tax_20_affect + tax_10 + tax_5).ids)],
                }),
                Command.create({
                    'name': 'line2',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(tax_10.ids)],
                }),
                Command.create({
                    'name': 'line3',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(tax_10.ids)],
                }),
                Command.create({
                    'name': 'line4',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 2000.0,
                    'tax_ids': [Command.set((tax_20_affect + tax_10).ids)],
                }),
            ]
        }

        invoice = self.env['account.move'].create(invoice_create_values)
        base_lines, tax_lines = self._dispatch_move_lines(invoice)

        tax_details = self._get_tax_details()
        self.assertTaxDetailsValues(tax_details, [
            {
                'base_line_id': base_lines[0].id,
                'tax_line_id': tax_lines[3].id,
                'base_amount': -200.0,
                'tax_amount': -10.0,
            },
            {
                'base_line_id': base_lines[0].id,
                'tax_line_id': tax_lines[2].id,
                'base_amount': -200.0,
                'tax_amount': -20.0,
            },
            {
                'base_line_id': base_lines[0].id,
                'tax_line_id': tax_lines[3].id,
                'base_amount': -1000.0,
                'tax_amount': -50.0,
            },
            {
                'base_line_id': base_lines[0].id,
                'tax_line_id': tax_lines[2].id,
                'base_amount': -1000.0,
                'tax_amount': -100.0,
            },
            {
                'base_line_id': base_lines[0].id,
                'tax_line_id': tax_lines[1].id,
                'base_amount': -1000.0,
                'tax_amount': -200.0,
            },
            {
                'base_line_id': base_lines[1].id,
                'tax_line_id': tax_lines[2].id,
                'base_amount': -1000.0,
                'tax_amount': -100.0,
            },
            {
                'base_line_id': base_lines[2].id,
                'tax_line_id': tax_lines[2].id,
                'base_amount': -1000.0,
                'tax_amount': -100.0,
            },
            {
                'base_line_id': base_lines[3].id,
                'tax_line_id': tax_lines[2].id,
                'base_amount': -400.0,
                'tax_amount': -40.0,
            },
            {
                'base_line_id': base_lines[3].id,
                'tax_line_id': tax_lines[2].id,
                'base_amount': -2000.0,
                'tax_amount': -200.0,
            },
            {
                'base_line_id': base_lines[3].id,
                'tax_line_id': tax_lines[0].id,
                'base_amount': -2000.0,
                'tax_amount': -400.0,
            },
        ])
        self.assertTotalAmounts(invoice, tax_details)

        # Same with a group of taxes

        tax_group = self.env['account.tax'].create({
            'name': "tax_group",
            'amount_type': 'group',
            'children_tax_ids': [Command.set((tax_20_affect + tax_10 + tax_5).ids)],
        })

        invoice_create_values['invoice_line_ids'][0][2]['tax_ids'] = [Command.set(tax_group.ids)]
        invoice = self.env['account.move'].create(invoice_create_values)

        base_lines, tax_lines = self._dispatch_move_lines(invoice)

        tax_details = self._get_tax_details(extra_domain=[('move_id', '=', invoice.id)])
        self.assertTaxDetailsValues(tax_details, [
            {
                'base_line_id': base_lines[0].id,
                'tax_line_id': tax_lines[4].id,
                'base_amount': -200.0,
                'tax_amount': -10.0,
            },
            {
                'base_line_id': base_lines[0].id,
                'tax_line_id': tax_lines[2].id,
                'base_amount': -200.0,
                'tax_amount': -20.0,
            },
            {
                'base_line_id': base_lines[0].id,
                'tax_line_id': tax_lines[4].id,
                'base_amount': -1000.0,
                'tax_amount': -50.0,
            },
            {
                'base_line_id': base_lines[0].id,
                'tax_line_id': tax_lines[2].id,
                'base_amount': -1000.0,
                'tax_amount': -100.0,
            },
            {
                'base_line_id': base_lines[0].id,
                'tax_line_id': tax_lines[1].id,
                'base_amount': -1000.0,
                'tax_amount': -200.0,
            },
            {
                'base_line_id': base_lines[1].id,
                'tax_line_id': tax_lines[3].id,
                'base_amount': -1000.0,
                'tax_amount': -100.0,
            },
            {
                'base_line_id': base_lines[2].id,
                'tax_line_id': tax_lines[3].id,
                'base_amount': -1000.0,
                'tax_amount': -100.0,
            },
            {
                'base_line_id': base_lines[3].id,
                'tax_line_id': tax_lines[3].id,
                'base_amount': -400.0,
                'tax_amount': -40.0,
            },
            {
                'base_line_id': base_lines[3].id,
                'tax_line_id': tax_lines[3].id,
                'base_amount': -2000.0,
                'tax_amount': -200.0,
            },
            {
                'base_line_id': base_lines[3].id,
                'tax_line_id': tax_lines[0].id,
                'base_amount': -2000.0,
                'tax_amount': -400.0,
            },
        ])
        self.assertTotalAmounts(invoice, tax_details)

    def test_affect_base_amount_2(self):
        taxes_10_affect = self.env['account.tax'].create([{
            'name': "tax_10_affect_%s" % i,
            'amount_type': 'percent',
            'amount': 10.0,
            'include_base_amount': True,
        } for i in range(3)])

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'line1',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(taxes_10_affect.ids)],
                }),
                Command.create({
                    'name': 'line2',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set((taxes_10_affect[0] + taxes_10_affect[2]).ids)],
                }),
            ]
        })
        base_lines, tax_lines = self._dispatch_move_lines(invoice)

        tax_details = self._get_tax_details()
        self.assertTaxDetailsValues(
            tax_details,
            [
                {
                    'base_line_id': base_lines[0].id,
                    'tax_line_id': tax_lines[2].id,
                    'base_amount': -100.0,
                    'tax_amount': -10.0,
                },
                {
                    'base_line_id': base_lines[0].id,
                    'tax_line_id': tax_lines[3].id,
                    'base_amount': -100.0,
                    'tax_amount': -10.0,
                },
                {
                    'base_line_id': base_lines[0].id,
                    'tax_line_id': tax_lines[3].id,
                    'base_amount': -110.0,
                    'tax_amount': -11.0,
                },
                {
                    'base_line_id': base_lines[0].id,
                    'tax_line_id': tax_lines[0].id,
                    'base_amount': -1000.0,
                    'tax_amount': -100.0,
                },
                {
                    'base_line_id': base_lines[0].id,
                    'tax_line_id': tax_lines[2].id,
                    'base_amount': -1000.0,
                    'tax_amount': -100.0,
                },
                {
                    'base_line_id': base_lines[0].id,
                    'tax_line_id': tax_lines[3].id,
                    'base_amount': -1000.0,
                    'tax_amount': -100.0,
                },
                {
                    'base_line_id': base_lines[1].id,
                    'tax_line_id': tax_lines[3].id,
                    'base_amount': -100.0,
                    'tax_amount': -10.0,
                },
                {
                    'base_line_id': base_lines[1].id,
                    'tax_line_id': tax_lines[3].id,
                    'base_amount': -1000.0,
                    'tax_amount': -100.0,
                },
                {
                    'base_line_id': base_lines[1].id,
                    'tax_line_id': tax_lines[1].id,
                    'base_amount': -1000.0,
                    'tax_amount': -100.0,
                },
            ],
        )
        self.assertTotalAmounts(invoice, tax_details)

    def test_affect_base_amount_3(self):
        eco_tax = self.env['account.tax'].create({
            'name': "eco_tax",
            'amount_type': 'fixed',
            'amount': 5.0,
            'include_base_amount': True,
        })
        tax_20 = self.env['account.tax'].create({
            'name': "tax_20",
            'amount_type': 'percent',
            'amount': 20.0,
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'line1',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 95.0,
                    'tax_ids': [Command.set((eco_tax + tax_20).ids)],
                }),
            ]
        })
        base_lines, tax_lines = self._dispatch_move_lines(invoice)

        tax_details = self._get_tax_details()
        self.assertTaxDetailsValues(
            tax_details,
            [
                {
                    'base_line_id': base_lines[0].id,
                    'tax_line_id': tax_lines[1].id,
                    'base_amount': -5.0,
                    'tax_amount': -1.0,
                },
                {
                    'base_line_id': base_lines[0].id,
                    'tax_line_id': tax_lines[0].id,
                    'base_amount': -95.0,
                    'tax_amount': -5.0,
                },
                {
                    'base_line_id': base_lines[0].id,
                    'tax_line_id': tax_lines[1].id,
                    'base_amount': -95.0,
                    'tax_amount': -19.0,
                },
            ],
        )
        self.assertTotalAmounts(invoice, tax_details)

    def test_affect_base_amount_4(self):
        tax_10 = self.env['account.tax'].create({
            'name': "eco_tax",
            'amount_type': 'percent',
            'amount': 10.0,
            'include_base_amount': True,
        })
        tax_20 = self.env['account.tax'].create({
            'name': "tax_20",
            'amount_type': 'percent',
            'amount': 20.0,
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'line1',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set((tax_10 + tax_20).ids)],
                }),
                Command.create({
                    'name': 'line1',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax_10.ids)],
                }),
            ]
        })
        base_lines, tax_lines = self._dispatch_move_lines(invoice)

        tax_details = self._get_tax_details()
        self.assertTaxDetailsValues(
            tax_details,
            [
                {
                    'base_line_id': base_lines[0].id,
                    'tax_line_id': tax_lines[2].id,
                    'base_amount': -10.0,
                    'tax_amount': -2.0,
                },
                {
                    'base_line_id': base_lines[0].id,
                    'tax_line_id': tax_lines[1].id,
                    'base_amount': -100.0,
                    'tax_amount': -10.0,
                },
                {
                    'base_line_id': base_lines[0].id,
                    'tax_line_id': tax_lines[2].id,
                    'base_amount': -100.0,
                    'tax_amount': -20.0,
                },
                {
                    'base_line_id': base_lines[1].id,
                    'tax_line_id': tax_lines[0].id,
                    'base_amount': -100.0,
                    'tax_amount': -10.0,
                },
            ],
        )
        self.assertTotalAmounts(invoice, tax_details)

    def test_affect_base_amount_5(self):
        affecting_tax = self.env['account.tax'].create({
            'name': 'Affecting',
            'amount': 42,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'include_base_amount': True,
            'sequence': 0,
        })

        affected_tax = self.env['account.tax'].create({
            'name': 'Affected',
            'amount': 10,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'sequence': 1
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2021-08-01',
            'invoice_line_ids': [
                Command.create({
                    'name': "affecting",
                    'account_id': self.company_data['default_account_revenue'].id,
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': affecting_tax.ids,
                }),

                Command.create({
                    'name': "affected",
                    'account_id': self.company_data['default_account_revenue'].id,
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': affected_tax.ids,
                }),

                Command.create({
                    'name': "affecting + affected",
                    'account_id': self.company_data['default_account_revenue'].id,
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': (affecting_tax + affected_tax).ids,
                }),
            ]
        })

        base_lines, tax_lines = self._dispatch_move_lines(invoice)
        tax_details = self._get_tax_details()

        self.assertTaxDetailsValues(
            tax_details,
            [
                {
                    'base_line_id': base_lines[0].id,
                    'tax_line_id': tax_lines[0].id,
                    'base_amount': -100.0,
                    'tax_amount': -42.0,
                },
                {
                    'base_line_id': base_lines[1].id,
                    'tax_line_id': tax_lines[2].id,
                    'base_amount': -100.0,
                    'tax_amount': -10.0,
                },
                {
                    'base_line_id': base_lines[2].id,
                    'tax_line_id': tax_lines[2].id,
                    'base_amount': -42.0,
                    'tax_amount': -4.2,
                },
                {
                    'base_line_id': base_lines[2].id,
                    'tax_line_id': tax_lines[2].id,
                    'base_amount': -100.0,
                    'tax_amount': -10.0,
                },
                {
                    'base_line_id': base_lines[2].id,
                    'tax_line_id': tax_lines[1].id,
                    'base_amount': -100.0,
                    'tax_amount': -42.0,
                },
            ],
        )
        self.assertTotalAmounts(invoice, tax_details)

    def test_affect_base_amount_6(self):
        affecting_tax = self.env['account.tax'].create({
            'name': 'Affecting',
            'amount': 42,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'include_base_amount': True,
            'sequence': 0,
        })

        affected_tax = self.env['account.tax'].create({
            'name': 'Affected',
            'amount': 10,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'sequence': 1
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2021-08-01',
            'invoice_line_ids': [
                Command.create({
                    'name': "affecting + affected",
                    'account_id': self.company_data['default_account_revenue'].id,
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': (affecting_tax + affected_tax).ids,
                }),
            ]
        })

        invoice.write({'invoice_line_ids': [Command.delete(invoice.invoice_line_ids.id)]})
        base_lines, tax_lines = self._dispatch_move_lines(invoice)
        self.assertFalse(base_lines)
        self.assertFalse(tax_lines)
        tax_details = self._get_tax_details()
        self.assertFalse(tax_details)

    def test_round_globally_rounding(self):
        self.env.company.tax_calculation_rounding_method = 'round_globally'

        tax_50 = self.env['account.tax'].create({
            'name': "tax_50",
            'amount_type': 'percent',
            'amount': 50.0,
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'line%s' % i,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 0.01,
                    'tax_ids': [Command.set(tax_50.ids)],
                })
            for i in range(7)]
        })
        base_lines, tax_lines = self._dispatch_move_lines(invoice)

        tax_details = self._get_tax_details()
        self.assertTaxDetailsValues(
            tax_details,
            [
                {
                    'base_line_id': base_lines[0].id,
                    'tax_line_id': tax_lines.id,
                    'base_amount': -0.01,
                    'tax_amount': -0.01,
                },
                {
                    'base_line_id': base_lines[1].id,
                    'tax_line_id': tax_lines.id,
                    'base_amount': -0.01,
                    'tax_amount': 0.0,
                },
                {
                    'base_line_id': base_lines[2].id,
                    'tax_line_id': tax_lines.id,
                    'base_amount': -0.01,
                    'tax_amount': -0.01,
                },
                {
                    'base_line_id': base_lines[3].id,
                    'tax_line_id': tax_lines.id,
                    'base_amount': -0.01,
                    'tax_amount': 0.00,
                },
                {
                    'base_line_id': base_lines[4].id,
                    'tax_line_id': tax_lines.id,
                    'base_amount': -0.01,
                    'tax_amount': -0.01,
                },
                {
                    'base_line_id': base_lines[5].id,
                    'tax_line_id': tax_lines.id,
                    'base_amount': -0.01,
                    'tax_amount': 0.0,
                },
                {
                    'base_line_id': base_lines[6].id,
                    'tax_line_id': tax_lines.id,
                    'base_amount': -0.01,
                    'tax_amount': -0.01,
                },
            ],
        )
        self.assertTotalAmounts(invoice, tax_details)

    def test_round_per_line_update(self):
        self.env.company.tax_calculation_rounding_method = 'round_per_line'

        tax_8 = self.env['account.tax'].create({
            'name': "tax_8",
            'amount_type': 'percent',
            'amount': 8.0,
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'invoice_cash_rounding_id': self.cash_rounding_b.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'line1',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 45.45,
                    'tax_ids': [Command.set(tax_8.ids)],
                })
            ]
        })
        invoice.invoice_line_ids.write({"price_unit": 4545})

        base_lines, tax_lines = self._dispatch_move_lines(invoice)

        tax_details = self._get_tax_details()
        self.assertTaxDetailsValues(
            tax_details,
            [
                {
                    'base_line_id': base_lines[0].id,
                    'tax_line_id': tax_lines[0].id,
                    'base_amount': -4545.0,
                    'tax_amount': -363.6,
                },
            ],
        )
        self.assertTotalAmounts(invoice, tax_details)

    def test_partitioning_lines_by_moves(self):
        tax_20_affect = self.env['account.tax'].create({
            'name': "tax_20_affect",
            'amount_type': 'percent',
            'amount': 20.0,
            'include_base_amount': True,
        })
        tax_10 = self.env['account.tax'].create({
            'name': "tax_10",
            'amount_type': 'percent',
            'amount': 10.0,
        })

        invoices = self.env['account.move']
        expected_values_list = []
        for i in range(1, 6):
            invoice = invoices.create({
                'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': '2019-01-01',
                'invoice_line_ids': [
                    Command.create({
                        'name': 'line1',
                        'account_id': self.company_data['default_account_revenue'].id,
                        'price_unit': i * 1000.0,
                        'tax_ids': [Command.set((tax_20_affect + tax_10).ids)],
                    }),
                ]
            })
            invoices |= invoice
            base_lines, tax_lines = self._dispatch_move_lines(invoice)
            expected_values_list += [
                {
                    'base_line_id': base_lines[0].id,
                    'tax_line_id': tax_lines[1].id,
                    'base_amount': -200.0 * i,
                    'tax_amount': -20.0 * i,
                },
                {
                    'base_line_id': base_lines[0].id,
                    'tax_line_id': tax_lines[1].id,
                    'base_amount': -1000.0 * i,
                    'tax_amount': -100.0 * i,
                },
                {
                    'base_line_id': base_lines[0].id,
                    'tax_line_id': tax_lines[0].id,
                    'base_amount': -1000.0 * i,
                    'tax_amount': -200.0 * i,
                },
            ]

        tax_details = self._get_tax_details()
        self.assertTaxDetailsValues(tax_details, expected_values_list)
        self.assertTotalAmounts(invoices, tax_details)

    def test_fixed_tax_with_negative_quantity(self):
        fixed_tax = self.env['account.tax'].create({
            'name': "fixed_tax",
            'amount_type': 'fixed',
            'amount': 10.0,
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'line1',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 100.0,
                    'quantity': 5,
                    'tax_ids': [Command.set(fixed_tax.ids)],
                }),
                Command.create({
                    'name': 'line2',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 100.0,
                    'quantity': 9,
                    'tax_ids': [Command.set(fixed_tax.ids)],
                }),
                Command.create({
                    'name': 'line3',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 100.0,
                    'quantity': -4,
                    'tax_ids': [Command.set(fixed_tax.ids)],
                }),
            ]
        })
        base_lines, tax_lines = self._dispatch_move_lines(invoice)

        tax_details = self._get_tax_details()
        self.assertTaxDetailsValues(
            tax_details,
            [
                {
                    'base_line_id': base_lines[0].id,
                    'tax_line_id': tax_lines[0].id,
                    'base_amount': -500.0,
                    'tax_amount': -50.0,
                },
                {
                    'base_line_id': base_lines[1].id,
                    'tax_line_id': tax_lines[0].id,
                    'base_amount': -900.0,
                    'tax_amount': -90.0,
                },
                {
                    'base_line_id': base_lines[2].id,
                    'tax_line_id': tax_lines[0].id,
                    'base_amount': 400.0,
                    'tax_amount': 40.0,
                },
            ],
        )
        self.assertTotalAmounts(invoice, tax_details)

    def test_percent_tax_with_negative_balance(self):
        percent_tax = self.env['account.tax'].create({
            'name': "percent_tax",
            'amount_type': 'percent',
            'amount': 10.0,
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'line1',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 500.0,
                    'tax_ids': [Command.set(percent_tax.ids)],
                }),
                Command.create({
                    'name': 'line2',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 900.0,
                    'tax_ids': [Command.set(percent_tax.ids)],
                }),
                Command.create({
                    'name': 'line3',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': -400.0,
                    'tax_ids': [Command.set(percent_tax.ids)],
                }),
            ]
        })
        base_lines, tax_lines = self._dispatch_move_lines(invoice)

        tax_details = self._get_tax_details()
        self.assertTaxDetailsValues(
            tax_details,
            [
                {
                    'base_line_id': base_lines[0].id,
                    'tax_line_id': tax_lines[0].id,
                    'base_amount': -500.0,
                    'tax_amount': -50.0,
                },
                {
                    'base_line_id': base_lines[1].id,
                    'tax_line_id': tax_lines[0].id,
                    'base_amount': -900.0,
                    'tax_amount': -90.0,
                },
                {
                    'base_line_id': base_lines[2].id,
                    'tax_line_id': tax_lines[0].id,
                    'base_amount': 400.0,
                    'tax_amount': 40.0,
                },
            ],
        )
        self.assertTotalAmounts(invoice, tax_details)

    def test_fixed_tax_with_negative_balance(self):
        fixed_tax = self.env['account.tax'].create({
            'name': "fixed_tax",
            'amount_type': 'fixed',
            'amount': 10.0,
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'line1',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 500.0,
                    'tax_ids': [Command.set(fixed_tax.ids)],
                }),
                Command.create({
                    'name': 'line2',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 900.0,
                    'tax_ids': [Command.set(fixed_tax.ids)],
                }),
                Command.create({
                    'name': 'line3',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': -400.0,
                    'tax_ids': [Command.set(fixed_tax.ids)],
                }),
            ]
        })
        base_lines, tax_lines = self._dispatch_move_lines(invoice)

        tax_details = self._get_tax_details()
        self.assertTaxDetailsValues(
            tax_details,
            [
                {
                    'base_line_id': base_lines[0].id,
                    'tax_line_id': tax_lines[0].id,
                    'base_amount': -500.0,
                    'tax_amount': -10.0,
                },
                {
                    'base_line_id': base_lines[1].id,
                    'tax_line_id': tax_lines[0].id,
                    'base_amount': -900.0,
                    'tax_amount': -10.0,
                },
                {
                    'base_line_id': base_lines[2].id,
                    'tax_line_id': tax_lines[0].id,
                    'base_amount': 400.0,
                    'tax_amount': 10.0,
                },
            ],
        )
        self.assertTotalAmounts(invoice, tax_details)

    def test_multiple_same_tax_lines(self):
        """ In expense, the same tax line could be generated multiple times. """
        percent_tax = self.env['account.tax'].create({
            'name': "percent_tax",
            'amount_type': 'percent',
            'amount': 10.0,
        })
        tax_rep = percent_tax.refund_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax')

        move = self.env['account.move'].with_context(skip_invoice_sync=True).create({
            'date': '2019-01-01',
            'line_ids': [
                # Base lines
                Command.create({
                    'name': 'base1',
                    'debit': 1000.0,
                    'credit': 0.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'tax_ids': [Command.set(percent_tax.ids)],
                }),
                Command.create({
                    'name': 'base2',
                    'debit': 10000.0,
                    'credit': 0.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'tax_ids': [Command.set(percent_tax.ids)],
                }),
                # Tax lines
                Command.create({
                    'name': 'tax1',
                    'debit': 100.0,
                    'credit': 0.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'tax_repartition_line_id': tax_rep.id,
                }),
                Command.create({
                    'name': 'tax1',
                    'debit': 1000.0,
                    'credit': 0.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'tax_repartition_line_id': tax_rep.id,
                }),
                # Balance
                Command.create({
                    'name': 'balance',
                    'debit': 0.0,
                    'credit': 12100.0,
                    'account_id': self.company_data['default_account_receivable'].id,
                }),
            ],
        })
        base_lines, tax_lines = self._dispatch_move_lines(move)

        tax_details = self._get_tax_details()
        self.assertTaxDetailsValues(
            tax_details,
            [
                {
                    'base_line_id': base_lines[0].id,
                    'tax_line_id': tax_lines[0].id,
                    'base_amount': 1000.0,
                    'tax_amount': 9.09,
                },
                {
                    'base_line_id': base_lines[0].id,
                    'tax_line_id': tax_lines[1].id,
                    'base_amount': 1000.0,
                    'tax_amount': 90.91,
                },
                {
                    'base_line_id': base_lines[1].id,
                    'tax_line_id': tax_lines[0].id,
                    'base_amount': 10000.0,
                    'tax_amount': 90.91,
                },
                {
                    'base_line_id': base_lines[1].id,
                    'tax_line_id': tax_lines[1].id,
                    'base_amount': 10000.0,
                    'tax_amount': 909.09,
                },
            ],
        )
        self.assertTotalAmounts(move, tax_details)

    def test_multiple_same_tax_lines_multi_currencies_manual_edition(self):
        percent_tax = self.env['account.tax'].create({
            'name': "percent_tax",
            'amount_type': 'percent',
            'amount': 10.0,
        })
        tax_rep = percent_tax.refund_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax')

        move = self.env['account.move'].with_context(skip_invoice_sync=True).create({
            'date': '2019-01-01',
            'line_ids': [
                # Base lines
                Command.create({
                    'name': 'base1',
                    'debit': 1200.0,
                    'credit': 0.0,
                    'amount_currency': 2400.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'currency_id': self.currency_data['currency'].id,
                    'tax_ids': [Command.set(percent_tax.ids)],
                }),
                Command.create({
                    'name': 'base2',
                    'debit': 12000.0,
                    'credit': 0.0,
                    'amount_currency': 6000.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'currency_id': self.currency_data['currency'].id,
                    'tax_ids': [Command.set(percent_tax.ids)],
                }),
                # Tax lines
                Command.create({
                    'name': 'tax1',
                    'debit': 120.0,
                    'credit': 0.0,
                    'amount_currency': 360.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'currency_id': self.currency_data['currency'].id,
                    'tax_repartition_line_id': tax_rep.id,
                }),
                Command.create({
                    'name': 'tax1',
                    'debit': 1200.0,
                    'credit': 0.0,
                    'amount_currency': 200.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'currency_id': self.currency_data['currency'].id,
                    'tax_repartition_line_id': tax_rep.id,
                }),
                # Balance
                Command.create({
                    'name': 'balance',
                    'debit': 0.0,
                    'credit': 14520.0,
                    'account_id': self.company_data['default_account_receivable'].id,
                }),
            ],
        })
        base_lines, tax_lines = self._dispatch_move_lines(move)

        tax_details = self._get_tax_details()
        self.assertTaxDetailsValues(
            tax_details,
            [
                {
                    'base_line_id': base_lines[0].id,
                    'tax_line_id': tax_lines[0].id,
                    'base_amount': 1200.0,
                    'tax_amount': 10.91,
                    'base_amount_currency': 2400.0,
                    'tax_amount_currency': 102.857, # (2400.0 / 8400.0) * (360.0 / 560.0) * 560.0
                },
                {
                    'base_line_id': base_lines[0].id,
                    'tax_line_id': tax_lines[1].id,
                    'base_amount': 1200.0,
                    'tax_amount': 109.09,
                    'base_amount_currency': 2400.0,
                    'tax_amount_currency': 57.143, # (2400.0 / 8400.0) * (200.0 / 560.0) * 560.0
                },
                {
                    'base_line_id': base_lines[1].id,
                    'tax_line_id': tax_lines[0].id,
                    'base_amount': 12000.0,
                    'tax_amount': 109.09,
                    'base_amount_currency': 6000.0,
                    'tax_amount_currency': 257.143, # (6000.0 / 8400.0) * (360.0 / 560.0) * 560.0
                },
                {
                    'base_line_id': base_lines[1].id,
                    'tax_line_id': tax_lines[1].id,
                    'base_amount': 12000.0,
                    'tax_amount': 1090.91,
                    'base_amount_currency': 6000.0,
                    'tax_amount_currency': 142.857, # (6000.0 / 8400.0) * (200.0 / 560.0) * 560.0
                },
            ],
        )
        self.assertTotalAmounts(move, tax_details)

    def test_mixing_tax_inside_and_outside_a_group_of_taxes(self):
        percent_tax = self.env['account.tax'].create({
            'name': "percent_tax",
            'amount_type': 'percent',
            'amount': 10.0,
        })
        tax_group = self.env['account.tax'].create({
            'name': "tax_group",
            'amount_type': 'group',
            'children_tax_ids': [Command.set(percent_tax.ids)],
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'line1',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(percent_tax.ids)],
                }),
                Command.create({
                    'name': 'line2',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(tax_group.ids)],
                }),
            ]
        })
        base_lines, tax_lines = self._dispatch_move_lines(invoice)

        tax_details = self._get_tax_details()
        self.assertTaxDetailsValues(
            tax_details,
            [
                {
                    'base_line_id': base_lines[0].id,
                    'tax_line_id': tax_lines[0].id,
                    'base_amount': -1000.0,
                    'tax_amount': -100.0,
                },
                {
                    'base_line_id': base_lines[1].id,
                    'tax_line_id': tax_lines[1].id,
                    'base_amount': -1000.0,
                    'tax_amount': -100.0,
                },
            ],
        )
        self.assertTotalAmounts(invoice, tax_details)

    def test_broken_configuration(self):
        percent_tax = self.env['account.tax'].create({
            'name': "percent_tax",
            'amount_type': 'percent',
            'amount': 10.0,
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'line1',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(percent_tax.ids)],
                }),
            ]
        })
        base_lines, tax_lines = self._dispatch_move_lines(invoice)

        # Break the configuration
        tax_lines.account_id = self.company_data['default_account_assets']

        tax_details = self._get_tax_details(fallback=True)
        self.assertTaxDetailsValues(
            tax_details,
            [
                {
                    'base_line_id': base_lines[0].id,
                    'tax_line_id': tax_lines[0].id,
                    'base_amount': -1000.0,
                    'tax_amount': -100.0,
                },
            ],
        )
        self.assertTotalAmounts(invoice, tax_details)

    def test_tax_on_payment(self):
        percent_tax = self.env['account.tax'].create({
            'name': "percent_tax",
            'amount_type': 'percent',
            'amount': 10.0,
            'tax_exigibility': 'on_payment',
            'cash_basis_transition_account_id': self.company_data['default_account_assets'].id,
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'line1',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(percent_tax.ids)],
                }),
            ]
        })
        base_lines, tax_lines = self._dispatch_move_lines(invoice)

        tax_details = self._get_tax_details()
        self.assertTaxDetailsValues(
            tax_details,
            [
                {
                    'base_line_id': base_lines[0].id,
                    'tax_line_id': tax_lines[0].id,
                    'base_amount': -1000.0,
                    'tax_amount': -100.0,
                },
            ],
        )
        self.assertTotalAmounts(invoice, tax_details)

    def test_amounts_sign(self):
        for tax_sign in (1, -1):
            tax = self.env['account.tax'].create({
                'name': "tax",
                'amount_type': 'percent',
                'amount': tax_sign * 10.0,
            })

            amounts_list = [
                (-1000.0, 7000.0, -2000.0),
                (1000.0, -7000.0, 2000.0),
                (-1000.0, -7000.0, 2000.0),
                (1000.0, 7000.0, -2000.0),
            ]
            for amounts in amounts_list:
                with self.subTest(tax_sign=tax_sign, amounts=amounts):
                    invoice = self.env['account.move'].create({
                        'move_type': 'in_invoice',
                        'partner_id': self.partner_a.id,
                        'invoice_date': '2019-01-01',
                        'invoice_line_ids': [
                            Command.create({
                                'name': 'line2',
                                'account_id': self.company_data['default_account_revenue'].id,
                                'price_unit': amount,
                                'tax_ids': [Command.set(tax.ids)],
                            })
                        for amount in amounts],
                    })
                    _base_lines, tax_lines = self._dispatch_move_lines(invoice)

                    tax_details = self._get_tax_details(extra_domain=[('move_id', '=', invoice.id)])
                    self.assertTaxDetailsValues(
                        tax_details,
                        [
                            {
                                'tax_line_id': tax_lines[0].id,
                                'base_amount': amount,
                                'tax_amount': tax_sign * amount * 0.1,
                            }
                        for amount in amounts],
                    )
                    self.assertTotalAmounts(invoice, tax_details)
