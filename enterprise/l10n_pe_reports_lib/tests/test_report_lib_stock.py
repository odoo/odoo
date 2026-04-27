from odoo import fields
from odoo.addons.stock_account.tests.test_stockvaluationlayer import TestStockValuationCommon
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import SQL

from collections import OrderedDict
from datetime import datetime
from freezegun import freeze_time


@tagged("post_install", "post_install_l10n", "-at_install", "l10n_pe_lib")
class TestPeReportsLibTransaction(TestStockValuationCommon, AccountTestInvoicingCommon):

    @classmethod
    def get_default_groups(cls):
        groups = super().get_default_groups()
        return groups | cls.env.ref('stock.group_stock_manager')

    @classmethod
    @AccountTestInvoicingCommon.setup_country('pe')
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company['country_id'] = cls.env.ref("base.pe")
        cls.env.company['vat'] = "20512528458"
        cls.env.company['l10n_pe_financial_statement_type'] = '01'
        cls.env.company.partner_id.l10n_latam_identification_type_id = cls.env.ref("l10n_pe.it_RUC")
        cls.product_a = cls.env['product.product'].create({
            'name': 'Product A',
            'default_code': 'A_A&A',
            'l10n_pe_type_of_existence': '1',
            'unspsc_code_id': cls.env['product.unspsc.code'].search([], limit=1).id,
            'uom_id': cls.env.ref('uom.product_uom_unit').id
        })
        cls.product_a.product_tmpl_id.categ_id.property_cost_method = 'average'

        cls.picking_type_in = cls.env['stock.picking.type'].search([('code', '=', 'incoming'), ('company_id', '=', cls.env.company.id)], limit=1)
        cls.picking_type_out = cls.env['stock.picking.type'].search([('code', '=', 'outgoing'), ('company_id', '=', cls.env.company.id)], limit=1)
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.company_data['company'].id)], limit=1)
        cls.stock_location = cls.warehouse.lot_stock_id

        # Generate report options and query elements passed to report element functions, same as what the report button calls
        cls.report = cls.env.ref('account_reports.general_ledger_report')
        cls.handler = cls.env['account.general.ledger.report.handler']
        cls.default_options = cls._generate_options_standalone(cls.report, '2024-01-01', '2024-12-31')
        cls.default_options['date']['period_type'] = 'year'

        base_query = cls.report._get_report_query(cls.default_options, 'from_beginning')
        cls.env['account.move.line']._apply_ir_rules(base_query)
        cls.report._init_currency_table(cls.default_options)
        currency_table_query = {
            'join': cls.report._currency_table_aml_join(cls.default_options),
            'balance': cls.report._currency_table_apply_rate(SQL("account_move_line.balance")),
            'debit': cls.report._currency_table_apply_rate(SQL("account_move_line.debit")),
            'credit': cls.report._currency_table_apply_rate(SQL("account_move_line.credit")),
            'residual': cls.report._currency_table_apply_rate(SQL("account_move.amount_residual")),
        }
        cls.report_args = [cls.default_options, currency_table_query]

    # Required to get around an access error
    @classmethod
    def _generate_options_standalone(cls, report, date_from, date_to, default_options=None):
        ''' Create new options at a certain date.
        :param report:          The report.
        :param date_from:       A datetime object, str representation of a date or False.
        :param date_to:         A datetime object or str representation of a date.
        :return:                The newly created options.
        '''
        if isinstance(date_from, datetime):
            date_from_str = fields.Date.to_string(date_from)
        else:
            date_from_str = date_from

        if isinstance(date_to, datetime):
            date_to_str = fields.Date.to_string(date_to)
        else:
            date_to_str = date_to

        if not default_options:
            default_options = {}

        return report.get_options({
            'selected_variant_id': report.id,
            'date': {
                'date_from': date_from_str,
                'date_to': date_to_str,
                'mode': 'range',
                'filter': 'custom',
            },
            'show_account': True,
            'show_currency': True,
            **default_options,
        })

    def test_lib_3_7(self):
        with freeze_time('2023-06-01'):     # Before the report period, should still be reported
            self._make_in_move(self.product_a, 13, unit_cost=100)
            self._make_in_move(self.product_a, 1, unit_cost=150)
        with freeze_time('2024-06-01'):     # Within the report period, should be reported
            self._make_in_move(self.product_a, 1, unit_cost=50)
            self._make_out_move(self.product_a, 2)
        with freeze_time('2025-06-01'):     # After the report period, should not be reported
            self._make_out_move(self.product_a, 10)
        report_data = self.handler._l10n_pe_get_lib_3_7_data(*self.report_args)
        self.assertEqual([OrderedDict(data) for data in report_data], [OrderedDict({
                'report_date': '20241231',
                'catalog_code': '1',
                'product_category_type': '01',
                'product_default_code': 'AAA',
                'product_catalog_code': '1',
                'product_unspsc_code_b': '01010101',
                'product_name': 'Product A',
                'product_uom_code': 'NIU',
                'product_valuation_code': '1',
                'stock_quantity': '13.00',
                'stock_unit_cost': '100.00',
                'stock_value': '1300.00',
                'op_status': '1'
        })])

    def test_lib_3_7_zero_quantity(self):
        with freeze_time('2024-06-01'):
            self._make_in_move(self.product_a, 2, unit_cost=100)
            self._make_out_move(self.product_a, 2)
        report_data = self.handler._l10n_pe_get_lib_3_7_data(*self.report_args)
        self.assertEqual([OrderedDict(data) for data in report_data], [])
