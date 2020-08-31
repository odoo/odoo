# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from odoo.tests import common
from odoo.tests.common import Form, SavepointCase
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.misc import formatLang
import datetime
import copy

import logging
_logger = logging.getLogger(__name__)


def _init_options(report, date_from, date_to):
    ''' Create new options at a certain date.
    :param report:          The report.
    :param filter:          One of the following values: ('today', 'custom', 'this_month', 'this_quarter', 'this_year', 'last_month', 'last_quarter', 'last_year').
    :param date_from:       A datetime object or False.
    :param date_to:         A datetime object.
    :return:                The newly created options.
    '''
    report.filter_date = {
        'date_from': date_from.strftime(DEFAULT_SERVER_DATE_FORMAT),
        'date_to': date_to.strftime(DEFAULT_SERVER_DATE_FORMAT),
        'filter': 'custom',
        'mode': report.filter_date.get('mode', 'range'),
    }
    return report._get_options(None)


class TestAccountReportsCommon(SavepointCase):

    # -------------------------------------------------------------------------
    # DATA GENERATION
    # -------------------------------------------------------------------------

    @classmethod
    def setUpClass(cls):
        super(TestAccountReportsCommon, cls).setUpClass()

        chart_template = cls.env.ref('l10n_generic_coa.configurable_chart_template', raise_if_not_found=False)
        if not chart_template:
            _logger.warn('Reports Tests skipped because l10n_generic_coa is not installed')
            cls.skipTest(cls, reason="l10n_generic_coa not installed")

        # Create companies.
        cls.company_parent = cls.env['res.company'].create({
            'name': 'company_parent',
            'currency_id': cls.env.ref('base.USD').id,
        })
        cls.company_child_eur = cls.env['res.company'].create({
            'name': 'company_child_eur',
            'currency_id': cls.env.ref('base.EUR').id,
        })

        # EUR = 2 USD
        cls.eur_to_usd = cls.env['res.currency.rate'].create({
            'name': '2016-01-01',
            'rate': 2.0,
            'currency_id': cls.env.ref('base.EUR').id,
            'company_id': cls.company_parent.id,
        })

        # Create user.
        user = cls.env['res.users'].create({
            'name': 'Because I am reportman!',
            'login': 'reportman',
            'groups_id': [(6, 0, cls.env.user.groups_id.ids)],
            'company_id': cls.company_parent.id,
            'company_ids': [(6, 0, (cls.company_parent + cls.company_child_eur).ids)],
        })
        user.partner_id.email = 'reportman@test.com'

        # Shadow the current environment/cursor with one having the report user.
        cls.env = cls.env(user=user)
        cls.cr = cls.env.cr

        # Get the new chart of accounts using the new environment.
        chart_template = cls.env.ref('l10n_generic_coa.configurable_chart_template')

        cls.partner_category_a = cls.env['res.partner.category'].create({'name': 'partner_categ_a'})
        cls.partner_category_b = cls.env['res.partner.category'].create({'name': 'partner_categ_b'})

        cls.partner_a = cls.env['res.partner'].create(
            {'name': 'partner_a', 'company_id': False, 'category_id': [(6, 0, [])]})
        cls.partner_b = cls.env['res.partner'].create(
            {'name': 'partner_b', 'company_id': False, 'category_id': [(6, 0, [cls.partner_category_a.id])]})
        cls.partner_c = cls.env['res.partner'].create(
            {'name': 'partner_c', 'company_id': False, 'category_id': [(6, 0, [cls.partner_category_b.id])]})
        cls.partner_d = cls.env['res.partner'].create(
            {'name': 'partner_d', 'company_id': False, 'category_id': [(6, 0, [cls.partner_category_a.id, cls.partner_category_b.id])]})

        # Init data for company_parent.
        chart_template.with_context(allowed_company_ids=cls.company_parent.ids).try_loading()

        cls.dec_year_minus_2 = datetime.datetime.strptime('2016-12-01', DEFAULT_SERVER_DATE_FORMAT).date()
        cls.jan_year_minus_1 = datetime.datetime.strptime('2017-01-01', DEFAULT_SERVER_DATE_FORMAT).date()
        cls.feb_year_minus_1 = datetime.datetime.strptime('2017-02-01', DEFAULT_SERVER_DATE_FORMAT).date()
        cls.mar_year_minus_1 = datetime.datetime.strptime('2017-03-01', DEFAULT_SERVER_DATE_FORMAT).date()
        cls.apr_year_minus_1 = datetime.datetime.strptime('2017-04-01', DEFAULT_SERVER_DATE_FORMAT).date()

        # December
        inv_dec_1 = cls._create_invoice(cls.env, 1200.0, cls.partner_a, 'out_invoice', cls.dec_year_minus_2)
        cls._create_payment(cls.env, cls.jan_year_minus_1, inv_dec_1, 600.0)
        inv_dec_2 = cls._create_invoice(cls.env, 1200.0, cls.partner_b, 'in_invoice', cls.dec_year_minus_2)
        pay_inv_dec_2 = cls._create_payment(cls.env, cls.dec_year_minus_2, inv_dec_2, 1200.0)
        cls._create_bank_statement(cls.env, pay_inv_dec_2)
        inv_dec_3 = cls._create_invoice(cls.env, 1200.0, cls.partner_c, 'in_invoice', cls.dec_year_minus_2)
        inv_dec_4 = cls._create_invoice(cls.env, 1200.0, cls.partner_d, 'in_invoice', cls.dec_year_minus_2)

        # January
        inv_jan_1 = cls._create_invoice(cls.env, 100.0, cls.partner_a, 'out_invoice', cls.jan_year_minus_1)
        inv_jan_2 = cls._create_invoice(cls.env, 100.0, cls.partner_b, 'out_invoice', cls.jan_year_minus_1)
        pay_inv_jan_2 = cls._create_payment(cls.env, cls.jan_year_minus_1, inv_jan_2, 100.0)
        cls._create_bank_statement(cls.env, pay_inv_jan_2)
        inv_jan_3 = cls._create_invoice(cls.env, 100.0, cls.partner_c, 'in_invoice', cls.jan_year_minus_1)
        pay_inv_jan_3 = cls._create_payment(cls.env, cls.feb_year_minus_1, inv_jan_3, 50.0)
        cls._create_bank_statement(cls.env, pay_inv_jan_3)
        inv_jan_4 = cls._create_invoice(cls.env, 100.0, cls.partner_d, 'out_invoice', cls.jan_year_minus_1)

        # February
        inv_feb_1 = cls._create_invoice(cls.env, 200.0, cls.partner_a, 'in_invoice', cls.feb_year_minus_1)
        inv_feb_2 = cls._create_invoice(cls.env, 200.0, cls.partner_b, 'out_invoice', cls.feb_year_minus_1)
        inv_feb_3 = cls._create_invoice(cls.env, 200.0, cls.partner_c, 'out_invoice', cls.feb_year_minus_1)
        pay_inv_feb_3 = cls._create_payment(cls.env, cls.mar_year_minus_1, inv_feb_3, 100.0)
        cls._create_bank_statement(cls.env, pay_inv_feb_3, reconcile=False)
        inv_feb_4 = cls._create_invoice(cls.env, 200.0, cls.partner_d, 'in_invoice', cls.feb_year_minus_1)
        cls._create_payment(cls.env, cls.feb_year_minus_1, inv_feb_4, 200.0)

        # March
        inv_mar_1 = cls._create_invoice(cls.env, 300.0, cls.partner_a, 'in_invoice', cls.mar_year_minus_1)
        cls._create_payment(cls.env, cls.mar_year_minus_1, inv_mar_1, 300.0)
        inv_mar_2 = cls._create_invoice(cls.env, 300.0, cls.partner_b, 'in_invoice', cls.mar_year_minus_1)
        inv_mar_3 = cls._create_invoice(cls.env, 300.0, cls.partner_c, 'out_invoice', cls.mar_year_minus_1)
        cls._create_payment(cls.env, cls.apr_year_minus_1, inv_mar_3, 150.0)
        inv_mar_4 = cls._create_invoice(cls.env, 300.0, cls.partner_d, 'out_invoice', cls.mar_year_minus_1)

        # Init data for company_child_eur.
        # Data are the same as the company_parent with doubled amount.
        # However, due to the foreign currency (2 EUR = 1 USD), the amounts are divided by two during the foreign
        # currency conversion.
        user.company_id = cls.company_child_eur
        chart_template.with_context(allowed_company_ids=cls.company_child_eur.ids).try_loading()

        # Currency has been reset to USD during the installation of the chart template.
        cls.company_child_eur.currency_id = cls.env.ref('base.EUR')

        # December
        inv_dec_5 = cls._create_invoice(cls.env, 2400.0, cls.partner_a, 'out_invoice', cls.dec_year_minus_2)
        cls._create_payment(cls.env, cls.jan_year_minus_1, inv_dec_5, 1200.0)
        inv_dec_6 = cls._create_invoice(cls.env, 2400.0, cls.partner_b, 'in_invoice', cls.dec_year_minus_2)
        pay_inv_dec_6 = cls._create_payment(cls.env, cls.dec_year_minus_2, inv_dec_6, 2400.0)
        cls._create_bank_statement(cls.env, pay_inv_dec_6)
        inv_dec_7 = cls._create_invoice(cls.env, 2400.0, cls.partner_c, 'in_invoice', cls.dec_year_minus_2)
        inv_dec_8 = cls._create_invoice(cls.env, 2400.0, cls.partner_d, 'in_invoice', cls.dec_year_minus_2)

        # January
        inv_jan_5 = cls._create_invoice(cls.env, 200.0, cls.partner_a, 'out_invoice', cls.jan_year_minus_1)
        inv_jan_6 = cls._create_invoice(cls.env, 200.0, cls.partner_b, 'out_invoice', cls.jan_year_minus_1)
        pay_inv_jan_6 = cls._create_payment(cls.env, cls.jan_year_minus_1, inv_jan_6, 200.0)
        cls._create_bank_statement(cls.env, pay_inv_jan_6)
        inv_jan_7 = cls._create_invoice(cls.env, 200.0, cls.partner_c, 'in_invoice', cls.jan_year_minus_1)
        pay_inv_jan_7 = cls._create_payment(cls.env, cls.feb_year_minus_1, inv_jan_7, 100.0)
        cls._create_bank_statement(cls.env, pay_inv_jan_7)
        inv_jan_8 = cls._create_invoice(cls.env, 200.0, cls.partner_d, 'out_invoice', cls.jan_year_minus_1)

        # February
        inv_feb_5 = cls._create_invoice(cls.env, 400.0, cls.partner_a, 'in_invoice', cls.feb_year_minus_1)
        inv_feb_6 = cls._create_invoice(cls.env, 400.0, cls.partner_b, 'out_invoice', cls.feb_year_minus_1)
        inv_feb_7 = cls._create_invoice(cls.env, 400.0, cls.partner_c, 'out_invoice', cls.feb_year_minus_1)
        pay_inv_feb_7 = cls._create_payment(cls.env, cls.mar_year_minus_1, inv_feb_7, 200.0)
        cls._create_bank_statement(cls.env, pay_inv_feb_7, reconcile=False)
        inv_feb_8 = cls._create_invoice(cls.env, 400.0, cls.partner_d, 'in_invoice', cls.feb_year_minus_1)
        cls._create_payment(cls.env, cls.feb_year_minus_1, inv_feb_8, 400.0)

        # Mars
        inv_mar_5 = cls._create_invoice(cls.env, 600.0, cls.partner_a, 'in_invoice', cls.mar_year_minus_1)
        cls._create_payment(cls.env, cls.mar_year_minus_1, inv_mar_5, 600.0)
        inv_mar_6 = cls._create_invoice(cls.env, 600.0, cls.partner_b, 'in_invoice', cls.mar_year_minus_1)
        inv_mar_7 = cls._create_invoice(cls.env, 600.0, cls.partner_c, 'out_invoice', cls.mar_year_minus_1)
        cls._create_payment(cls.env, cls.apr_year_minus_1, inv_mar_7, 300.0)
        inv_mar_8 = cls._create_invoice(cls.env, 600.0, cls.partner_d, 'out_invoice', cls.mar_year_minus_1)

        user.company_id = cls.company_parent

        # Write the property on tag group
        cls.tax_rec_account = cls.env['account.account'].create({
            'name': 'TAX receivable account',
            'code': 'TAX REC',
            'user_type_id': cls.env.ref('account.data_account_type_current_assets').id,
            'company_id': cls.company_parent.id,
        })
        cls.tax_pay_account = cls.env['account.account'].create({
            'name': 'TAX payable account',
            'code': 'TAX PAY',
            'user_type_id': cls.env.ref('account.data_account_type_current_assets').id,
            'company_id': cls.company_parent.id,
        })
        cls.tax_adv_account = cls.env['account.account'].create({
            'name': 'TAX advance account',
            'code': 'TAX ADV',
            'user_type_id': cls.env.ref('account.data_account_type_current_assets').id,
            'company_id': cls.company_parent.id,
        })
        # Set the tax rec/pay on tax_group
        tax_groups = cls.env['account.tax.group'].search([])
        tax_groups.write({
            'property_tax_receivable_account_id': cls.tax_rec_account,
            'property_tax_payable_account_id': cls.tax_pay_account
        })

        # Date filter helper
        cls.january_date = datetime.datetime.strptime('2018-01-01', DEFAULT_SERVER_DATE_FORMAT).date()
        cls.january_end_date = datetime.datetime.strptime('2018-01-31', DEFAULT_SERVER_DATE_FORMAT).date()
        cls.february_date = datetime.datetime.strptime('2018-02-01', DEFAULT_SERVER_DATE_FORMAT).date()
        cls.february_end_date = datetime.datetime.strptime('2018-02-28', DEFAULT_SERVER_DATE_FORMAT).date()

        # Create ir.filters to test the financial reports.
        cls.groupby_partner_filter = cls.env['ir.filters'].create({
            'name': 'report tests groupby filter',
            'model_id': 'account.move.line',
            'domain': '[]',
            'context': str({'group_by': ['partner_id']}),
        })

    @staticmethod
    def _create_invoice(env, amount, partner, invoice_type, date, clear_taxes=False):
        ''' Helper to create an account.move on the fly with only one line.
        N.B: The taxes are also applied.
        :param amount:          The amount of the unique account.move.line.
        :param partner:         The partner.
        :param invoice_type:    The invoice type.
        :param date:            The invoice date as a datetime object.
        :return:                An account.move record.
        '''
        invoice_form = Form(env['account.move'].with_context(default_type=invoice_type))
        invoice_form.partner_id = partner
        invoice_form.date = date
        invoice_form.invoice_date = date
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.name = 'test'
            invoice_line_form.price_unit = amount
            if clear_taxes:
                invoice_line_form.tax_ids.clear()
        invoice = invoice_form.save()
        invoice.post()
        return invoice

    @staticmethod
    def _create_payment(env, date, invoices, amount=None, journal=None):
        ''' Helper to create an account.payment on the fly for some invoices.
        :param date:        The payment date.
        :param invoices:    The invoices on which the payment is done.
        :param amount:      The payment amount.
        :return:            An account.payment record.
        '''
        self_ctx = env['account.payment'].with_context(active_model='account.move', active_ids=invoices.ids)
        payment_form = Form(self_ctx)
        payment_form.payment_date = date
        if journal:
            payment_form.journal_id = journal
        if amount:
            payment_form.amount = amount
        register_payment = payment_form.save()
        register_payment.post()
        return register_payment

    @staticmethod
    def _create_bank_statement(env, payment, amount=None, reconcile=True):
        ''' Helper to create an account.bank.statement on the fly for a payment.
        :param payment:     An account.payment record.
        :param amount:      An optional custom amount.
        :param reconcile:   Reconcile the newly created statement line with the payment.
        :return:            An account.bank.statement record.
        '''
        bank_journal = payment.journal_id
        amount = amount or (payment.payment_type == 'inbound' and payment.amount or -payment.amount)
        statement_form = Form(env['account.bank.statement'])
        statement_form.journal_id = bank_journal
        statement_form.date = payment.payment_date
        statement_form.name = payment.name
        with statement_form.line_ids.new() as statement_line_form:
            statement_line_form.date = payment.payment_date
            statement_line_form.name = payment.name
            statement_line_form.partner_id = payment.partner_id
            statement_line_form.amount = amount
        statement_form.balance_end_real = statement_form.balance_end
        statement = statement_form.save()
        if reconcile:
            move_line = payment.move_line_ids.filtered(
                lambda aml: aml.account_id in bank_journal.default_debit_account_id + bank_journal.default_credit_account_id)
            statement.line_ids[0].process_reconciliation(payment_aml_rec=move_line)
        return statement

    # -------------------------------------------------------------------------
    # TESTS METHODS
    # -------------------------------------------------------------------------

    @staticmethod
    def _init_options(report, date_from, date_to):
        ''' Create new options at a certain date.
        :param report:          The report.
        :param filter:          One of the following values: ('today', 'custom', 'this_month', 'this_quarter', 'this_year', 'last_month', 'last_quarter', 'last_year').
        :param date_from:       A datetime object or False.
        :param date_to:         A datetime object.
        :return:                The newly created options.
        '''
        return _init_options(report, date_from, date_to)

    def _update_comparison_filter(self, options, report, comparison_type, number_period, date_from=None, date_to=None):
        ''' Modify the existing options to set a new filter_comparison.
        :param options:         The report options.
        :param report:          The report.
        :param comparison_type: One of the following values: ('no_comparison', 'custom', 'previous_period', 'previous_year').
        :param number_period:   The number of period to compare.
        :param date_from:       A datetime object for the 'custom' comparison_type.
        :param date_to:         A datetime object the 'custom' comparison_type.
        :return:                The newly created options.
        '''
        report.filter_comparison = {
            'date_from': date_from and date_from.strftime(DEFAULT_SERVER_DATE_FORMAT),
            'date_to': date_to and date_to.strftime(DEFAULT_SERVER_DATE_FORMAT),
            'filter': comparison_type,
            'number_period': number_period,
        }
        new_options = copy.deepcopy(options)
        report._init_filter_comparison(new_options)
        return new_options

    def _update_multi_selector_filter(self, options, option_key, selected_ids):
        ''' Modify a selector in the options to select .
        :param options:         The report options.
        :param option_key:      The key to the option.
        :param selected_ids:    The ids to be selected.
        :return:                The newly created options.
        '''
        new_options = copy.deepcopy(options)
        for c in new_options[option_key]:
            c['selected'] = c['id'] in selected_ids
        return new_options

    def assertLinesValues(self, lines, columns, expected_values, currency=None):
        ''' Helper to compare the lines returned by the _get_lines method
        with some expected results.
        :param lines:               See _get_lines.
        :params columns:            The columns index.
        :param expected_values:     A list of iterables.
        '''
        used_currency = currency or self.env.company.currency_id

        # Compare the table length to see if any line is missing
        self.assertEquals(len(lines), len(expected_values))

        # Compare cell by cell the current value with the expected one.
        i = 0
        for line in lines:
            j = 0
            compared_values = [[], []]
            for index in columns:
                expected_value = expected_values[i][j]

                if index == 0:
                    current_value = line['name']
                else:
                    colspan = line.get('colspan', 1)
                    line_index = index - colspan
                    if line_index < 0:
                        current_value = ''
                    else:
                        current_value = line['columns'][line_index].get('name', '')

                if type(expected_value) in (int, float) and type(current_value) == str:
                    expected_value = formatLang(self.env, expected_value, currency_obj=used_currency)

                compared_values[0].append(current_value)
                compared_values[1].append(expected_value)

                j += 1
            self.assertEqual(compared_values[0], compared_values[1])
            i += 1
