from odoo import Command, tools

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import freeze_time, tagged


@freeze_time('2025-02-10 18:00:00')
@tagged('post_install_l10n', 'post_install', '-at_install')
class TestJpkFaReport(TestAccountReportsCommon):

    @classmethod
    @TestAccountReportsCommon.setup_country('pl')
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data['company'].write({
            'name': 'Polish Company',
            'city': 'Warsow',
            'street': 'ul. Marszałkowska 123',
            'state_id': cls.env.ref('l10n_pl.state_pl_mz'),
            'zip': '01-857',
            'vat': 'PL1234567883',
            'email': 'test@mail.com',
            'l10n_pl_reports_tax_office_id': cls.env.ref('l10n_pl.pl_tax_office_0206'),
        })

        cls.partner_a.write({
            'country_id': cls.env.ref('base.pl').id,
            'name': 'Jan Kowalski',
            'city': 'Warszawa',
            'street': 'ul. Nowowiejska 12',
            'zip': '00-150',
        })

        cls.partner_b.write({
            'country_id': cls.env.ref('base.be').id,
            'name': 'John Doe',
            'city': 'Bruxelles',
            'street': 'Rue de la Loi, 20',
            'zip': '1000',
        })

        cls.tax_pl_23 = cls.company_data['default_tax_sale'].copy({'name': "23% test", 'amount': 23})

        cls.tax_pl_8 = cls.company_data['default_tax_sale'].copy({'name': "8% test", 'amount': 8})

        invoices = cls.env['account.move'].create([
            {
                'name': 'INV/2025/00001',
                'move_type': 'out_invoice',
                'invoice_date': '2025-01-01',
                'date': '2025-01-01',
                'partner_id': cls.partner_a.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.product_b.id,
                        'quantity': 10.0,
                        'price_unit': 20.0,
                        'tax_ids': [Command.set(cls.tax_pl_23.ids)],
                    }),
                ],
            },
            {
                # The report do not take into account the KSEF = accepted
                'name': 'INV/2025/00003',
                'move_type': 'out_invoice',
                'invoice_date': '2025-01-10',
                'date': '2025-01-10',
                'partner_id': cls.partner_a.id,
                'l10n_pl_edi_status': 'accepted',
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.product_a.id,
                        'quantity': 1.0,
                        'price_unit': 1000.0,
                        'tax_ids': [Command.set(cls.tax_pl_23.ids)],
                    }),
                ],
            },
            {
                'name': 'INV/2025/00006',
                'move_type': 'out_invoice',
                'invoice_date': '2025-01-31',
                'date': '2025-01-31',
                'partner_id': cls.partner_a.id,
                'l10n_pl_edi_status': 'sent',
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.product_a.id,
                        'quantity': 1.0,
                        'price_unit': 100.0,
                        'tax_ids': False,
                    }),
                ],
            },
        ])
        invoices.action_post()

        cls.invoice_to_unfold = cls.env['account.move'].create([
            {
                'name': 'INV/2025/00004',
                'move_type': 'out_invoice',
                'invoice_date': '2025-01-15',
                'date': '2025-01-15',
                'partner_id': cls.partner_a.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.product_a.id,
                        'quantity': 4.0,
                        'price_unit': 750.0,
                        'tax_ids': [Command.set(cls.tax_pl_23.ids)],
                    }),
                    Command.create({
                        'product_id': cls.product_b.id,
                        'quantity': 2.0,
                        'price_unit': 20.0,
                        'tax_ids': [Command.set(cls.tax_pl_8.ids)],
                    })
                ],
            }
        ])
        cls.invoice_to_unfold.action_post()

        # Test the multi-currency behavior
        invoice_euro = cls.env['account.move'].create([
            {
                'name': 'INV/2025/00002',
                'move_type': 'out_invoice',
                'invoice_date': '2025-01-02',
                'date': '2025-01-02',
                'partner_id': cls.partner_b.id,
                'currency_id': cls.env.ref('base.EUR').id,
                'invoice_currency_rate': 0.85,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.product_a.id,
                        'quantity': 1.0,
                        'price_unit': 150.0,
                        'tax_ids': [Command.set(cls.tax_pl_23.ids)],
                    })
                ]
            }
        ])
        invoice_euro.action_activate_currency()
        invoice_euro.action_post()

        # Test the refund part
        invoice_to_revert = cls.env['account.move'].create([
            {
                'name': 'INV/2025/00005',
                'move_type': 'out_invoice',
                'invoice_date': '2025-01-25',
                'date': '2025-01-25',
                'partner_id': cls.partner_a.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.product_b.id,
                        'quantity': 10.0,
                        'price_unit': 20.0,
                        'tax_ids': [Command.set(cls.tax_pl_23.ids)],
                    }),
                ],
            }
        ])
        invoice_to_revert.action_post()
        cls.env['account.move.reversal'].create([
            {
                'move_ids': invoice_to_revert.ids,
                'reason': 'Broken devise',
                'journal_id': cls.company_data['default_journal_sale'].id,
            }
        ])
        reversal_move = cls.env['account.move'].create([
            {
                'name': 'RINV/2025/00001',
                'move_type': 'out_refund',
                'invoice_date': '2025-01-30',
                'date': '2025-01-30',
                'partner_id': cls.partner_a.id,
                'reversed_entry_id': invoice_to_revert.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.product_b.id,
                        'quantity': 10.0,
                        'price_unit': 20.0,
                        'tax_ids': [Command.set(cls.tax_pl_23.ids)],
                    })
                ]
            }
        ])
        reversal_move.action_post()

        cls.report = cls.env.ref('l10n_pl_reports_jpk_fa.jpk_fa_report')

    def test_jpk_fa_report(self):
        options = self._generate_options(self.report, '2025-01-01', '2025-01-31')

        self.assertLinesValues(
            self.report._get_lines(options),
            #       Name            Net Amount      Tax Amount    Amount Currency      Total Amount
            [       0,                      4,              6,                 7,                8],
            [
                ('INV/2025/00001',     200.00,          46.00,                '',           246.00),
                ('INV/2025/00002',     176.47,          40.59,            184.50,           217.06),
                ('INV/2025/00004',    3040.00,         693.20,                '',          3733.20),
                ('INV/2025/00005',     200.00,          46.00,                '',           246.00),
                ('RINV/2025/00001',   -200.00,         -46.00,                '',          -246.00),
                ('INV/2025/00006',     100.00,           0.00,                '',           100.00),
                ('Total',             3516.47,         779.79,                '',          4296.26),
            ],
            options,
            currency_map={7: {'currency': self.env.ref('base.EUR')}},
        )

    def test_jpk_fa_report_unfold_lines(self):
        options = self._generate_options(self.report, '2025-01-01', '2025-01-31')

        options['unfolded_lines'] = [self.report._get_generic_line_id('account.move', self.invoice_to_unfold.id)]

        lines = self.report._get_lines(options)
        self.assertLinesValues(
            lines,
            #       Name            Net Amount        Tax Used         Tax Amount    Amount Currency      Total Amount
            [       0,                      4,              5,                 6,                 7,                8],
            [
                ('INV/2025/00001',     200.00,             '',             46.00,                '',           246.00),
                ('INV/2025/00002',     176.47,             '',             40.59,            184.50,           217.06),
                ('INV/2025/00004',    3040.00,             '',            693.20,                '',          3733.20),
                ('product_a',         3000.00,     '23% test',            690.00,                '',          3690.00),
                ('product_b',           40.00,      '8% test',              3.20,                '',            43.20),
                ('INV/2025/00005',     200.00,             '',             46.00,                '',           246.00),
                ('RINV/2025/00001',   -200.00,             '',            -46.00,                '',          -246.00),
                ('INV/2025/00006',     100.00,             '',              0.00,                '',           100.00),
                ('Total',             3516.47,             '',            779.79,                '',          4296.26),
            ],
            options,
            currency_map={7: {'currency': self.env.ref('base.EUR')}},
        )

        unfolded_lines = [{'name': line['name'], 'level': line['level']} for line in lines]

        self.assertEqual(
            unfolded_lines,
            [
                {'level': 1, 'name': 'INV/2025/00001'},
                {'level': 1, 'name': 'INV/2025/00002'},
                {'level': 1, 'name': 'INV/2025/00004'},
                {'level': 4, 'name': 'product_a'},
                {'level': 4, 'name': 'product_b'},
                {'level': 1, 'name': 'INV/2025/00005'},
                {'level': 1, 'name': 'RINV/2025/00001'},
                {'level': 1, 'name': 'INV/2025/00006'},
                {'level': 1, 'name': 'Total'},
            ]
        )

        options['unfold_all'] = True

        lines = self.report._get_lines(options)
        self.assertLinesValues(
            lines,
            #       Name            Net Amount        Tax Used         Tax Amount    Amount Currency      Total Amount
            [       0,                      4,              5,                 6,                 7,                8],
            [
                ('INV/2025/00001',     200.00,             '',             46.00,                '',           246.00),
                ('product_b',          200.00,     '23% test',             46.00,                '',           246.00),
                ('INV/2025/00002',     176.47,             '',             40.59,            184.50,           217.06),
                ('product_a',          176.47,     '23% test',             40.59,                '',           217.06),
                ('INV/2025/00004',    3040.00,             '',            693.20,                '',          3733.20),
                ('product_a',         3000.00,     '23% test',            690.00,                '',          3690.00),
                ('product_b',           40.00,      '8% test',              3.20,                '',            43.20),
                ('INV/2025/00005',     200.00,             '',             46.00,                '',           246.00),
                ('product_b',          200.00,     '23% test',             46.00,                '',           246.00),
                ('RINV/2025/00001',   -200.00,             '',            -46.00,                '',          -246.00),
                ('product_b',         -200.00,     '23% test',            -46.00,                '',          -246.00),
                ('INV/2025/00006',     100.00,             '',              0.00,                '',           100.00),
                ('product_a',          100.00,             '',                '',                '',           100.00),
                ('Total',             3516.47,             '',            779.79,                '',          4296.26),
            ],
            options,
            currency_map={7: {'currency': self.env.ref('base.EUR')}},
        )

        unfolded_lines = [{'name': line['name'], 'level': line['level']} for line in lines]

        self.assertEqual(
            unfolded_lines,
            [
                {'level': 1, 'name': 'INV/2025/00001'},
                {'level': 4, 'name': 'product_b'},
                {'level': 1, 'name': 'INV/2025/00002'},
                {'level': 4, 'name': 'product_a'},
                {'level': 1, 'name': 'INV/2025/00004'},
                {'level': 4, 'name': 'product_a'},
                {'level': 4, 'name': 'product_b'},
                {'level': 1, 'name': 'INV/2025/00005'},
                {'level': 4, 'name': 'product_b'},
                {'level': 1, 'name': 'RINV/2025/00001'},
                {'level': 4, 'name': 'product_b'},
                {'level': 1, 'name': 'INV/2025/00006'},
                {'level': 4, 'name': 'product_a'},
                {'level': 1, 'name': 'Total'},
            ]
        )

    def test_jpk_fa_export(self):
        options = self._generate_options(self.report, '2025-01-01', '2025-01-31')
        result_print = self.env[self.report.custom_handler_model_name].export_tax_report_to_xml(options)

        with tools.file_open('l10n_pl_reports_jpk_fa/tests/expected_xmls/jpk_fa_expected.xml', 'rb') as expected_xml_file:
            self.assertXmlTreeEqual(
                self.get_xml_tree_from_string(result_print['file_content']),
                self.get_xml_tree_from_string(expected_xml_file.read()),
            )
