# -*- coding: utf-8 -*-
# pylint: disable=bad-whitespace
from unittest.mock import patch
from freezegun import freeze_time

from .common import TestAccountReportsCommon
from odoo import fields, Command
from odoo.tests import tagged
from odoo.tests.common import Form
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestTaxReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # Create country data

        cls.fiscal_country = cls.env['res.country'].create({
            'name': "Discworld",
            'code': 'DW',
        })

        cls.country_state_1 = cls.env['res.country.state'].create({
            'name': "Ankh Morpork",
            'code': "AM",
            'country_id': cls.fiscal_country.id,
        })

        cls.country_state_2 = cls.env['res.country.state'].create({
            'name': "Counterweight Continent",
            'code': "CC",
            'country_id': cls.fiscal_country.id,
        })

        cls.foreign_country = cls.env['res.country'].create({
            'name': "The Principality of Zeon",
            'code': 'PZ',
        })

        # Setup fiscal data
        cls.company_data['company'].write({
            'state_id': cls. country_state_1.id, # Not necessary at the moment; put there for consistency and robustness with possible future changes
            'account_tax_periodicity': 'trimester',
        })
        cls.change_company_country(cls.company_data['company'], cls.fiscal_country)

        # Prepare tax groups
        cls.tax_group_1 = cls._instantiate_basic_test_tax_group()
        cls.tax_group_2 = cls._instantiate_basic_test_tax_group()
        cls.tax_group_3 = cls._instantiate_basic_test_tax_group(country=cls.foreign_country)

        # Prepare tax accounts
        cls.tax_account_1 = cls.env['account.account'].create({
            'name': 'Tax Account',
            'code': '250000',
            'account_type': 'liability_current',
            'company_id': cls.company_data['company'].id,
        })

        cls.tax_account_2 = cls.env['account.account'].create({
            'name': 'Tax Account',
            'code': '250001',
            'account_type': 'liability_current',
            'company_id': cls.company_data['company'].id,
        })

        # ==== Sale taxes: group of two taxes having type_tax_use = 'sale' ====
        cls.sale_tax_percentage_incl_1 = cls.env['account.tax'].create({
            'name': 'sale_tax_percentage_incl_1',
            'amount': 20.0,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'price_include': True,
            'tax_group_id': cls.tax_group_1.id,
        })

        cls.sale_tax_percentage_excl = cls.env['account.tax'].create({
            'name': 'sale_tax_percentage_excl',
            'amount': 10.0,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'tax_group_id': cls.tax_group_1.id,
        })

        cls.sale_tax_group = cls.env['account.tax'].create({
            'name': 'sale_tax_group',
            'amount_type': 'group',
            'type_tax_use': 'sale',
            'children_tax_ids': [Command.set((cls.sale_tax_percentage_incl_1 + cls.sale_tax_percentage_excl).ids)],
        })

        cls.move_sale = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': cls.company_data['default_journal_sale'].id,
            'line_ids': [
                Command.create({
                    'debit': 1320.0,
                    'credit': 0.0,
                    'account_id': cls.company_data['default_account_receivable'].id,
                }),
                Command.create({
                    'debit': 0.0,
                    'credit': 120.0,
                    'account_id': cls.tax_account_1.id,
                    'tax_repartition_line_id': cls.sale_tax_percentage_excl.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').id,
                }),
                Command.create({
                    'debit': 0.0,
                    'credit': 200.0,
                    'account_id': cls.tax_account_1.id,
                    'tax_repartition_line_id': cls.sale_tax_percentage_incl_1.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').id,
                    'tax_ids': [Command.set(cls.sale_tax_percentage_excl.ids)]
                }),
                Command.create({
                    'debit': 0.0,
                    'credit': 1000.0,
                    'account_id': cls.company_data['default_account_revenue'].id,
                    'tax_ids': [Command.set(cls.sale_tax_group.ids)]
                }),
            ],
        })
        cls.move_sale.action_post()

        # ==== Purchase taxes: group of taxes having type_tax_use = 'none' ====

        cls.none_tax_percentage_incl_2 = cls.env['account.tax'].create({
            'name': 'none_tax_percentage_incl_2',
            'amount': 20.0,
            'amount_type': 'percent',
            'type_tax_use': 'none',
            'price_include': True,
            'tax_group_id': cls.tax_group_2.id,
        })

        cls.none_tax_percentage_excl = cls.env['account.tax'].create({
            'name': 'none_tax_percentage_excl',
            'amount': 30.0,
            'amount_type': 'percent',
            'type_tax_use': 'none',
            'tax_group_id': cls.tax_group_2.id,
        })

        cls.purchase_tax_group = cls.env['account.tax'].create({
            'name': 'purchase_tax_group',
            'amount_type': 'group',
            'type_tax_use': 'purchase',
            'children_tax_ids': [Command.set((cls.none_tax_percentage_incl_2 + cls.none_tax_percentage_excl).ids)],
        })

        cls.move_purchase = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': cls.company_data['default_journal_purchase'].id,
            'line_ids': [
                Command.create({
                    'debit': 0.0,
                    'credit': 3120.0,
                    'account_id': cls.company_data['default_account_payable'].id,
                }),
                Command.create({
                    'debit': 720.0,
                    'credit': 0.0,
                    'account_id': cls.tax_account_1.id,
                    'tax_repartition_line_id': cls.none_tax_percentage_excl.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').id,
                }),
                Command.create({
                    'debit': 400.0,
                    'credit': 0.0,
                    'account_id': cls.tax_account_1.id,
                    'tax_repartition_line_id': cls.none_tax_percentage_incl_2.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').id,
                    'tax_ids': [Command.set(cls.none_tax_percentage_excl.ids)]
                }),
                Command.create({
                    'debit': 2000.0,
                    'credit': 0.0,
                    'account_id': cls.company_data['default_account_expense'].id,
                    'tax_ids': [Command.set(cls.purchase_tax_group.ids)]
                }),
            ],
        })
        cls.move_purchase.action_post()

        #Instantiate test data for fiscal_position option of the tax report (both for checking the report and VAT closing)

        # Create a foreign partner
        cls.test_fpos_foreign_partner = cls.env['res.partner'].create({
            'name': "Mare Cel",
            'country_id': cls.fiscal_country.id,
            'state_id': cls.country_state_2.id,
        })

        # Create a tax report and some taxes for it
        cls.basic_tax_report = cls.env['account.report'].create({
            'name': "The Unseen Tax Report",
            'country_id': cls.fiscal_country.id,
            'root_report_id': cls.env.ref("account.generic_tax_report").id,
            'column_ids': [Command.create({'name': 'balance', 'sequence': 1, 'expression_label': 'balance',})],
        })

        cls.test_fpos_tax_sale = cls._add_basic_tax_for_report(
            cls.basic_tax_report, 50, 'sale', cls.tax_group_1,
            [(30, cls.tax_account_1, False), (70, cls.tax_account_1, True), (-10, cls.tax_account_2, True)]
        )

        cls.test_fpos_tax_purchase = cls._add_basic_tax_for_report(
            cls.basic_tax_report, 50, 'purchase', cls.tax_group_2,
            [(10, cls.tax_account_1, False), (60, cls.tax_account_1, True), (-5, cls.tax_account_2, True)]
        )

        # Create a fiscal_position to automatically map the default tax for partner "Mare Cel" to our test tax
        cls.foreign_vat_fpos = cls.env['account.fiscal.position'].create({
            'name': "Test fpos",
            'auto_apply': True,
            'country_id': cls.fiscal_country.id,
            'state_ids': cls.country_state_2.ids,
            'foreign_vat': '12345',
        })

        # Create some domestic invoices (not all in the same closing period)
        cls.init_invoice('out_invoice', partner=cls.partner_a, invoice_date='2020-12-22', post=True, amounts=[28000], taxes=cls.test_fpos_tax_sale)
        cls.init_invoice('out_invoice', partner=cls.partner_a, invoice_date='2021-01-22', post=True, amounts=[200], taxes=cls.test_fpos_tax_sale)
        cls.init_invoice('out_refund', partner=cls.partner_a, invoice_date='2021-01-12', post=True, amounts=[20], taxes=cls.test_fpos_tax_sale)
        cls.init_invoice('in_invoice', partner=cls.partner_a, invoice_date='2021-03-12', post=True, amounts=[400], taxes=cls.test_fpos_tax_purchase)
        cls.init_invoice('in_refund', partner=cls.partner_a, invoice_date='2021-03-20', post=True, amounts=[60], taxes=cls.test_fpos_tax_purchase)
        cls.init_invoice('in_invoice', partner=cls.partner_a, invoice_date='2021-04-07', post=True, amounts=[42000], taxes=cls.test_fpos_tax_purchase)

        # Create some foreign invoices (not all in the same closing period)
        cls.init_invoice('out_invoice', partner=cls.test_fpos_foreign_partner, invoice_date='2020-12-13', post=True, amounts=[26000], taxes=cls.test_fpos_tax_sale)
        cls.init_invoice('out_invoice', partner=cls.test_fpos_foreign_partner, invoice_date='2021-01-16', post=True, amounts=[800], taxes=cls.test_fpos_tax_sale)
        cls.init_invoice('out_refund', partner=cls.test_fpos_foreign_partner, invoice_date='2021-01-30', post=True, amounts=[200], taxes=cls.test_fpos_tax_sale)
        cls.init_invoice('in_invoice', partner=cls.test_fpos_foreign_partner, invoice_date='2021-02-01', post=True, amounts=[1000], taxes=cls.test_fpos_tax_purchase)
        cls.init_invoice('in_refund', partner=cls.test_fpos_foreign_partner, invoice_date='2021-03-02', post=True, amounts=[600], taxes=cls.test_fpos_tax_purchase)
        cls.init_invoice('in_refund', partner=cls.test_fpos_foreign_partner, invoice_date='2021-05-02', post=True, amounts=[10000], taxes=cls.test_fpos_tax_purchase)

    @classmethod
    def _add_basic_tax_for_report(cls, tax_report, percentage, type_tax_use, tax_group, tax_repartition, company=None):
        """ Creates a basic test tax, as well as tax report lines and tags, connecting them all together.

        A tax report line will be created within tax report for each of the elements in tax_repartition,
        for both invoice and refund, so that the resulting repartition lines each reference their corresponding
        report line. Negative tags will be assign for refund lines; postive tags for invoice ones.

        :param tax_report: The report to create lines for.
        :param percentage: The created tax has amoun_type='percent'. This parameter contains its amount.
        :param type_tax_use: type_tax_use of the tax to create
        :param tax_repartition: List of tuples in the form [(factor_percent, account, use_in_tax_closing)], one tuple
                                for each tax repartition line to create (base lines will be automatically created).
        """
        tax = cls.env['account.tax'].create({
            'name': f"{type_tax_use} - {percentage} - {tax_report.name}",
            'amount': percentage,
            'amount_type': 'percent',
            'type_tax_use': type_tax_use,
            'tax_group_id': tax_group.id,
            'country_id': tax_report.country_id.id,
            'company_id': company.id if company else cls.env.company.id,
        })

        to_write = {}
        for move_type_suffix in ('invoice', 'refund'):
            sign = "-" if move_type_suffix == 'refund' else "+"
            report_line_sequence = tax_report.line_ids[-1].sequence + 1 if tax_report.line_ids else 0


            # Create a report line for the base
            base_report_line_name = f"{tax.id}-{move_type_suffix}-base"
            base_report_line = cls._create_tax_report_line(base_report_line_name, tax_report, tag_name=base_report_line_name, sequence=report_line_sequence)
            report_line_sequence += 1

            base_tag = base_report_line.expression_ids._get_matching_tags(sign)

            repartition_vals = [
                Command.clear(),
                Command.create({'repartition_type': 'base', 'tag_ids': base_tag.ids}),
            ]

            for (factor_percent, account, use_in_tax_closing) in tax_repartition:
                # Create a report line for the reparition line
                tax_report_line_name = f"{tax.id}-{move_type_suffix}-{factor_percent}"
                tax_report_line = cls._create_tax_report_line(tax_report_line_name, tax_report, tag_name=tax_report_line_name, sequence=report_line_sequence)
                report_line_sequence += 1

                tax_tag = tax_report_line.expression_ids._get_matching_tags(sign)

                repartition_vals.append(Command.create({
                    'account_id': account.id if account else None,
                    'factor_percent': factor_percent,
                    'use_in_tax_closing': use_in_tax_closing,
                    'tag_ids': tax_tag.ids,
                }))

            to_write[f"{move_type_suffix}_repartition_line_ids"] = repartition_vals

        tax.write(to_write)

        return tax

    def _assert_vat_closing(self, report, options, closing_vals_by_fpos):
        """ Checks the result of the VAT closing

        :param options: the tax report options to make the closing for
        :param closing_vals_by_fpos: A list of dict(fiscal_position: [dict(line_vals)], where fiscal_position is (possibly empty)
                                     account.fiscal.position record, and line_vals, the expected values for each closing move lines.
                                     In case the option 'companies' contains more than 1 company, a tuple (company, fiscal_position)
                                     replaces the fiscal_position key
        """
        with patch.object(type(self.env['account.move']), '_get_vat_report_attachments', autospec=True, side_effect=lambda *args, **kwargs: []):
            vat_closing_moves = self.env['account.generic.tax.report.handler']._generate_tax_closing_entries(report, options)

            if len(options['companies']) > 1:
                closing_moves_by_fpos = {(move.company_id, move.fiscal_position_id): move for move in vat_closing_moves}
            else:
                closing_moves_by_fpos = {move.fiscal_position_id: move for move in vat_closing_moves}

            for key, closing_vals in closing_vals_by_fpos.items():
                vat_closing_move = closing_moves_by_fpos[key]
                self.assertRecordValues(vat_closing_move.line_ids, closing_vals)
            self.assertEqual(len(closing_vals_by_fpos), len(vat_closing_moves), "Exactly one move should have been generated per fiscal position; nothing else.")

    def test_vat_closing_single_fpos(self):
        """ Tests the VAT closing when a foreign VAT fiscal position is selected on the tax report
        """
        options = self._generate_options(
            self.basic_tax_report, fields.Date.from_string('2021-01-15'), fields.Date.from_string('2021-02-01'),
            {'fiscal_position': self.foreign_vat_fpos.id}
        )

        self._assert_vat_closing(self.basic_tax_report, options, {
            self.foreign_vat_fpos: [
                # sales: 800 * 0.5 * 0.7 - 200 * 0.5 * 0.7
                {'debit': 210,      'credit': 0.0,      'account_id': self.tax_account_1.id},
                # sales: 800 * 0.5 * (-0.1) - 200 * 0.5 * (-0.1)
                {'debit': 0,        'credit': 30,       'account_id': self.tax_account_2.id},
                # purchases: 1000 * 0.5 * 0.6 - 600 * 0.5 * 0.6
                {'debit': 0,        'credit': 120,      'account_id': self.tax_account_1.id},
                # purchases: 1000 * 0.5 * (-0.05) - 600 * 0.5 * (-0.05)
                {'debit': 10,       'credit': 0,        'account_id': self.tax_account_2.id},
                # For sales operations
                {'debit': 0,        'credit': 180,      'account_id': self.tax_group_1.tax_payable_account_id.id},
                # For purchase operations
                {'debit': 110,      'credit': 0,        'account_id': self.tax_group_2.tax_receivable_account_id.id},
            ]
        })

    def test_vat_closing_domestic(self):
        """ Tests the VAT closing when a foreign VAT fiscal position is selected on the tax report
        """
        options = self._generate_options(
            self.basic_tax_report, fields.Date.from_string('2021-01-15'), fields.Date.from_string('2021-02-01'),
            {'fiscal_position': 'domestic'}
        )

        self._assert_vat_closing(self.basic_tax_report, options, {
            self.env['account.fiscal.position']: [
                # sales: 200 * 0.5 * 0.7 - 20 * 0.5 * 0.7
                {'debit': 63,       'credit': 0.0,      'account_id': self.tax_account_1.id},
                # sales: 200 * 0.5 * (-0.1) - 20 * 0.5 * (-0.1)
                {'debit': 0,        'credit': 9,        'account_id': self.tax_account_2.id},
                # purchases: 400 * 0.5 * 0.6 - 60 * 0.5 * 0.6
                {'debit': 0,        'credit': 102,      'account_id': self.tax_account_1.id},
                # purchases: 400 * 0.5 * (-0.05) - 60 * 0.5 * (-0.05)
                {'debit': 8.5,      'credit': 0,        'account_id': self.tax_account_2.id},
                # For sales operations
                {'debit': 0,        'credit': 54,       'account_id': self.tax_group_1.tax_payable_account_id.id},
                # For purchase operations
                {'debit': 93.5,     'credit': 0,        'account_id': self.tax_group_2.tax_receivable_account_id.id},
            ]
        })

    def test_vat_closing_everything(self):
        """ Tests the VAT closing when the option to show all foreign VAT fiscal positions is activated.
        One closing move should then be generated per fiscal position.
        """
        options = self._generate_options(
            self.basic_tax_report, fields.Date.from_string('2021-01-15'), fields.Date.from_string('2021-02-01'),
            {'fiscal_position': 'all'}
        )

        self._assert_vat_closing(self.basic_tax_report, options, {
            # From test_vat_closing_domestic
            self.env['account.fiscal.position']: [
                # sales: 200 * 0.5 * 0.7 - 20 * 0.5 * 0.7
                {'debit': 63,       'credit': 0.0,      'account_id': self.tax_account_1.id},
                # sales: 200 * 0.5 * (-0.1) - 20 * 0.5 * (-0.1)
                {'debit': 0,        'credit': 9,        'account_id': self.tax_account_2.id},
                # purchases: 400 * 0.5 * 0.6 - 60 * 0.5 * 0.6
                {'debit': 0,        'credit': 102,      'account_id': self.tax_account_1.id},
                # purchases: 400 * 0.5 * (-0.05) - 60 * 0.5 * (-0.05)
                {'debit': 8.5,      'credit': 0,        'account_id': self.tax_account_2.id},
                # For sales operations
                {'debit': 0,        'credit': 54,       'account_id': self.tax_group_1.tax_payable_account_id.id},
                # For purchase operations
                {'debit': 93.5,     'credit': 0,        'account_id': self.tax_group_2.tax_receivable_account_id.id},
            ],

            # From test_vat_closing_single_fpos
            self.foreign_vat_fpos: [
                # sales: 800 * 0.5 * 0.7 - 200 * 0.5 * 0.7
                {'debit': 210,      'credit': 0.0,      'account_id': self.tax_account_1.id},
                # sales: 800 * 0.5 * (-0.1) - 200 * 0.5 * (-0.1)
                {'debit': 0,        'credit': 30,       'account_id': self.tax_account_2.id},
                # purchases: 1000 * 0.5 * 0.6 - 600 * 0.5 * 0.6
                {'debit': 0,        'credit': 120,      'account_id': self.tax_account_1.id},
                # purchases: 1000 * 0.5 * (-0.05) - 600 * 0.5 * (-0.05)
                {'debit': 10,       'credit': 0,        'account_id': self.tax_account_2.id},
                # For sales operations
                {'debit': 0,        'credit': 180,      'account_id': self.tax_group_1.tax_payable_account_id.id},
                # For purchase operations
                {'debit': 110,      'credit': 0,        'account_id': self.tax_group_2.tax_receivable_account_id.id},
            ],
        })

    def test_vat_closing_generic(self):
        """ VAT closing for the generic report should create one closing move per fiscal position + a domestic one.
        One closing move should then be generated per fiscal position.
        """
        for generic_report_xml_id in ('account.generic_tax_report', 'account.generic_tax_report_account_tax', 'account.generic_tax_report_tax_account'):
            generic_report = self.env.ref(generic_report_xml_id)
            options = self._generate_options(generic_report, fields.Date.from_string('2021-01-15'), fields.Date.from_string('2021-02-01'))

            self._assert_vat_closing(generic_report, options, {
                # From test_vat_closing_domestic
                self.env['account.fiscal.position']: [
                    # sales: 200 * 0.5 * 0.7 - 20 * 0.5 * 0.7
                    {'debit': 63,       'credit': 0.0,      'account_id': self.tax_account_1.id},
                    # sales: 200 * 0.5 * (-0.1) - 20 * 0.5 * (-0.1)
                    {'debit': 0,        'credit': 9,        'account_id': self.tax_account_2.id},
                    # purchases: 400 * 0.5 * 0.6 - 60 * 0.5 * 0.6
                    {'debit': 0,        'credit': 102,      'account_id': self.tax_account_1.id},
                    # purchases: 400 * 0.5 * (-0.05) - 60 * 0.5 * (-0.05)
                    {'debit': 8.5,      'credit': 0,        'account_id': self.tax_account_2.id},
                    # For sales operations
                    {'debit': 0,        'credit': 54,       'account_id': self.tax_group_1.tax_payable_account_id.id},
                    # For purchase operations
                    {'debit': 93.5,     'credit': 0,        'account_id': self.tax_group_2.tax_receivable_account_id.id},
                ],

                # From test_vat_closing_single_fpos
                self.foreign_vat_fpos: [
                    # sales: 800 * 0.5 * 0.7 - 200 * 0.5 * 0.7
                    {'debit': 210,      'credit': 0.0,      'account_id': self.tax_account_1.id},
                    # sales: 800 * 0.5 * (-0.1) - 200 * 0.5 * (-0.1)
                    {'debit': 0,        'credit': 30,       'account_id': self.tax_account_2.id},
                    # purchases: 1000 * 0.5 * 0.6 - 600 * 0.5 * 0.6
                    {'debit': 0,        'credit': 120,      'account_id': self.tax_account_1.id},
                    # purchases: 1000 * 0.5 * (-0.05) - 600 * 0.5 * (-0.05)
                    {'debit': 10,       'credit': 0,        'account_id': self.tax_account_2.id},
                    # For sales operations
                    {'debit': 0,        'credit': 180,      'account_id': self.tax_group_1.tax_payable_account_id.id},
                    # For purchase operations
                    {'debit': 110,      'credit': 0,        'account_id': self.tax_group_2.tax_receivable_account_id.id},
                ],
            })

    def test_vat_closing_button_availability(self):
        def assertTaxClosingAvailable(is_enabled, active_companies, export_main_company=None):
            options = tax_report.with_context(allowed_company_ids=active_companies.ids).get_options()
            closing_button_dict = next(filter(lambda x: x['action'] == 'action_periodic_vat_entries', options['buttons']))
            self.assertEqual(closing_button_dict.get('disabled', False), not is_enabled)
            if is_enabled:
                self.assertEqual(tax_report._get_sender_company_for_export(options), export_main_company)

        tax_report = self.env.ref('account.generic_tax_report')

        main_company = self.company_data['company']
        main_company.vat = '123'
        branch_1 = self.env['res.company'].create({'name': "Branch 1", 'parent_id': main_company.id})
        branch_1_1 = self.env['res.company'].create({'name': "Branch 1 sub-branch 1", 'parent_id': branch_1.id})
        branch_2 = self.env['res.company'].create({'name': "Branch 2", 'parent_id': main_company.id, 'vat': '456'})
        branch_2_1 = self.env['res.company'].create({'name': "Branch 2 sub-branch 1", 'parent_id': branch_2.id})

        assertTaxClosingAvailable(False, main_company)
        assertTaxClosingAvailable(True, main_company + branch_1 + branch_1_1 + branch_2 + branch_2_1, export_main_company=main_company)
        assertTaxClosingAvailable(True, branch_2 + branch_2_1 + main_company + branch_1 + branch_1_1, export_main_company=branch_2)
        assertTaxClosingAvailable(True, main_company + branch_1 + branch_1_1, export_main_company=main_company)
        assertTaxClosingAvailable(False, main_company + branch_1)
        assertTaxClosingAvailable(False, branch_1 + branch_1_1)
        assertTaxClosingAvailable(True, branch_1 + main_company + branch_1_1, export_main_company=main_company)
        assertTaxClosingAvailable(True, branch_2 + main_company + branch_2_1, export_main_company=branch_2)
        assertTaxClosingAvailable(False, branch_2_1)

    def test_tax_report_fpos_domestic(self):
        """ Test tax report's content for 'domestic' foreign VAT fiscal position option.
        """
        options = self._generate_options(
            self.basic_tax_report, fields.Date.from_string('2021-01-01'), fields.Date.from_string('2021-03-31'),
            {'fiscal_position': 'domestic'}
        )
        self.assertLinesValues(
            self.basic_tax_report._get_lines(options),
            #   Name                                                          Balance
            [0,                                                               1],
            [
                # out_invoice
                (f'{self.test_fpos_tax_sale.id}-invoice-base',             200 ),
                (f'{self.test_fpos_tax_sale.id}-invoice-30',                30 ),
                (f'{self.test_fpos_tax_sale.id}-invoice-70',                70 ),
                (f'{self.test_fpos_tax_sale.id}-invoice--10',              -10 ),

                # out_refund
                (f'{self.test_fpos_tax_sale.id}-refund-base',              -20 ),
                (f'{self.test_fpos_tax_sale.id}-refund-30',                 -3 ),
                (f'{self.test_fpos_tax_sale.id}-refund-70',                 -7 ),
                (f'{self.test_fpos_tax_sale.id}-refund--10',                 1 ),

                # in_invoice
                (f'{self.test_fpos_tax_purchase.id}-invoice-base',         400 ),
                (f'{self.test_fpos_tax_purchase.id}-invoice-10',            20 ),
                (f'{self.test_fpos_tax_purchase.id}-invoice-60',           120 ),
                (f'{self.test_fpos_tax_purchase.id}-invoice--5',           -10 ),

                # in_refund
                (f'{self.test_fpos_tax_purchase.id}-refund-base',          -60 ),
                (f'{self.test_fpos_tax_purchase.id}-refund-10',             -3 ),
                (f'{self.test_fpos_tax_purchase.id}-refund-60',            -18 ),
                (f'{self.test_fpos_tax_purchase.id}-refund--5',             1.5),
            ],
            options,
        )

    def test_tax_report_fpos_foreign(self):
        """ Test tax report's content with a foreign VAT fiscal position.
        """
        options = self._generate_options(
            self.basic_tax_report, fields.Date.from_string('2021-01-01'), fields.Date.from_string('2021-03-31'),
            {'fiscal_position': self.foreign_vat_fpos.id}
        )
        self.assertLinesValues(
            self.basic_tax_report._get_lines(options),
            #   Name                                                          Balance
            [0,                                                               1],
            [
                # out_invoice
                (f'{self.test_fpos_tax_sale.id}-invoice-base',              800),
                (f'{self.test_fpos_tax_sale.id}-invoice-30',                120),
                (f'{self.test_fpos_tax_sale.id}-invoice-70',                280),
                (f'{self.test_fpos_tax_sale.id}-invoice--10',               -40),

                # out_refund
                (f'{self.test_fpos_tax_sale.id}-refund-base',              -200),
                (f'{self.test_fpos_tax_sale.id}-refund-30',                 -30),
                (f'{self.test_fpos_tax_sale.id}-refund-70',                 -70),
                (f'{self.test_fpos_tax_sale.id}-refund--10',                 10),

                # in_invoice
                (f'{self.test_fpos_tax_purchase.id}-invoice-base',         1000),
                (f'{self.test_fpos_tax_purchase.id}-invoice-10',             50),
                (f'{self.test_fpos_tax_purchase.id}-invoice-60',            300),
                (f'{self.test_fpos_tax_purchase.id}-invoice--5',            -25),

                # in_refund
                (f'{self.test_fpos_tax_purchase.id}-refund-base',          -600),
                (f'{self.test_fpos_tax_purchase.id}-refund-10',             -30),
                (f'{self.test_fpos_tax_purchase.id}-refund-60',            -180),
                (f'{self.test_fpos_tax_purchase.id}-refund--5',              15),
            ],
            options,
        )

    def test_tax_report_fpos_everything(self):
        """ Test tax report's content for 'all' foreign VAT fiscal position option.
        """
        options = self._generate_options(
            self.basic_tax_report, fields.Date.from_string('2021-01-01'), fields.Date.from_string('2021-03-31'),
            {'fiscal_position': 'all'}
        )
        self.assertLinesValues(
            self.basic_tax_report._get_lines(options),
            #   Name                                                          Balance
            [0,                                                               1],
            [
                # out_invoice
                (f'{self.test_fpos_tax_sale.id}-invoice-base',            1000 ),
                (f'{self.test_fpos_tax_sale.id}-invoice-30',               150 ),
                (f'{self.test_fpos_tax_sale.id}-invoice-70',               350 ),
                (f'{self.test_fpos_tax_sale.id}-invoice--10',              -50 ),

                # out_refund
                (f'{self.test_fpos_tax_sale.id}-refund-base',             -220 ),
                (f'{self.test_fpos_tax_sale.id}-refund-30',                -33 ),
                (f'{self.test_fpos_tax_sale.id}-refund-70',                -77 ),
                (f'{self.test_fpos_tax_sale.id}-refund--10',                11 ),

                # in_invoice
                (f'{self.test_fpos_tax_purchase.id}-invoice-base',        1400 ),
                (f'{self.test_fpos_tax_purchase.id}-invoice-10',            70 ),
                (f'{self.test_fpos_tax_purchase.id}-invoice-60',           420 ),
                (f'{self.test_fpos_tax_purchase.id}-invoice--5',           -35 ),

                # in_refund
                (f'{self.test_fpos_tax_purchase.id}-refund-base',         -660 ),
                (f'{self.test_fpos_tax_purchase.id}-refund-10',            -33 ),
                (f'{self.test_fpos_tax_purchase.id}-refund-60',           -198 ),
                (f'{self.test_fpos_tax_purchase.id}-refund--5',            16.5),
            ],
            options,
        )

    def test_tax_report_single_fpos(self):
        """ When opening the tax report from a foreign country for which there exists only one
        foreing VAT fiscal position, this fiscal position should be selected by default in the
        report's options.
        """
        new_tax_report = self.env['account.report'].create({
            'name': "",
            'country_id': self.foreign_country.id,
            'root_report_id': self.env.ref("account.generic_tax_report").id,
            'column_ids': [Command.create({'name': 'balance', 'sequence': 1, 'expression_label': 'balance'})]
        })
        foreign_vat_fpos = self.env['account.fiscal.position'].create({
            'name': "Test fpos",
            'country_id': self.foreign_country.id,
            'foreign_vat': '422211',
        })
        options = self._generate_options(new_tax_report, fields.Date.from_string('2021-01-01'), fields.Date.from_string('2021-03-31'))
        self.assertEqual(options['fiscal_position'], foreign_vat_fpos.id, "When only one VAT fiscal position is available for a non-domestic country, it should be chosen by default")

    def test_tax_report_grid(self):
        company = self.company_data['company']

        # We generate a tax report with the following layout
        #/Base
        #   - Base 42%
        #   - Base 11%
        #/Tax
        #   - Tax 42%
        #       - 10.5%
        #       - 31.5%
        #   - Tax 11%
        #/Tax difference (42% - 11%)

        tax_report = self.env['account.report'].create({
            'name': 'Test',
            'country_id': company.account_fiscal_country_id.id,
            'root_report_id': self.env.ref("account.generic_tax_report").id,
            'column_ids': [Command.create({'name': 'balance', 'sequence': 1, 'expression_label': 'balance'})]
        })

        # We create the lines in a different order from the one they have in report,
        # so that we ensure sequence is taken into account properly when rendering the report
        tax_section = self._create_tax_report_line('Tax', tax_report, sequence=4, formula="tax_42.balance + tax_11.balance + tax_neg_10.balance")
        base_section = self._create_tax_report_line('Base', tax_report, sequence=1, formula="base_11.balance + base_42.balance")
        base_42_line = self._create_tax_report_line('Base 42%', tax_report, sequence=2, parent_line=base_section, code='base_42', tag_name='base_42')
        base_11_line = self._create_tax_report_line('Base 11%', tax_report, sequence=3, parent_line=base_section, code='base_11', tag_name='base_11')
        tax_42_section = self._create_tax_report_line('Tax 42%', tax_report, sequence=5, parent_line=tax_section, code='tax_42', formula='tax_31_5.balance + tax_10_5.balance')
        tax_31_5_line = self._create_tax_report_line('Tax 31.5%', tax_report, sequence=7, parent_line=tax_42_section, code='tax_31_5', tag_name='tax_31_5')
        tax_10_5_line = self._create_tax_report_line('Tax 10.5%', tax_report, sequence=6, parent_line=tax_42_section, code='tax_10_5', tag_name='tax_10_5')
        tax_11_line = self._create_tax_report_line('Tax 11%', tax_report, sequence=8, parent_line=tax_section, code='tax_11', tag_name='tax_11')
        tax_neg_10_line = self._create_tax_report_line('Tax -10%', tax_report, sequence=9, parent_line=tax_section, code='tax_neg_10', tag_name='tax_neg_10')
        self._create_tax_report_line('Tax difference (42%-11%)', tax_report, sequence=10, formula='tax_42.balance - tax_11.balance')

        # Create two taxes linked to report lines
        tax_11 = self.env['account.tax'].create({
            'name': 'Impôt sur les revenus',
            'amount': '11',
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'invoice_repartition_line_ids': [
                Command.create({
                    'repartition_type': 'base',
                    'tag_ids': self._get_tag_ids("+", base_11_line.expression_ids),
                }),
                Command.create({
                    'repartition_type': 'tax',
                    'tag_ids': self._get_tag_ids("+", tax_11_line.expression_ids),
                }),
            ],
            'refund_repartition_line_ids': [
                Command.create({
                    'repartition_type': 'base',
                    'tag_ids': self._get_tag_ids("-", base_11_line.expression_ids),
                }),
                Command.create({
                    'repartition_type': 'tax',
                    'tag_ids': self._get_tag_ids("-", tax_11_line.expression_ids),
                }),
            ],
        })

        tax_42 = self.env['account.tax'].create({
            'name': 'Impôt sur les revenants',
            'amount': '42',
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'invoice_repartition_line_ids': [
                Command.create({
                    'repartition_type': 'base',
                    'tag_ids': self._get_tag_ids("+", base_42_line.expression_ids),
                }),

                Command.create({
                    'factor_percent': 25,
                    'repartition_type': 'tax',
                    'tag_ids': self._get_tag_ids("+", tax_10_5_line.expression_ids),
                }),

                Command.create({
                    'factor_percent': 75,
                    'repartition_type': 'tax',
                    'tag_ids': self._get_tag_ids("+", tax_31_5_line.expression_ids),
                }),

                Command.create({
                    'factor_percent': -10,
                    'repartition_type': 'tax',
                    'tag_ids': self._get_tag_ids("-", tax_neg_10_line.expression_ids),
                }),
            ],
            'refund_repartition_line_ids': [
                Command.create({
                    'repartition_type': 'base',
                    'tag_ids': self._get_tag_ids("-", base_42_line.expression_ids),
                }),

                Command.create({
                    'factor_percent': 25,
                    'repartition_type': 'tax',
                    'tag_ids': self._get_tag_ids("-", tax_10_5_line.expression_ids),
                }),

                Command.create({
                    'factor_percent': 75,
                    'repartition_type': 'tax',
                    'tag_ids': self._get_tag_ids("-", tax_31_5_line.expression_ids),
                }),

                Command.create({
                    'factor_percent': -10,
                    'repartition_type': 'tax',
                    'tag_ids': self._get_tag_ids("+", tax_neg_10_line.expression_ids),
                }),
            ],
        })

        # Create an invoice using the tax we just made
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'Turlututu',
                'price_unit': 100.0,
                'quantity': 1,
                'account_id': self.company_data['default_account_revenue'].id,
                'tax_ids': [Command.set((tax_11 + tax_42).ids)],
            })],
        })
        invoice.action_post()

        # Generate the report and check the results
        report = tax_report
        options = self._generate_options(report, invoice.date, invoice.date)

        # Invalidate the cache to ensure the lines will be fetched in the right order.
        self.env.invalidate_all()

        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                        Balance
            [   0,                                             1  ],
            [
                ('Base',                                    200   ),
                ('Base 42%',                                100   ),
                ('Base 11%',                                100   ),
                ('Total Base',                              200   ),

                ('Tax',                                      57.20),
                ('Tax 42%',                                  42   ),
                ('Tax 10.5%',                                10.5 ),
                ('Tax 31.5%',                                31.5 ),
                ('Total Tax 42%',                            42   ),

                ('Tax 11%',                                  11   ),
                ('Tax -10%',                                  4.2 ),
                ('Total Tax',                                57.2 ),

                ('Tax difference (42%-11%)',                 31   ),
            ],
            options,
        )

        # We refund the invoice
        refund_wizard = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=invoice.ids).create({
            'reason': 'Test refund tax repartition',
            'journal_id': invoice.journal_id.id,
            'date': invoice.date,
        })
        refund_wizard.modify_moves()

        # We check the taxes on refund have impacted the report properly (everything should be 0)
        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                         Balance
            [   0,                                               1],
            [
                ('Base',                                       0.0),
                ('Base 42%',                                   0.0),
                ('Base 11%',                                   0.0),
                ('Total Base',                                 0.0),

                ('Tax',                                        0.0),
                ('Tax 42%',                                    0.0),
                ('Tax 10.5%',                                  0.0),
                ('Tax 31.5%',                                  0.0),
                ('Total Tax 42%',                              0.0),

                ('Tax 11%',                                    0.0),
                ('Tax -10%',                                   0.0),
                ('Total Tax',                                  0.0),

                ('Tax difference (42%-11%)',                   0.0),
            ],
            options,
        )

    def _create_caba_taxes_for_report_lines(self, report_lines_dict, company):
        """ Creates cash basis taxes with a specific test repartition and maps them to
        the provided tax_report lines.

        :param report_lines_dict:  A dictionnary mapping tax_type_use values to
                                   tax report lines records
        :param company:            The company to create the test tags for

        :return:                   The created account.tax objects
        """
        return self.env['account.tax'].create([
            {
                'name': 'Impôt sur tout ce qui bouge',
                'amount': '20',
                'amount_type': 'percent',
                'type_tax_use': tax_type,
                'tax_exigibility': 'on_payment',
                'invoice_repartition_line_ids': [
                    Command.create({
                        'repartition_type': 'base',
                        'tag_ids': self._get_tag_ids("+", report_line.expression_ids),
                    }),
                    Command.create({
                        'factor_percent': 25,
                        'repartition_type': 'tax',
                        'tag_ids': self._get_tag_ids("+", report_line.expression_ids),
                    }),
                    Command.create({
                        'factor_percent': 75,
                        'repartition_type': 'tax',
                        'tag_ids': self._get_tag_ids("+", report_line.expression_ids),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.create({
                        'repartition_type': 'base',
                        'tag_ids': self._get_tag_ids("-", report_line.expression_ids),
                    }),
                    Command.create({
                        'factor_percent': 25,
                        'repartition_type': 'tax',
                        'tag_ids': self._get_tag_ids("-", report_line.expression_ids),
                    }),
                    Command.create({
                        'factor_percent': 75,
                        'repartition_type': 'tax',
                    }),
                ],
            }
            for tax_type, report_line in report_lines_dict.items()
        ])

    def _create_taxes_for_report_lines(self, report_lines_dict, company):
        return self.env['account.tax'].create([
            {
                'name': 'Impôt sur tout ce qui bouge',
                'amount': '20',
                'amount_type': 'percent',
                'type_tax_use': tax_type,
                'invoice_repartition_line_ids': [
                    Command.create({
                        'repartition_type': 'base',
                        'tag_ids': self._get_tag_ids("+", report_line[0].expression_ids),
                    }),
                    Command.create({
                        'repartition_type': 'tax',
                        'tag_ids': self._get_tag_ids("+", report_line[1].expression_ids),
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.create({
                        'repartition_type': 'base',
                        'tag_ids': self._get_tag_ids("+", report_line[0].expression_ids),
                    }),
                    Command.create({
                        'repartition_type': 'tax',
                        'tag_ids': self._get_tag_ids("+", report_line[1].expression_ids),
                    }),
                ],
            }
            for tax_type, report_line in report_lines_dict.items()
        ])


    def _run_caba_generic_test(self, expected_columns, expected_lines, on_invoice_created=None, on_all_invoices_created=None, invoice_generator=None):
        """ Generic test function called by several cash basis tests.

        This function creates a new sale and purchase tax, each associated with
        a new tax report line using _create_caba_taxes_for_report_lines.
        It then creates an invoice AND a refund for each of these tax, and finally
        compare the tax report to the expected values, passed in parameters.

        Since _create_caba_taxes_for_report_lines creates asymmetric taxes (their 75%
        repartition line does not impact the report line at refund), we can be sure this
        function helper gives a complete coverage, and does not shadow any result due, for
        example, to some undesired swapping between debit and credit.

        :param expected_columns:          The columns we want the final tax report to contain

        :param expected_lines:            The lines we want the final tax report to contain

        :param on_invoice_created:        A function to be called when a single invoice has
                                          just been created, taking the invoice as a parameter
                                          (This can be used to reconcile the invoice with something, for example)

        :param on_all_invoices_created:   A function to be called when all the invoices corresponding
                                          to a tax type have been created, taking the
                                          recordset of all these invoices as a parameter
                                          (Use it to reconcile invoice and credit note together, for example)

        :param invoice_generator:         A function used to generate an invoice. A default
                                          one is called if none is provided, creating
                                          an invoice with a single line amounting to 100,
                                          with the provided tax set on it.
        """
        def default_invoice_generator(inv_type, partner, account, date, tax):
            return self.env['account.move'].create({
                'move_type': inv_type,
                'partner_id': partner.id,
                'invoice_date': date,
                'invoice_line_ids': [Command.create({
                    'name': 'test',
                    'quantity': 1,
                    'account_id': account.id,
                    'price_unit': 100,
                    'tax_ids': [Command.set(tax.ids)],
                })],
            })

        today = fields.Date.today()

        company = self.company_data['company']
        company.tax_exigibility = True
        partner = self.env['res.partner'].create({'name': 'Char Aznable'})

        # Create a tax report
        tax_report = self.env['account.report'].create({
            'name': 'Test',
            'country_id': self.fiscal_country.id,
            'root_report_id': self.env.ref("account.generic_tax_report").id,
            'column_ids': [Command.create({'name': 'balance', 'sequence': 1, 'expression_label': 'balance'})]
        })

        # We create some report lines
        report_lines_dict = {
            'sale': self._create_tax_report_line('Sale', tax_report, sequence=1, tag_name='sale'),
            'purchase': self._create_tax_report_line('Purchase', tax_report, sequence=2, tag_name='purchase'),
        }

        # We create a sale and a purchase tax, linked to our report lines' tags
        taxes = self._create_caba_taxes_for_report_lines(report_lines_dict, company)


        # Create invoice and refund using the tax we just made
        invoice_types = {
            'sale': ('out_invoice', 'out_refund'),
            'purchase': ('in_invoice', 'in_refund')
        }

        account_types = {
            'sale': 'income',
            'purchase': 'expense',
        }
        for tax in taxes:
            invoices = self.env['account.move']
            account = self.env['account.account'].search([('company_id', '=', company.id), ('account_type', '=', account_types[tax.type_tax_use])], limit=1)
            for inv_type in invoice_types[tax.type_tax_use]:
                invoice = (invoice_generator or default_invoice_generator)(inv_type, partner, account, today, tax)
                invoice.action_post()
                invoices += invoice

                if on_invoice_created:
                    on_invoice_created(invoice)

            if on_all_invoices_created:
                on_all_invoices_created(invoices)

        # Generate the report and check the results
        # We check the taxes on invoice have impacted the report properly
        options = self._generate_options(tax_report, date_from=today, date_to=today)
        inv_report_lines = tax_report._get_lines(options)
        self.assertLinesValues(inv_report_lines, expected_columns, expected_lines, options)

    def _register_full_payment_for_invoice(self, invoice):
        """ Fully pay the invoice, so that the cash basis entries are created
        """
        self.env['account.payment.register'].with_context(active_ids=invoice.ids, active_model='account.move').create({
            'payment_date': invoice.date,
        })._create_payments()

    @freeze_time('2023-10-05 02:00:00')
    def test_tax_report_grid_cash_basis(self):
        """ Cash basis moves create for taxes based on payments are handled differently
        by the report; we want to ensure their sign is managed properly.
        """
        # 100 (base, invoice) - 100 (base, refund) + 20 (tax, invoice) - 5 (25% tax, refund) = 15
        self._run_caba_generic_test(
            #   Name                      Balance
            [   0,                            1],
            [
                ('Sale',                     15),
                ('Purchase',                 15),
            ],
            on_invoice_created=self._register_full_payment_for_invoice
        )

    @freeze_time('2023-10-05 02:00:00')
    def test_tax_report_grid_cash_basis_refund(self):
        """ Cash basis moves create for taxes based on payments are handled differently
        by the report; we want to ensure their sign is managed properly. This
        test runs the case where an invoice is reconciled with a refund (created
        separetely, so not cancelling it).
        """
        def reconcile_opposite_types(invoices):
            """ Reconciles the created invoices with their matching refund.
            """
            invoices.mapped('line_ids').filtered(lambda x: x.account_type in ('asset_receivable', 'liability_payable')).reconcile()

        # 100 (base, invoice) - 100 (base, refund) + 20 (tax, invoice) - 5 (25% tax, refund) = 15
        self._run_caba_generic_test(
            #   Name                      Balance
            [   0,                        1],
            [
                ('Sale',                     15),
                ('Purchase',                 15),
            ],
            on_all_invoices_created=reconcile_opposite_types
        )

    @freeze_time('2023-10-05 02:00:00')
    def test_tax_report_grid_cash_basis_misc_pmt(self):
        """ Cash basis moves create for taxes based on payments are handled differently
        by the report; we want to ensure their sign is managed properly. This
        test runs the case where the invoice is paid with a misc operation instead
        of a payment.
        """
        def reconcile_with_misc_pmt(invoice):
            """ Create a misc operation equivalent to a full payment and reconciles
            the invoice with it.
            """
            # Pay the invoice with a misc operation simulating a payment, so that the cash basis entries are created
            invoice_reconcilable_line = invoice.line_ids.filtered(lambda x: x.account_type in ('liability_payable', 'asset_receivable'))
            account = (invoice.line_ids - invoice_reconcilable_line).account_id
            pmt_move = self.env['account.move'].create({
                'move_type': 'entry',
                'date': invoice.date,
                'line_ids': [Command.create({
                                'account_id': invoice_reconcilable_line.account_id.id,
                                'debit': invoice_reconcilable_line.credit,
                                'credit': invoice_reconcilable_line.debit,
                            }),
                            Command.create({
                                'account_id': account.id,
                                'credit': invoice_reconcilable_line.credit,
                                'debit': invoice_reconcilable_line.debit,
                            })],
            })
            pmt_move.action_post()
            payment_reconcilable_line = pmt_move.line_ids.filtered(lambda x: x.account_type in ('liability_payable', 'asset_receivable'))
            (invoice_reconcilable_line + payment_reconcilable_line).reconcile()

        # 100 (base, invoice) - 100 (base, refund) + 20 (tax, invoice) - 5 (25% tax, refund) = 15
        self._run_caba_generic_test(
            #   Name                      Balance
            [   0,                            1],
            [
                ('Sale',                     15),
                ('Purchase',                 15),
            ],
            on_invoice_created=reconcile_with_misc_pmt
        )

    @freeze_time('2023-10-05 02:00:00')
    def test_caba_no_payment(self):
        """ The cash basis taxes of an unpaid invoice should
        never impact the report.
        """
        self._run_caba_generic_test(
            #   Name                      Balance
            [   0,                            1],
            [
                ('Sale',                    0.0),
                ('Purchase',                0.0),
            ]
        )

    @freeze_time('2023-10-05 02:00:00')
    def test_caba_half_payment(self):
        """ Paying half the amount of the invoice should report half the
        base and tax amounts.
        """
        def register_half_payment_for_invoice(invoice):
            """ Fully pay the invoice, so that the cash basis entries are created
            """
            payment_method_id = self.inbound_payment_method_line if invoice.is_inbound() else self.outbound_payment_method_line
            self.env['account.payment.register'].with_context(active_ids=invoice.ids, active_model='account.move').create({
                'amount': invoice.amount_residual / 2,
                'payment_date': invoice.date,
                'payment_method_line_id': payment_method_id.id,
            })._create_payments()

        # 50 (base, invoice) - 50 (base, refund) + 10 (tax, invoice) - 2.5 (25% tax, refund) = 7.5
        self._run_caba_generic_test(
            #   Name                     Balance
            [   0,                            1],
            [
                ('Sale',                    7.5),
                ('Purchase',                7.5),
            ],
            on_invoice_created=register_half_payment_for_invoice
        )

    def test_caba_mixed_generic_report(self):
        """ Tests mixing taxes with different tax exigibilities displays correct amounts
        in the generic tax report.
        """
        self.env.company.tax_exigibility = True
        # Create taxes
        regular_tax = self.env['account.tax'].create({
            'name': 'Regular',
            'amount': 42,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            # We use default repartition: 1 base line, 1 100% tax line
        })

        caba_tax = self.env['account.tax'].create({
            'name': 'Cash Basis',
            'amount': 10,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'tax_exigibility': 'on_payment',
            # We use default repartition: 1 base line, 1 100% tax line
        })

        # Create an invoice using them, and post it
        invoice = self.init_invoice(
            'out_invoice',
            invoice_date='2021-07-01',
            post=True,
            amounts=[100],
            taxes=regular_tax + caba_tax,
            company=self.company_data['company'],
        )

        # Check the report only contains non-caba things
        report = self.env.ref("account.generic_tax_report")
        options = self._generate_options(report, invoice.date, invoice.date)
        self.assertLinesValues(
            report._get_lines(options),
            #   Name                         Net               Tax
            [   0,                             1,                2],
            [
                ("Sales",                     '',               42),
                ("Regular (42.0%)",          100,               42),
                ("Total Sales",               '',               42),
            ],
            options,
        )

        # Pay half of the invoice
        self.env['account.payment.register'].with_context(active_ids=invoice.ids, active_model='account.move').create({
            'amount': 76,
            'payment_date': invoice.date,
            'payment_method_line_id': self.outbound_payment_method_line.id,
        })._create_payments()

        # Check the report again: half the cash basis should be there
        self.assertLinesValues(
            report._get_lines(options),
            #   Name                          Net               Tax
            [   0,                              1,               2],
            [
                ("Sales",                      '',              47),
                ("Regular (42.0%)",           100,              42),
                ("Cash Basis (10.0%)",         50,               5),
                ("Total Sales",                '',              47),
            ],
            options,
        )

        # Pay the rest
        self.env['account.payment.register'].with_context(active_ids=invoice.ids, active_model='account.move').create({
            'amount': 76,
            'payment_date': invoice.date,
            'payment_method_line_id': self.outbound_payment_method_line.id,
        })._create_payments()

        # Check everything is in the report
        self.assertLinesValues(
            report._get_lines(options),
            #   Name                          Net              Tax
            [   0,                              1,               2],
            [
                ("Sales",                      '',              52),
                ("Regular (42.0%)",           100,              42),
                ("Cash Basis (10.0%)",        100,              10),
                ("Total Sales",                '',              52),
            ],
            options,
        )

    def test_tax_report_mixed_exigibility_affect_base_generic_invoice(self):
        """ Tests mixing caba and non-caba taxes with one of them affecting the base
        of the other worcs properly on invoices for generic report.
        """
        self.env.company.tax_exigibility = True
        # Create taxes
        regular_tax = self.env['account.tax'].create({
            'name': 'Regular',
            'amount': 42,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'include_base_amount': True,
            'sequence': 0,
            # We use default repartition: 1 base line, 1 100% tax line
        })

        caba_tax = self.env['account.tax'].create({
            'name': 'Cash Basis',
            'amount': 10,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'tax_exigibility': 'on_payment',
            'include_base_amount': True,
            'sequence': 1,
            # We use default repartition: 1 base line, 1 100% tax line
        })

        report = self.env.ref("account.generic_tax_report")
        # Case 1: on_invoice tax affecting on_payment tax's base
        self._run_check_suite_mixed_exigibility_affect_base(
            regular_tax + caba_tax,
            '2021-07-01',
            report,
            # Name,                          Net,               Tax
            [   0,                             1,                2],
            # Before payment
            [
                ("Sales",                     '',            42   ),
                ("Regular (42.0%)",          100,            42   ),
                ("Total Sales",               '',            42   ),
            ],
            # After paying 30%
            [
                ("Sales",                     '',            46.26),
                ("Regular (42.0%)",          100,            42   ),
                ("Cash Basis (10.0%)",        42.6,           4.26),
                ("Total Sales",               '',            46.26),
            ],
            # After full payment
            [
                ("Sales",                     '',             56.2),
                ("Regular (42.0%)",          100,             42  ),
                ("Cash Basis (10.0%)",       142,             14.2),
                ("Total Sales",               '',             56.2),
            ]
        )

        # Change sequence
        caba_tax.sequence = 0
        regular_tax.sequence = 1

        # Case 2: on_payment tax affecting on_invoice tax's base
        self._run_check_suite_mixed_exigibility_affect_base(
            regular_tax + caba_tax,
            '2021-07-02',
            report,
            #   Name                         Net                Tax
            [   0,                             1,                2],
            # Before payment
            [
                ("Sales",                     '',             46.2),
                ("Regular (42.0%)",          110,             46.2),
                ("Total Sales",               '',             46.2),
            ],
            # After paying 30%
            [
                ("Sales",                     '',             49.2),
                ("Cash Basis (10.0%)",        30,              3  ),
                ("Regular (42.0%)",          110,             46.2),
                ("Total Sales",               '',             49.2),
            ],
            # After full payment
            [
                ("Sales",                     '',             56.2),
                ("Cash Basis (10.0%)",       100,             10  ),
                ("Regular (42.0%)",          110,             46.2),
                ("Total Sales",               '',             56.2),
            ]
        )

    def test_tax_report_mixed_exigibility_affect_base_tags(self):
        """ Tests mixing caba and non-caba taxes with one of them affecting the base
        of the other worcs properly on invoices for tax report.
        """
        self.env.company.tax_exigibility = True
        # Create taxes
        tax_report = self.env['account.report'].create({
            'name': "Sokovia Accords",
            'country_id': self.fiscal_country.id,
            'root_report_id': self.env.ref("account.generic_tax_report").id,
            'column_ids': [Command.create({'name': 'balance', 'sequence': 1, 'expression_label': 'balance'})],
        })

        regular_tax = self._add_basic_tax_for_report(tax_report, 42, 'sale', self.tax_group_1, [(100, None, True)])
        caba_tax = self._add_basic_tax_for_report(tax_report, 10, 'sale', self.tax_group_1, [(100, None, True)])

        regular_tax.write({
            'include_base_amount': True,
            'sequence': 0,
        })
        caba_tax.write({
            'include_base_amount': True,
            'tax_exigibility': 'on_payment',
            'sequence': 1,
        })

        # Case 1: on_invoice tax affecting on_payment tax's base
        self._run_check_suite_mixed_exigibility_affect_base(
            regular_tax + caba_tax,
            '2021-07-01',
            tax_report,
            #   Name                                       Balance
            [   0,                                               1],
            # Before payment
            [
                (f'{regular_tax.id}-invoice-base',          100   ),
                (f'{regular_tax.id}-invoice-100',            42   ),
                (f'{regular_tax.id}-refund-base',             0.0 ),
                (f'{regular_tax.id}-refund-100',              0.0 ),

                (f'{caba_tax.id}-invoice-base',               0.0 ),
                (f'{caba_tax.id}-invoice-100',                0.0 ),
                (f'{caba_tax.id}-refund-base',                0.0 ),
                (f'{caba_tax.id}-refund-100',                 0.0 ),
            ],
            # After paying 30%
            [
                (f'{regular_tax.id}-invoice-base',          100   ),
                (f'{regular_tax.id}-invoice-100',            42   ),
                (f'{regular_tax.id}-refund-base',             0.0 ),
                (f'{regular_tax.id}-refund-100',              0.0 ),

                (f'{caba_tax.id}-invoice-base',              42.6 ),
                (f'{caba_tax.id}-invoice-100',                4.26),
                (f'{caba_tax.id}-refund-base',                0.0 ),
                (f'{caba_tax.id}-refund-100',                 0.0 ),
            ],
            # After full payment
            [
                (f'{regular_tax.id}-invoice-base',          100   ),
                (f'{regular_tax.id}-invoice-100',            42   ),
                (f'{regular_tax.id}-refund-base',             0.0 ),
                (f'{regular_tax.id}-refund-100',              0.0 ),

                (f'{caba_tax.id}-invoice-base',             142   ),
                (f'{caba_tax.id}-invoice-100',               14.2 ),
                (f'{caba_tax.id}-refund-base',                0.0 ),
                (f'{caba_tax.id}-refund-100',                 0.0 ),
            ],
        )

        # Change sequence
        caba_tax.sequence = 0
        regular_tax.sequence = 1

        # Case 2: on_payment tax affecting on_invoice tax's base
        self._run_check_suite_mixed_exigibility_affect_base(
            regular_tax + caba_tax,
            '2021-07-02',
            tax_report,
            #   Name                                       Balance
            [   0,                                               1],
            # Before payment
            [
                (f'{regular_tax.id}-invoice-base',           110  ),
                (f'{regular_tax.id}-invoice-100',             46.2),
                (f'{regular_tax.id}-refund-base',              0.0),
                (f'{regular_tax.id}-refund-100',               0.0),

                (f'{caba_tax.id}-invoice-base',                0.0),
                (f'{caba_tax.id}-invoice-100',                 0.0),
                (f'{caba_tax.id}-refund-base',                 0.0),
                (f'{caba_tax.id}-refund-100',                  0.0),
            ],
            # After paying 30%
            [
                (f'{regular_tax.id}-invoice-base',           110  ),
                (f'{regular_tax.id}-invoice-100',             46.2),
                (f'{regular_tax.id}-refund-base',              0.0),
                (f'{regular_tax.id}-refund-100',               0.0),

                (f'{caba_tax.id}-invoice-base',               30  ),
                (f'{caba_tax.id}-invoice-100',                 3  ),
                (f'{caba_tax.id}-refund-base',                 0.0),
                (f'{caba_tax.id}-refund-100',                  0.0),
            ],
            # After full payment
            [
                (f'{regular_tax.id}-invoice-base',          110   ),
                (f'{regular_tax.id}-invoice-100',            46.2 ),
                (f'{regular_tax.id}-refund-base',             0.0 ),
                (f'{regular_tax.id}-refund-100',              0.0 ),

                (f'{caba_tax.id}-invoice-base',             100   ),
                (f'{caba_tax.id}-invoice-100',               10   ),
                (f'{caba_tax.id}-refund-base',                0.0 ),
                (f'{caba_tax.id}-refund-100',                 0.0 ),
            ],
        )

    def _run_check_suite_mixed_exigibility_affect_base(self, taxes, invoice_date, report, report_columns, vals_not_paid, vals_30_percent_paid, vals_fully_paid):
        # Create an invoice using them
        invoice = self.init_invoice(
            'out_invoice',
            invoice_date=invoice_date,
            post=True,
            amounts=[100],
            taxes=taxes,
            company=self.company_data['company'],
        )

        # Check the report
        report_options = self._generate_options(report, invoice.date, invoice.date)
        self.assertLinesValues(report._get_lines(report_options), report_columns, vals_not_paid, report_options)

        # Pay 30% of the invoice
        self.env['account.payment.register'].with_context(active_ids=invoice.ids, active_model='account.move').create({
            'amount': invoice.amount_residual * 0.3,
            'payment_date': invoice.date,
            'payment_method_line_id': self.outbound_payment_method_line.id,
        })._create_payments()

        # Check the report again: 30% of the caba amounts should be there
        self.assertLinesValues(report._get_lines(report_options), report_columns, vals_30_percent_paid, report_options)

        # Pay the rest: total caba amounts should be there
        self.env['account.payment.register'].with_context(active_ids=invoice.ids, active_model='account.move').create({
            'payment_date': invoice.date,
            'payment_method_line_id': self.outbound_payment_method_line.id,
        })._create_payments()

        # Check the report
        self.assertLinesValues(report._get_lines(report_options), report_columns, vals_fully_paid, report_options)

    def test_caba_always_exigible(self):
        """ Misc operations without payable nor receivable lines must always be exigible,
        whatever the tax_exigibility configured on their taxes.
        """
        tax_report = self.env['account.report'].create({
            'name': "Laplace's Box",
            'country_id': self.fiscal_country.id,
            'root_report_id': self.env.ref("account.generic_tax_report").id,
            'column_ids': [Command.create({'name': 'balance', 'sequence': 1, 'expression_label': 'balance'})],
        })

        regular_tax = self._add_basic_tax_for_report(tax_report, 42, 'sale', self.tax_group_1, [(100, None, True)])
        caba_tax = self._add_basic_tax_for_report(tax_report, 10, 'sale', self.tax_group_1, [(100, None, True)])

        regular_tax.write({
            'include_base_amount': True,
            'sequence': 0,
        })
        caba_tax.write({
            'tax_exigibility': 'on_payment',
            'sequence': 1,
        })

        # Create a misc operation using various combinations of our taxes
        move = self.env['account.move'].create({
            'date': '2021-08-01',
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                Command.create({
                    'name': "Test with %s" % ', '.join(taxes.mapped('name')),
                    'account_id': self.company_data['default_account_revenue'].id,
                    'credit': 100,
                    'tax_ids': [Command.set(taxes.ids)],
                })
                for taxes in (caba_tax, regular_tax, caba_tax + regular_tax)
            ] + [
                Command.create({
                    'name': "Balancing line",
                    'account_id': self.company_data['default_account_assets'].id,
                    'debit': 408.2,
                    'tax_ids': [],
                })
            ]
        })

        move.action_post()

        self.assertTrue(move.always_tax_exigible, "A move without payable/receivable line should always be exigible, whatever its taxes.")

        # Check tax report by grid
        report_options = self._generate_options(tax_report, move.date, move.date)
        self.assertLinesValues(
            tax_report._get_lines(report_options),
            #   Name                                        Balance
            [   0,                                               1],
            [
                (f'{regular_tax.id}-invoice-base',           200  ),
                (f'{regular_tax.id}-invoice-100',             84  ),
                (f'{regular_tax.id}-refund-base',              0.0),
                (f'{regular_tax.id}-refund-100',               0.0),

                (f'{caba_tax.id}-invoice-base',              242  ),
                (f'{caba_tax.id}-invoice-100',                24.2),
                (f'{caba_tax.id}-refund-base',                 0.0),
                (f'{caba_tax.id}-refund-100',                  0.0),
            ],
            report_options,
        )


        # Check generic tax report
        tax_report = self.env.ref("account.generic_tax_report")
        report_options = self._generate_options(tax_report, move.date, move.date)
        self.assertLinesValues(
            tax_report._get_lines(report_options),
            #   Name                               Net           Tax
            [   0,                                   1,           2],
            [
                ("Sales",                           '',       108.2),
                (f"{regular_tax.name} (42.0%)",    200,        84  ),
                (f"{caba_tax.name} (10.0%)",       242,        24.2),
                ("Total Sales",                     '',       108.2),
            ],
            report_options,
        )

    @freeze_time('2023-10-05 02:00:00')
    def test_tax_report_grid_caba_negative_inv_line(self):
        """ Tests cash basis taxes work properly in case a line of the invoice
        has been made with a negative quantities and taxes (causing debit and
        credit to be inverted on the base line).
        """
        def neg_line_invoice_generator(inv_type, partner, account, date, tax):
            """ Invoices created here have a line at 100 with a negative quantity of -1.
            They also required a second line (here 200), so that the invoice doesn't
            have a negative total, but we don't put any tax on it.
            """
            return self.env['account.move'].create({
                'move_type': inv_type,
                'partner_id': partner.id,
                'invoice_date': date,
                'invoice_line_ids': [
                    Command.create({
                        'name': 'test',
                        'quantity': -1,
                        'account_id': account.id,
                        'price_unit': 100,
                        'tax_ids': [Command.set(tax.ids)],
                    }),

                    # Second line, so that the invoice doesn't have a negative total
                    Command.create({
                        'name': 'test',
                        'quantity': 1,
                        'account_id': account.id,
                        'price_unit': 200,
                        'tax_ids': [],
                    }),
                ],
            })

        # -100 (base, invoice) + 100 (base, refund) - 20 (tax, invoice) + 5 (25% tax, refund) = -15
        self._run_caba_generic_test(
            #   Name                      Balance
            [   0,                        1],
            [
                ('Sale',                     -15),
                ('Purchase',                 -15),
            ],
            on_invoice_created=self._register_full_payment_for_invoice,
            invoice_generator=neg_line_invoice_generator,
        )

    def test_fiscal_position_switch_all_option_flow(self):
        """ 'all' fiscal position option sometimes must be reset or enforced in order to keep
        the report consistent. We check those cases here.
        """
        foreign_tax_report = self.env['account.report'].create({
            'name': "",
            'country_id': self.foreign_country.id,
            'root_report_id': self.env.ref("account.generic_tax_report").id,
            'column_ids': [Command.create({'name': 'balance', 'sequence': 1, 'expression_label': 'balance'})],
        })
        foreign_vat_fpos = self.env['account.fiscal.position'].create({
            'name': "Test fpos",
            'country_id': self.foreign_country.id,
            'foreign_vat': '422211',
        })

        # Case 1: 'all' allowed if multiple fpos
        to_check = self.basic_tax_report.get_options({'fiscal_position': 'all', 'selected_variant_id': self.basic_tax_report.id})
        self.assertEqual(to_check['fiscal_position'], 'all', "Opening the report with 'all' fiscal_position option should work if there are fiscal positions for different states in that country")

        # Case 2: 'all' not allowed if domestic and no fpos
        self.foreign_vat_fpos.foreign_vat = None # No unlink because setupClass created some moves with it
        to_check = self.basic_tax_report.get_options({'fiscal_position': 'all', 'selected_variant_id': self.basic_tax_report.id})
        self.assertEqual(to_check['fiscal_position'], 'domestic', "Opening the domestic report with 'all' should change to 'domestic' if there's no state-specific fiscal position in the country")

        # Case 3: 'all' not allowed on foreign report with 1 fpos
        to_check = foreign_tax_report.get_options({'fiscal_position': 'all', 'selected_variant_id': foreign_tax_report.id})
        self.assertEqual(to_check['fiscal_position'], foreign_vat_fpos.id, "Opening a foreign report with only one single fiscal position with 'all' option should change if to only select this fiscal position")

        # Case 4: always 'all' on generic report
        generic_tax_report = self.env.ref("account.generic_tax_report")
        to_check = generic_tax_report.get_options({'fiscal_position': foreign_vat_fpos.id, 'selected_variant_id': generic_tax_report.id})
        self.assertEqual(to_check['fiscal_position'], 'all', "The generic report should always use 'all' fiscal position option.")

    def test_tax_report_multi_inv_line_no_rep_account(self):
        """ Tests the behavior of the tax report when using a tax without any
        repartition account (hence doing its tax lines on the base account),
        and using the tax on two lines (to make sure grouping is handled
        properly by the report).
        We do that for both regular and cash basis taxes.
        """
        # Create taxes
        regular_tax = self.env['account.tax'].create({
            'name': 'Regular',
            'amount': 42,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            # We use default repartition: 1 base line, 1 100% tax line
        })

        caba_tax = self.env['account.tax'].create({
            'name': 'Cash Basis',
            'amount': 42,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'tax_exigibility': 'on_payment',
            # We use default repartition: 1 base line, 1 100% tax line
        })
        self.env.company.tax_exigibility = True

        # Make one invoice of 2 lines for each of our taxes
        invoice_date = fields.Date.from_string('2021-04-01')
        other_account_revenue = self.company_data['default_account_revenue'].copy()

        regular_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': invoice_date,
            'invoice_line_ids': [
                Command.create({
                    'name': 'line 1',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 100,
                    'tax_ids': [Command.set(regular_tax.ids)],
                }),

                Command.create({
                    'name': 'line 2',
                    'account_id': other_account_revenue.id,
                    'price_unit': 100,
                    'tax_ids': [Command.set(regular_tax.ids)],
                })
            ],
        })

        caba_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': invoice_date,
            'invoice_line_ids': [
                Command.create({
                    'name': 'line 1',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 100,
                    'tax_ids': [Command.set(caba_tax.ids)],
                }),

                Command.create({
                    'name': 'line 2',
                    'account_id': other_account_revenue.id,
                    'price_unit': 100,
                    'tax_ids': [Command.set(caba_tax.ids)],
                })
            ],
        })

        # Post the invoices
        regular_invoice.action_post()
        caba_invoice.action_post()

        # Pay cash basis invoice
        self.env['account.payment.register'].with_context(active_ids=caba_invoice.ids, active_model='account.move').create({
            'payment_date': invoice_date,
        })._create_payments()

        # Check the generic report
        report = self.env.ref("account.generic_tax_report")
        options = self._generate_options(report, invoice_date, invoice_date)
        self.assertLinesValues(
            report._get_lines(options),
            #   Name                         Net               Tax
            [   0,                             1,                2],
            [
                ("Sales",                     '',              168),
                ("Regular (42.0%)",          200,               84),
                ("Cash Basis (42.0%)",       200,               84),
                ("Total Sales",               '',              168),
            ],
            options,
        )

    def test_tax_unit(self):
        tax_unit_report = self.env['account.report'].create({
            'name': "And now for something completely different",
            'country_id': self.fiscal_country.id,
            'root_report_id': self.env.ref("account.generic_tax_report").id,
            'column_ids': [Command.create({'name': 'balance', 'sequence': 1, 'expression_label': 'balance'})],
        })

        company_1 = self.company_data['company']
        company_2 = self.company_data_2['company']
        company_data_3 = self.setup_company_data("Company 3", chart_template=company_1.chart_template)
        company_3 = company_data_3['company']
        unit_companies = company_1 + company_2
        all_companies = unit_companies + company_3

        company_2.currency_id = company_1.currency_id

        tax_unit = self.env['account.tax.unit'].create({
            'name': "One unit to rule them all",
            'country_id': self.fiscal_country.id,
            'vat': "DW1234567890",
            'company_ids': [Command.set(unit_companies.ids)],
            'main_company_id': company_1.id,
        })
        tax_group_2 = self._instantiate_basic_test_tax_group(company_2)
        self._instantiate_basic_test_tax_group(company_3)

        created_taxes = {}
        tax_accounts = {}
        invoice_date = fields.Date.from_string('2018-01-01')
        for index, company in enumerate(all_companies):
            # Make sure the fiscal country is what we want
            self.change_company_country(company, self.fiscal_country)

            # Create a tax for this report
            tax_account = self.env['account.account'].create({
                'name': 'Tax unit test tax account',
                'code': 'test.tax.unit',
                'account_type': 'asset_current',
                'company_id': company.id,
            })
            tax_group = self.env['account.tax.group'].search([('company_id', '=', company.id), ('name', '=', 'Test tax group')], limit=1)

            test_tax = self._add_basic_tax_for_report(tax_unit_report, 42, 'sale', tax_group, [(100, tax_account, True)], company=company)
            created_taxes[company] = test_tax
            tax_accounts[company] = tax_account

            # Create an invoice with this tax
            self.init_invoice(
                'out_invoice',
                partner=self.partner_a,
                invoice_date=invoice_date,
                post=True,
                amounts=[100 * (index + 1)],
                taxes=test_tax, company=company
            )

        # Check report content, with various scenarios of active companies
        for active_companies in (company_1, company_2, company_3, unit_companies, all_companies, company_2 + company_3):

            # In the regular flow, selected companies are changed from the selector, in the UI.
            # The tax unit option of the report changes the value of the selector, so it'll
            # always stay consistent with allowed_company_ids.
            options = self._generate_options(
                tax_unit_report.with_context(allowed_company_ids=active_companies.ids),
                invoice_date,
                invoice_date,
                {'fiscal_position': 'domestic'}
            )

            target_unit = tax_unit if company_3 != active_companies[0] else None
            self.assertTrue(
                (not target_unit and not options['available_tax_units']) \
                or (options['available_tax_units'] and any(available_unit['id'] == target_unit.id for available_unit in options['available_tax_units'])),
                "The tax unit should always be available when self.env.company is part of it."
            )

            self.assertEqual(
                options['tax_unit'] != 'company_only',
                active_companies == unit_companies,
                "The tax unit option should only be enabled when all the companies of the unit are selected, and nothing else."
            )

            self.assertLinesValues(
                tax_unit_report.with_context(allowed_company_ids=active_companies.ids)._get_lines(options),
                #   Name                                                          Balance
                [   0,                                                            1],
                [
                    # Company 1
                    (f'{created_taxes[company_1].id}-invoice-base',           100 if company_1 in active_companies else 0.0),
                    (f'{created_taxes[company_1].id}-invoice-100',             42 if company_1 in active_companies else 0.0),
                    (f'{created_taxes[company_1].id}-refund-base',             0.0),
                    (f'{created_taxes[company_1].id}-refund-100',              0.0),

                    # Company 2
                    (f'{created_taxes[company_2].id}-invoice-base',           200 if active_companies == unit_companies or active_companies[0] == company_2 else 0.0),
                    (f'{created_taxes[company_2].id}-invoice-100',             84 if active_companies == unit_companies or active_companies[0] == company_2 else 0.0),
                    (f'{created_taxes[company_2].id}-refund-base',             0.0),
                    (f'{created_taxes[company_2].id}-refund-100',              0.0),

                    # Company 3 (not part of the unit, so always 0 in our cases)
                    (f'{created_taxes[company_3].id}-invoice-base',           300 if company_3 == active_companies[0] else 0.0),
                    (f'{created_taxes[company_3].id}-invoice-100',            126 if company_3 == active_companies[0] else 0.0),
                    (f'{created_taxes[company_3].id}-refund-base',             0.0),
                    (f'{created_taxes[company_3].id}-refund-100',              0.0),
                ],
                options,
            )

        # Check closing for the vat unit
        options = self._generate_options(
            tax_unit_report.with_context(allowed_company_ids=unit_companies.ids),
            invoice_date,
            invoice_date,
            {'tax_report': tax_unit_report.id, 'fiscal_position': 'all'}
        )

        self._assert_vat_closing(tax_unit_report, options, {
            (company_1, self.env['account.fiscal.position']): [
                {'debit': 42,       'credit':  0,       'account_id': tax_accounts[company_1].id},
                {'debit':  0,       'credit': 42,       'account_id': self.tax_group_1.tax_payable_account_id.id},
            ],

            (company_1, self.foreign_vat_fpos): [
                # Don't check accounts here; they are gotten by searching on taxes, basically we don't care about them as it's 0-balanced.
                {'debit':  0,       'credit':  0,},
                {'debit':  0,       'credit':  0,},
            ],

            (company_2, self.env['account.fiscal.position']): [
                {'debit': 84,       'credit':  0,       'account_id': tax_accounts[company_2].id},
                {'debit':  0,       'credit': 84,       'account_id': tax_group_2.tax_payable_account_id.id},
            ],
        })

    def test_tax_unit_auto_fiscal_position(self):
        # setup companies
        company_1 = self.company_data['company']
        company_2 = self.company_data_2['company']
        company_2.currency_id = company_1.currency_id
        company_data_3 = self.setup_company_data("Company 3", chart_template=company_1.chart_template)
        company_3 = company_data_3['company']
        company_data_4 = self.setup_company_data("Company 4", chart_template=company_1.chart_template)
        company_4 = company_data_4['company']
        unit_companies = company_1 + company_2 + company_3
        all_companies = unit_companies + company_4

        # create a tax unit containing 3 companies
        tax_unit = self.env['account.tax.unit'].create({
            'name': "One unit to rule them all",
            'country_id': self.fiscal_country.id,
            'vat': "DW1234567890",
            'company_ids': [Command.set(unit_companies.ids)],
            'main_company_id': company_1.id,
        })
        self.assertFalse(tax_unit.fpos_synced)
        tax_unit.action_sync_unit_fiscal_positions()
        for current_company in unit_companies:
            # verify that partners for other companies in the unit have a fiscal position that removes taxes
            created_fp = tax_unit._get_tax_unit_fiscal_positions(companies=current_company)
            self.assertTrue(created_fp)
            self.assertEqual(
                (unit_companies - current_company).partner_id.with_company(current_company).property_account_position_id,
                created_fp
            )
            self.assertTrue(created_fp.tax_ids.tax_src_id)
            self.assertFalse(created_fp.tax_ids.tax_dest_id)
            self.assertFalse(current_company.partner_id.with_company(current_company).property_account_position_id)
        tax_unit._compute_fiscal_position_completion()
        self.assertTrue(tax_unit.fpos_synced)

        # remove company 3 from the unit and verify that the fiscal positions are removed from the relevant companies
        tax_unit.write({
            'company_ids': [Command.unlink(company_3.id)]
        })
        self.assertFalse(tax_unit.fpos_synced)
        tax_unit.action_sync_unit_fiscal_positions()
        self.assertFalse(company_3.partner_id.with_company(company_1).property_account_position_id)
        self.assertFalse(company_1.partner_id.with_company(company_3).property_account_position_id)
        company_1_fp = tax_unit._get_tax_unit_fiscal_positions(companies=company_1)
        self.assertEqual(company_2.partner_id.with_company(company_1).property_account_position_id, company_1_fp)
        self.assertTrue(tax_unit.fpos_synced)

        # add company 3, remove company 2
        tax_unit.write({
            'company_ids': [Command.link(company_3.id), Command.unlink(company_2.id)]
        })
        self.assertFalse(tax_unit.fpos_synced)
        tax_unit.action_sync_unit_fiscal_positions()
        company_1_fp = tax_unit._get_tax_unit_fiscal_positions(companies=company_1)
        self.assertEqual(company_3.partner_id.with_company(company_1).property_account_position_id, company_1_fp)
        self.assertFalse(company_2.partner_id.with_company(company_1).property_account_position_id)
        self.assertTrue(company_1.partner_id.with_company(company_3).property_account_position_id)

        # remove the fiscal position from the partner of company 1
        company_1.partner_id.with_company(company_3).property_account_position_id = False
        self.assertFalse(tax_unit.fpos_synced)
        tax_unit.action_sync_unit_fiscal_positions()
        self.assertTrue(tax_unit.fpos_synced)

        #replace all companies
        tax_unit.write({
            'company_ids': [Command.set([company_2.id, company_4.id])],
            'main_company_id': company_2.id,
        })
        self.assertFalse(tax_unit.fpos_synced)
        tax_unit.action_sync_unit_fiscal_positions()
        self.assertTrue(tax_unit.fpos_synced)

        # no fiscal positions should exist after deleting the unit
        tax_unit.unlink()
        for company in all_companies:
            self.assertFalse(all_companies.partner_id.with_company(company).property_account_position_id)

    def test_vat_unit_with_foreign_vat_fpos(self):
        # Company 1 has the test country as domestic country, and a foreign VAT fpos in a different province
        company_1 = self.company_data['company']

        # Company 2 belongs to a different country, and has a foreign VAT fpos to the test country, with just one
        # move adding 1000 in the first line of the report.
        company_2 = self.company_data_2['company']
        company_2.currency_id = company_1.currency_id

        foreign_vat_fpos = self.env['account.fiscal.position'].create({
            'name': 'fpos',
            'foreign_vat': 'tagada tsoin tsoin',
            'country_id': self.fiscal_country.id,
            'company_id': company_2.id,
        })

        report_line = self.env['account.report.line'].search([
            ('report_id', '=', self.basic_tax_report.id),
            ('name', '=', f'{self.test_fpos_tax_sale.id}-invoice-base'),
        ])

        plus_tag = report_line.expression_ids._get_matching_tags("+")

        comp2_move = self.env['account.move'].create({
            'journal_id': self.company_data_2['default_journal_misc'].id,
            'date': '2021-02-02',
            'fiscal_position_id': foreign_vat_fpos.id,
            'line_ids': [
                Command.create({
                    'account_id': self.company_data_2['default_account_assets'].id,
                    'credit': 1000,
                }),

                Command.create({
                    'account_id': self.company_data_2['default_account_expense'].id,
                    'debit': 1000,
                    'tax_tag_ids': [Command.set(plus_tag.ids)],
                }),
            ]
        })

        comp2_move.action_post()

        # Both companies belong to a tax unit in test country
        tax_unit = self.env['account.tax.unit'].create({
            'name': "Taxvengers, assemble!",
            'country_id': self.fiscal_country.id,
            'vat': "dudu",
            'company_ids': [Command.set((company_1 + company_2).ids)],
            'main_company_id': company_1.id,
        })

        # Opening the tax report for test country, we should see the same as in test_tax_report_fpos_everything + the 1000 of company 2, whatever the main company

        # Varying the order of the two companies (and hence changing the "main" active one) should make no difference.
        for unit_companies in ((company_1 + company_2), (company_2 + company_1)):
            options = self._generate_options(
                self.basic_tax_report.with_context(allowed_company_ids=unit_companies.ids),
                fields.Date.from_string('2021-01-01'),
                fields.Date.from_string('2021-03-31'),
                {'fiscal_position': 'all'}
            )

            self.assertEqual(options['tax_unit'], tax_unit.id, "The tax unit should have been auto-detected.")

            self.assertLinesValues(
                self.basic_tax_report._get_lines(options),
                #   Name                                                          Balance
                [   0,                                                            1],
                [
                    # out_invoice + 1000 from company_2 on the first line
                    (f'{self.test_fpos_tax_sale.id}-invoice-base',          2000),
                    (f'{self.test_fpos_tax_sale.id}-invoice-30',             150),
                    (f'{self.test_fpos_tax_sale.id}-invoice-70',             350),
                    (f'{self.test_fpos_tax_sale.id}-invoice--10',            -50),

                    #out_refund
                    (f'{self.test_fpos_tax_sale.id}-refund-base',           -220),
                    (f'{self.test_fpos_tax_sale.id}-refund-30',              -33),
                    (f'{self.test_fpos_tax_sale.id}-refund-70',              -77),
                    (f'{self.test_fpos_tax_sale.id}-refund--10',              11),

                    #in_invoice
                    (f'{self.test_fpos_tax_purchase.id}-invoice-base',      1400),
                    (f'{self.test_fpos_tax_purchase.id}-invoice-10',          70),
                    (f'{self.test_fpos_tax_purchase.id}-invoice-60',         420),
                    (f'{self.test_fpos_tax_purchase.id}-invoice--5',         -35),

                    #in_refund
                    (f'{self.test_fpos_tax_purchase.id}-refund-base',       -660),
                    (f'{self.test_fpos_tax_purchase.id}-refund-10',          -33),
                    (f'{self.test_fpos_tax_purchase.id}-refund-60',         -198),
                    (f'{self.test_fpos_tax_purchase.id}-refund--5',         16.5),
                ],
                options,
            )

    @freeze_time('2023-10-05 02:00:00')
    def test_tax_report_with_entries_with_sale_and_purchase_taxes(self):
        """ Ensure signs are managed properly for entry moves.
        This test runs the case where invoice/bill like entries are created and reverted.
        """
        today = fields.Date.today()
        company = self.env.user.company_id
        tax_report = self.env['account.report'].create({
            'name': 'Test',
            'country_id': self.fiscal_country.id,
            'root_report_id': self.env.ref("account.generic_tax_report").id,
            'column_ids': [Command.create({'name': 'balance', 'sequence': 1, 'expression_label': 'balance'})],
        })

        # We create some report lines
        report_lines_dict = {
            'sale': [
                self._create_tax_report_line('Sale base', tax_report, sequence=1, tag_name='sale_b'),
                self._create_tax_report_line('Sale tax', tax_report, sequence=1, tag_name='sale_t'),
            ],
            'purchase': [
                self._create_tax_report_line('Purchase base', tax_report, sequence=2, tag_name='purchase_b'),
                self._create_tax_report_line('Purchase tax', tax_report, sequence=2, tag_name='purchase_t'),
            ],
        }

        # We create a sale and a purchase tax, linked to our report line tags
        taxes = self._create_taxes_for_report_lines(report_lines_dict, company)

        account_types = {
            'sale': 'income',
            'purchase': 'expense',
        }
        for tax in taxes:
            account = self.env['account.account'].search([('company_id', '=', company.id), ('account_type', '=', account_types[tax.type_tax_use])], limit=1)
            # create one entry and it's reverse
            move_form = Form(self.env['account.move'].with_context(default_move_type='entry'))
            with move_form.line_ids.new() as line:
                line.account_id = account
                if tax.type_tax_use == 'sale':
                    line.credit = 1000
                else:
                    line.debit = 1000
                line.tax_ids.clear()
                line.tax_ids.add(tax)

            # Create a third account.move.line for balance.
            with move_form.line_ids.new() as line:
                line.account_id = account
                if tax.type_tax_use == 'sale':
                    line.debit = 1200
                else:
                    line.credit = 1200
            move = move_form.save()
            move.action_post()
            refund_wizard = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=move.ids).create({
                'reason': 'reasons',
                'journal_id': self.company_data['default_journal_misc'].id,
            })
            refund_wizard.modify_moves()

            self.assertEqual(
                move.line_ids.tax_repartition_line_id,
                move.reversal_move_id.line_ids.tax_repartition_line_id,
                "The same repartition line should be used when reverting a misc operation, to ensure they sum up to 0 in all cases."
            )

        options = self._generate_options(tax_report, today, today)

        # We check the taxes on entries have impacted the report properly
        inv_report_lines = tax_report._get_lines(options)

        self.assertLinesValues(
            inv_report_lines,
            #   Name                         Balance
            [   0,                           1],
            [
                ('Sale base',              0.0),
                ('Sale tax',               0.0),
                ('Purchase base',          0.0),
                ('Purchase tax',           0.0),
            ],
            options,
        )

    @freeze_time('2023-10-05 02:00:00')
    def test_invoice_like_entry_reverse_caba_report(self):
        """ Cancelling the reconciliation of an invoice using cash basis taxes should reverse the cash basis move
        in such a way that the original cash basis move lines' impact falls down to 0.
        """
        self.env.company.tax_exigibility = True

        tax_report = self.env['account.report'].create({
            'name': 'CABA test',
            'country_id': self.fiscal_country.id,
            'root_report_id': self.env.ref("account.generic_tax_report").id,
            'column_ids': [Command.create({'name': 'balance', 'sequence': 1, 'expression_label': 'balance'})],
        })
        report_line_invoice_base = self._create_tax_report_line('Invoice base', tax_report, sequence=1, tag_name='caba_invoice_base')
        report_line_invoice_tax = self._create_tax_report_line('Invoice tax', tax_report, sequence=2, tag_name='caba_invoice_tax')
        report_line_refund_base = self._create_tax_report_line('Refund base', tax_report, sequence=3, tag_name='caba_refund_base')
        report_line_refund_tax = self._create_tax_report_line('Refund tax', tax_report, sequence=4, tag_name='caba_refund_tax')

        tax = self.env['account.tax'].create({
            'name': 'The Tax Who Says Ni',
            'type_tax_use': 'sale',
            'amount': 42,
            'tax_exigibility': 'on_payment',
            'invoice_repartition_line_ids': [
                Command.create({
                    'repartition_type': 'base',
                    'tag_ids': [Command.set(report_line_invoice_base.expression_ids._get_matching_tags("+").ids)],
                }),
                Command.create({
                    'repartition_type': 'tax',
                    'tag_ids': [Command.set(report_line_invoice_tax.expression_ids._get_matching_tags("+").ids)],
                }),
            ],
            'refund_repartition_line_ids': [
                Command.create({
                    'repartition_type': 'base',
                    'tag_ids': [Command.set(report_line_refund_base.expression_ids._get_matching_tags("+").ids)],
                }),
                Command.create({
                    'repartition_type': 'tax',
                    'tag_ids': [Command.set(report_line_refund_tax.expression_ids._get_matching_tags("+").ids)],
                }),
            ],
        })

        move_form = Form(self.env['account.move'] \
                    .with_company(self.company_data['company']) \
                    .with_context(default_move_type='entry'))
        move_form.date = fields.Date.today()
        with move_form.line_ids.new() as base_line_form:
            base_line_form.name = "Base line"
            base_line_form.account_id = self.company_data['default_account_revenue']
            base_line_form.credit = 100
            base_line_form.tax_ids.clear()
            base_line_form.tax_ids.add(tax)

        with move_form.line_ids.new() as receivable_line_form:
            receivable_line_form.name = "Receivable line"
            receivable_line_form.account_id = self.company_data['default_account_receivable']
            receivable_line_form.debit = 142
        move = move_form.save()
        move.action_post()
        # make payment
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'amount': 142,
            'date': move.date,
            'journal_id': self.company_data['default_journal_bank'].id,
        })
        payment.action_post()

        report_options = self._generate_options(tax_report, move.date, move.date)
        self.assertLinesValues(
            tax_report._get_lines(report_options),
            #   Name                                       Balance
            [   0,                                               1],
            [
                ('Invoice base',                               0.0),
                ('Invoice tax',                                0.0),
                ('Refund base',                                0.0),
                ('Refund tax',                                 0.0),
            ],
            report_options,
        )

        # Reconcile the move with a payment
        (payment.move_id + move).line_ids.filtered(lambda x: x.account_id == self.company_data['default_account_receivable']).reconcile()
        self.assertLinesValues(
            tax_report._get_lines(report_options),
            #   Name                                       Balance
            [   0,                                               1],
            [
                ('Invoice base',                               100),
                ('Invoice tax',                                 42),
                ('Refund base',                                0.0),
                ('Refund tax',                                 0.0),
            ],
            report_options,
        )

        # Unreconcile the moves
        move.line_ids.remove_move_reconcile()
        self.assertLinesValues(
            tax_report._get_lines(report_options),
            #   Name                                       Balance
            [   0,                                               1],
            [
                ('Invoice base',                               0.0),
                ('Invoice tax',                                0.0),
                ('Refund base',                                0.0),
                ('Refund tax',                                 0.0),
            ],
            report_options,
        )

    def test_tax_report_get_past_closing_entry(self):
        options = self._generate_options(self.basic_tax_report, '2021-01-01', '2021-12-31')

        with patch.object(type(self.env['account.move']), '_get_vat_report_attachments', autospec=True, side_effect=lambda *args, **kwargs: []):
            # Generate the tax closing entry and close the period without posting it, so that we can assert on the exception
            vat_closing_move = self.env['account.generic.tax.report.handler']._generate_tax_closing_entries(self.basic_tax_report, options)
            vat_closing_move.action_post()

        # Calling the action_periodic_vat_entries method should return the existing tax closing entry.
        vat_closing_action = self.env['account.generic.tax.report.handler'].action_periodic_vat_entries(options)
        self.assertEqual(vat_closing_move.id, vat_closing_action['res_id'])

    def setup_multi_vat_context(self):
        """Setup 2 tax reports, taxes and partner to represent a multiVat context in which both taxes affect both tax report"""

        def get_positive_tag(report_line):
            return report_line.expression_ids._get_matching_tags().filtered(lambda x: not x.tax_negate)

        self.env['account.fiscal.position'].create({
            'name': "FP With foreign VAT number",
            'country_id': self.foreign_country.id,
            'foreign_vat': '422211',
            'auto_apply': True,
        })

        local_tax_report, foreign_tax_report = self.env['account.report'].create([
            {
                'name': "The Local Tax Report",
                'country_id': self.company_data['company'].account_fiscal_country_id.id,
                'root_report_id': self.env.ref('account.generic_tax_report').id,
                'column_ids': [Command.create({'name': 'balance', 'sequence': 1, 'expression_label': 'balance'})],
            },
            {
                'name': "The Foreign Tax Report",
                'country_id': self.foreign_country.id,
                'root_report_id': self.env.ref('account.generic_tax_report').id,
                'column_ids': [Command.create({'name': 'balance', 'sequence': 1, 'expression_label': 'balance', })],
            },
        ])
        local_tax_report_base_line = self._create_tax_report_line("base_local", local_tax_report, sequence=1, code="base_local", tag_name="base_local")
        local_tax_report_tax_line = self._create_tax_report_line("tax_local", local_tax_report, sequence=2, code="tax_local", tag_name="tax_local")
        foreign_tax_report_base_line = self._create_tax_report_line("base_foreign", foreign_tax_report, sequence=1, code="base_foreign", tag_name="base_foreign")
        foreign_tax_report_tax_line = self._create_tax_report_line("tax_foreign", foreign_tax_report, sequence=2, code="tax_foreign", tag_name="tax_foreign")

        local_tax_affecting_foreign_tax_report = self.env['account.tax'].create({'name': "The local tax affecting the foreign report", 'amount': 20})
        foreign_tax_affecting_local_tax_report = self.env['account.tax'].create({
            'name': "The foreign tax affecting the local tax report",
            'amount': 20,
            'country_id': self.foreign_country.id,
        })
        for tax in (local_tax_affecting_foreign_tax_report, foreign_tax_affecting_local_tax_report):
            base_line, tax_line = tax.invoice_repartition_line_ids
            base_line.tag_ids = get_positive_tag(local_tax_report_base_line) + get_positive_tag(foreign_tax_report_base_line)
            tax_line.tag_ids = get_positive_tag(local_tax_report_tax_line) + get_positive_tag(foreign_tax_report_tax_line)

        local_partner = self.partner_a
        foreign_partner = self.partner_a.copy()
        foreign_partner.country_id = self.foreign_country

        return {
            'tax_report': (local_tax_report, foreign_tax_report,),
            'taxes': (local_tax_affecting_foreign_tax_report, foreign_tax_affecting_local_tax_report,),
            'partners': (local_partner, foreign_partner),
        }

    def test_local_tax_can_affect_foreign_tax_report(self):
        setup_data = self.setup_multi_vat_context()
        local_tax_report, foreign_tax_report = setup_data['tax_report']
        local_tax_affecting_foreign_tax_report, _ = setup_data['taxes']
        local_partner, _ = setup_data['partners']

        invoice = self.init_invoice('out_invoice', partner=local_partner, invoice_date='2022-12-01', post=True, amounts=[100], taxes=local_tax_affecting_foreign_tax_report)
        options = self._generate_options(local_tax_report, invoice.date, invoice.date)
        self.assertLinesValues(
            local_tax_report._get_lines(options),
            #   Name                                        Balance
            [   0,                                                1],
            [
                ("base_local",                                100.0),
                ("tax_local",                                  20.0),
            ],
            options,
        )

        options = self._generate_options(foreign_tax_report, invoice.date, invoice.date)
        self.assertLinesValues(
            foreign_tax_report._get_lines(options),
            #   Name                                          Balance
            [   0,                                                1],
            [
                ("base_foreign",                              100.0),
                ("tax_foreign",                                20.0),
            ],
            options,
        )

    def test_foreign_tax_can_affect_local_tax_report(self):
        setup_data = self.setup_multi_vat_context()
        local_tax_report, foreign_tax_report = setup_data['tax_report']
        _, foreign_tax_affecting_local_tax_report = setup_data['taxes']
        _, foreign_partner = setup_data['partners']

        invoice = self.init_invoice('out_invoice', partner=foreign_partner, invoice_date='2022-12-01', post=True, amounts=[100], taxes=foreign_tax_affecting_local_tax_report)
        options = self._generate_options(local_tax_report, invoice.date, invoice.date)
        self.assertLinesValues(
            local_tax_report._get_lines(options),
            #   Name                                        Balance
            [   0,                                                1],
            [
                ("base_local",                                100.0),
                ("tax_local",                                  20.0),
            ],
            options,
        )

        options = self._generate_options(foreign_tax_report, invoice.date, invoice.date)
        self.assertLinesValues(
            foreign_tax_report._get_lines(options),
            #   Name                                          Balance
            [   0,                                                1],
            [
                ("base_foreign",                              100.0),
                ("tax_foreign",                                20.0),
            ],
            options,
        )
    def test_engine_external_many_fiscal_positions(self):
        # Create a tax report that contains default manual expressions
        self.basic_tax_report_2 = self.env['account.report'].create({
            'name': "The Other Tax Report",
            'country_id': self.fiscal_country.id,
            'root_report_id': self.env.ref("account.generic_tax_report").id,
            'column_ids': [Command.create({'name': 'balance', 'sequence': 1, 'expression_label': 'balance'})],
            'line_ids': [
                Command.create({
                    'name': "test_line_1",
                    'code': "test_line_1",
                    'sequence': 1,
                    'expression_ids': [
                        Command.create({
                            'date_scope': 'strict_range',
                            'engine': 'external',
                            'formula': 'sum',
                            'label': 'balance',
                        }),
                        Command.create({
                            'date_scope': 'strict_range',
                            'engine': 'account_codes',
                            'formula': '101',
                            'label': '_default_balance',
                        })
                    ]
                }),
                Command.create({
                    'name': "test_line_2",
                    'code': "test_line_2",
                    'sequence': 2,
                    'expression_ids': [
                        Command.create({
                            'date_scope': 'strict_range',
                            'engine': 'account_codes',
                            'formula': '101',
                            'label': 'balance',
                        })
                    ],
                })
            ]
        })

        company_2 = self.company_data_2['company']
        company_2.country_id = self.fiscal_country
        company_2.currency_id = self.company_data['company'].currency_id

        # create two foreign fiscal positions (FPs), so we could create moves for each of them
        foreign_vat_fpos = self.env['account.fiscal.position'].create([
            {
                'name': 'fpos 1',
                'foreign_vat': 'A Swallow from Africa',
                'country_id': self.fiscal_country.id,
                'company_id': company_2.id,
                'state_ids': self.country_state_1,
            },
            {
                'name': 'fpos 2',
                'foreign_vat': 'A Swallow from Europe',
                'country_id': self.fiscal_country.id,
                'company_id': company_2.id,
                'state_ids': self.country_state_2,
            },
        ])

        test_account_1 = self.env['account.account'].create({
            'code': "101007",
            'name': "test account",
            'account_type': "asset_current",
            'company_id': company_2.id,
        })

        test_account_2 = self.env['account.account'].create({
            'code': "test",
            'name': "test",
            'account_type': "asset_current",
            'company_id': company_2.id,
        })

        move_vals = [{
            'date': fields.Date.from_string('2020-01-01'),
            'fiscal_position_id': fp.id,
            'company_id': company_2.id,
            'line_ids': [
                Command.create({
                    'name': 'line 1',
                    'account_id': test_account_1.id,
                    'debit': 1000 * (i + 1),
                    'credit': 0.0,
                }),
                Command.create({
                    'name': 'line 2',
                    'account_id': test_account_2.id,
                    'debit': 0.0,
                    'credit': 1000 * (i + 1),
                }),
            ]
        } for i, fp in enumerate(foreign_vat_fpos)]

        # create a move that includes an account starting with '101'
        # to make sure its amount does not appear in the tax report for company_2
        other_company_move_vals = {
            'date': fields.Date.from_string('2020-01-01'),
            'company_id': self.company_data['company'].id,
            'line_ids': [
                Command.create({
                    'name': 'line 1',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'debit': 1200,
                    'credit': 0.0,
                }),
                Command.create({
                    'name': 'line 2',
                    'account_id': self.company_data['default_account_assets'].id,
                    'debit': 0.0,
                    'credit': 1200,
                }),
            ]
        }

        moves = self.env['account.move'].create(move_vals)
        moves.action_post()
        other_company_move = self.env['account.move'].create(other_company_move_vals)
        other_company_move.action_post()

        # we need to create different options per FP
        fiscal_positions = ['all'] + foreign_vat_fpos.ids
        report_options = {}
        for fp in fiscal_positions:
            fp_options = self._generate_options(
                self.basic_tax_report_2.with_context(allowed_company_ids=[company_2.id]),
                '2020-01-01', '2020-01-04',
                default_options={
                    'fiscal_position': fp,
                }
            )
            report_options[fp] = fp_options

        # when we filter by all FPs, the result on the second line
        # should be the sum of the moves
        # the first line contains a default expression and remains empty
        # until we set a lock date
        total_amount = sum([1000 * (i + 1) for i in range(len(foreign_vat_fpos.ids))])
        report_lines = self.basic_tax_report_2\
            .with_company(company_2)._get_lines(report_options['all'])
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report_lines,
            [0,                             1],
            [
                ('test_line_1',           0.0),
                ('test_line_2',  total_amount),
            ],
            report_options['all'],
        )

        # subsequently, line 2 should only contain the amount for the selected FP
        for i, fp in enumerate(foreign_vat_fpos.ids):
            report_lines = self.basic_tax_report_2\
                .with_company(company_2)._get_lines(report_options[fp])
            self.assertLinesValues(
                # pylint: disable=bad-whitespace
                report_lines,
                [0,                               1],
                [
                    ('test_line_1',            0.0),
                    ('test_line_2', 1000 * (i + 1)),
                ],
                report_options[fp],
            )

        # the default values shouldn't be created if the general lock date is set
        lock_date_wizard = self.env['account.change.lock.date']\
            .with_company(company_2).create({
            'fiscalyear_lock_date': fields.Date.from_string('2020-01-04'),
        })
        lock_date_wizard.change_lock_date()

        report_lines = self.basic_tax_report_2\
            .with_company(company_2)._get_lines(report_options['all'])
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report_lines,
            [0,                             1],
            [
                ('test_line_1',           0.0),
                ('test_line_2',  total_amount),
            ],
            report_options['all'],
        )

        # if we change the tax_lock_date, the default values should be created
        lock_date_wizard = self.env['account.change.lock.date']\
            .with_company(company_2).create({
            'tax_lock_date': fields.Date.from_string('2020-01-04'),
        })
        lock_date_wizard.change_lock_date()

        report_lines = self.basic_tax_report_2\
            .with_company(company_2)._get_lines(report_options['all'])
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report_lines,
            [0,                             1],
            [
                ('test_line_1',  total_amount),
                ('test_line_2',  total_amount),
            ],
            report_options['all'],
        )

        for i, fp in enumerate(foreign_vat_fpos.ids):
            report_lines = self.basic_tax_report_2\
                .with_company(company_2)._get_lines(report_options[fp])
            self.assertLinesValues(
                # pylint: disable=bad-whitespace
                report_lines,
                [0,                               1],
                [
                    ('test_line_1', 1000 * (i + 1)),
                    ('test_line_2', 1000 * (i + 1)),
                ],
                report_options[fp],
            )

    def test_tax_report_w_rounding_line(self):
        """Check that the tax report is correct when a rounding line is added to an invoice."""
        self.env['res.config.settings'].create({
            'company_id': self.company_data['company'].id,
            'group_cash_rounding': True
        })

        rounding = self.env['account.cash.rounding'].create({
            'name': 'Test rounding',
            'rounding': 0.05,
            'strategy': 'biggest_tax',
            'rounding_method': 'HALF-UP',
            'company_id': self.company_data['company'].id,
        })

        tax = self.sale_tax_percentage_incl_1.copy({
            'name': 'The Tax Who Says Ni',
            'amount': 21,
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'The Holy Grail',
                    'quantity': 1,
                    'price_unit': 1.26,
                    'tax_ids': [Command.set(self.sale_tax_percentage_incl_1.ids)],
                }),
                Command.create({
                    'name': 'What is your favourite colour?',
                    'quantity': 1,
                    'price_unit': 2.32,
                    'tax_ids': [Command.set(tax.ids)],
                })
            ],
            'invoice_cash_rounding_id': rounding.id,
        })

        invoice.action_post()

        self.assertRecordValues(invoice.line_ids, [
            {
                'name': 'The Holy Grail',
                'debit': 0.00,
                'credit': 1.05,
            },
            {
                'name': 'What is your favourite colour?',
                'debit': 0.00,
                'credit': 1.92,
            },
            {
                'name': self.sale_tax_percentage_incl_1.name,
                'debit': 0.00,
                'credit': 0.21,
            },
            {
                'name': tax.name,
                'debit': 0.00,
                'credit': 0.40,
            },
            {
                'name': f'{tax.name} (rounding)',
                'debit': 0.00,
                'credit': 0.02,
            },
            {
                'name': invoice.name,
                'debit': 3.60,
                'credit': 0.00,
            }
        ])

        report = self.env.ref('account.generic_tax_report')
        options = self._generate_options(report, invoice.date, invoice.date)

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                                                                         Base      Tax
            [   0,                                                                                           1,        2],
            [
                ('Sales',                                                                                   "",     0.63),
                (f'{self.sale_tax_percentage_incl_1.name} ({self.sale_tax_percentage_incl_1.amount}%)',   1.05,     0.21),
                (f'{tax.name} ({tax.amount}%)',                                                           1.92,     0.42),
                ('Total Sales',                                                                            "",      0.63),
            ],
            options
        )

        report = self.env.ref("account.generic_tax_report_account_tax")
        options['report_id'] = report.id

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                                                                         Base      Tax
            [   0,                                                                                           1,        2],
            [
                ('Sales',                                                                                   "",     0.63),
                (self.company_data['default_account_revenue'].display_name,                                 "",     0.63),
                (f'{self.sale_tax_percentage_incl_1.name} ({self.sale_tax_percentage_incl_1.amount}%)',   1.05,     0.21),
                (f'{tax.name} ({tax.amount}%)',                                                           1.92,     0.42),
                (f'Total {self.company_data["default_account_revenue"].display_name}',                      "",     0.63),
                ('Total Sales',                                                                             "",     0.63),
            ],
            options
        )

        report = self.env.ref("account.generic_tax_report_tax_account")
        options['report_id'] = report.id

        self.assertLinesValues(
            report._get_lines(options),
            #   Name                                                                                               Base      Tax
            [   0,                                                                                                 1,        2],
            [
                ('Sales',                                                                                         "",     0.63),
                (f'{self.sale_tax_percentage_incl_1.name} ({self.sale_tax_percentage_incl_1.amount}%)',           "",     0.21),
                (self.company_data['default_account_revenue'].display_name,                                     1.05,     0.21),
                (f'Total {self.sale_tax_percentage_incl_1.name} ({self.sale_tax_percentage_incl_1.amount}%)',     "",     0.21),
                (f'{tax.name} ({tax.amount}%)',                                                                   "",     0.42),
                (self.company_data['default_account_revenue'].display_name,                                     1.92,     0.42),
                (f'Total {tax.name} ({tax.amount}%)',                                                             "",     0.42),
                ('Total Sales',                                                                                   "",     0.63),
            ],
            options
        )

    def test_tax_report_closing_entry_reset_to_draft(self):
        """
        Test the reset to draft functionality to ensure no duplicate closing entry is created.

        This test checks that when a tax report closing entry is posted and then reset to draft,
        creating a subsequent closing entry will not result in a duplicate. Instead, the same
        initial closing entry will be reused.
        """
        options = self._generate_options(self.basic_tax_report, '2021-03-01', '2021-03-31')
        vat_closing_action = self.env['account.generic.tax.report.handler'].action_periodic_vat_entries(options)
        initial_closing_entry = self.env['account.move'].browse(vat_closing_action['res_id'])
        initial_closing_entry.action_post()
        initial_closing_entry.button_draft()
        vat_closing_action = self.env['account.generic.tax.report.handler'].action_periodic_vat_entries(options)
        subsequent_closing_entry  = self.env['account.move'].browse(vat_closing_action['res_id'])
        self.assertEqual(initial_closing_entry, subsequent_closing_entry)

    def test_tax_report_closing_entry_draft_with_new_entries(self):
        """
        Test whether the tax closing entry gets properly computed when reset to draft and the VAT closing button is clicked again.
        """
        options = self._generate_options(self.basic_tax_report, '2023-01-01', '2023-03-31')
        self.init_invoice('out_invoice', partner=self.partner_a, invoice_date='2023-03-22', post=True, amounts=[200], taxes=self.tax_sale_a)
        initial_vat_closing_action = self.env['account.generic.tax.report.handler'].action_periodic_vat_entries(options)
        initial_closing_entry = self.env['account.move'].browse(initial_vat_closing_action['res_id'])
        initial_values = []
        for aml in initial_closing_entry.line_ids:
            self.assertEqual(aml.balance, 30 if aml.balance > 0 else -30)
            initial_values.append({'account_id': aml.account_id.id, 'balance': aml.balance})
        self.init_invoice('out_invoice', partner=self.partner_a, invoice_date='2023-03-22', post=True, amounts=[1000], taxes=self.tax_sale_a)
        subsequent_vat_closing_action = self.env['account.generic.tax.report.handler'].action_periodic_vat_entries(options)
        subsequent_closing_entry  = self.env['account.move'].browse(subsequent_vat_closing_action['res_id'])
        self.assertRecordValues(subsequent_closing_entry.line_ids, [
            {'account_id': initial_values[0]['account_id'], 'balance': initial_values[0]['balance'] + 150},
            {'account_id': initial_values[1]['account_id'], 'balance': initial_values[1]['balance'] - 150},
        ])

    def test_tax_report_multi_company_post_closing(self):
        # Branches
        root_company = self.setup_company_data("Root Company", chart_template=self.env.company.chart_template)['company']
        branch_1 = self.env['res.company'].create({'name': "Branch 1", 'parent_id': root_company.id})
        branch_1_1 = self.env['res.company'].create({'name': "Branch 1.1", 'parent_id': branch_1.id})
        branch_2 = self.env['res.company'].create({'name': "Branch 2", 'parent_id': root_company.id})
        branch_companies = root_company + branch_1 + branch_1_1 + branch_2
        branch_companies.account_tax_periodicity_journal_id = root_company.account_tax_periodicity_journal_id.id

        # Tax unit
        unit_part_1 = self.setup_company_data("Unit part 1", chart_template=self.env.company.chart_template)['company']
        unit_part_2 = self.setup_company_data("Unit part 2", chart_template=self.env.company.chart_template)['company']

        tax_unit = self.env['account.tax.unit'].create({
            'name': "One unit to rule them all",
            'country_id': unit_part_1.account_fiscal_country_id.id,
            'vat': "123",
            'company_ids': (unit_part_1 + unit_part_2).ids,
            'main_company_id': unit_part_1.id,
        })

        tax_report = self.env['account.report'].create({
            'name': "My Onw Particular Tax Report",
            'country_id': unit_part_1.account_fiscal_country_id.id,
            'root_report_id': self.env.ref("account.generic_tax_report").id,
            'column_ids': [Command.create({'name': 'balance', 'sequence': 1, 'expression_label': 'balance',})],
        })

        for test_type, main_company, active_companies in [('branches', root_company, branch_companies), ('tax units', tax_unit.main_company_id, tax_unit.company_ids)]:
            with self.subTest(f"Post multicompany closing - {test_type}"):
                tax_report_with_companies = tax_report.with_context(allowed_company_ids=active_companies.ids)
                options = self._generate_options(tax_report_with_companies, '2023-01-01', '2023-01-01')
                closing_moves = self.env['account.generic.tax.report.handler'].with_context(allowed_company_ids=active_companies.ids)._generate_tax_closing_entries(tax_report_with_companies, options)

                self.assertEqual(len(closing_moves), len(active_companies), "One closing move should have been created per company")
                self.assertTrue(all(move.state == 'draft' for move in closing_moves), "All generated closing moves should be in draft")
                main_closing_move = closing_moves.filtered(lambda x: x.company_id == main_company)
                self.assertEqual(len(main_closing_move), 1)

                # The warning message telling multiple closing will be posted at once by posting the current one should only appear on the
                # main company's closing move.
                self.assertTrue(main_closing_move.tax_closing_show_multi_closing_warning)
                self.assertFalse(any(closing.tax_closing_show_multi_closing_warning for closing in (closing_moves - main_closing_move)))

                main_closing_move.action_post()
                self.assertTrue(all(move.state == 'posted' for move in closing_moves), "Posting the main closing should have posted all the depending closings")
                self.assertFalse(main_closing_move.tax_closing_show_multi_closing_warning)

    def test_tax_report_prevent_draft_if_subsequent_posted(self):
        """
        Test the reset to draft functionality to ensure it is not possible to reset to draft a closing entry
        if subsequent closing entries are already posted.
        """
        options = self._generate_options(self.basic_tax_report, '2023-01-01', '2023-03-31')
        vat_closing_action = self.env['account.generic.tax.report.handler'].action_periodic_vat_entries(options)
        Q1_closing_entry = self.env['account.move'].browse(vat_closing_action['res_id'])
        Q1_closing_entry.action_post()

        options = self._generate_options(self.basic_tax_report, '2023-04-01', '2023-06-30')
        vat_closing_action = self.env['account.generic.tax.report.handler'].action_periodic_vat_entries(options)
        Q2_closing_entry = self.env['account.move'].browse(vat_closing_action['res_id'])
        Q2_closing_entry.action_post()

        with self.assertRaises(UserError):
            Q1_closing_entry.button_draft()
