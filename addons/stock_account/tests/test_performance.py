# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import time
from datetime import timedelta

from odoo import fields
from odoo.cli.populate import Populate
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.stock_account.tests.common import TestStockValuationCommon

_logger = logging.getLogger(__name__)


@tagged('-standard', 'stock_account_performance', '-at_install', 'post_install')
class TestStockValuationReportPerformance(TestStockValuationCommon):
    """ Populate-based performance tests for the aggregate Stock Valuation
    report, at scale on AVCO-automated, lot-valuated products.

    These tests are excluded from the standard test suite; run explicitly with
    e.g. `--test-tags stock_account_performance`.
    """

    def _create_avco_lot_product(self, name):
        product = self.env['product.product'].create({
            **self.product_common_vals,
            'name': name,
            'categ_id': self.category_avco_auto.id,
            'tracking': 'lot',
            'lot_valuated': True,
        })
        lots = self.env['stock.lot'].create([
            {'name': f'{name}-{i}', 'product_id': product.id}
            for i in range(10)
        ])
        for lot in lots:
            self._make_in_move(product=product, quantity=10.0, unit_cost=10.0, lot_ids=lot)
        return product

    @mute_logger('odoo.cli.populate', 'odoo.tools.populate')
    def _populate_to_product_template_count(self, total_count):
        """ Duplicate product.template/product.product/stock.lot/stock.move/
        stock.move.line/stock.quant with the same factor, so every duplicated
        product keeps its own 10 lots + 10 done moves (with matching quants).

        product.product, stock.move.line and stock.quant must be listed
        explicitly: their one2many inverses (product_variant_ids,
        move_line_ids) are declared copy=False, so the populate engine's
        auto-cascade never duplicates them on its own.
        """
        before_count = self.env['product.template'].search_count([])
        factor = round(total_count / before_count) - 1
        if factor < 1:
            _logger.warning(
                "Skipping populate: %s existing product.template records already "
                "exceed the %s target.", before_count, total_count)
            return False
        Populate.populate(self.env, {
            'product.template': factor,
            'product.product': factor,
            'stock.lot': factor,
            'stock.move': factor,
            'stock.move.line': factor,
            'stock.quant': factor,
        }, 1)
        self.env.invalidate_all()
        return True

    def _get_report_values(self, report, label, **kwargs):
        query_count_before = self.env.cr.sql_log_count
        start = time.time()
        values = report.get_report_values(**kwargs)
        _logger.info(
            "get_report_values(%s): %.2fs, %s queries",
            label, time.time() - start, self.env.cr.sql_log_count - query_count_before)
        return values

    def _test_get_report_values_performance(self, total_count):
        self._create_avco_lot_product(f'Perf Product {total_count}')
        self.env.flush_all()
        if not self._populate_to_product_template_count(total_count):
            return

        report = self.env['stock_account.stock.valuation.report']

        # "Today" behavior: date=False, uses the current qty_available/total_value.
        today_values = self._get_report_values(report, 'today, no date')
        self.assertTrue(today_values['data']['ending_stock']['value'])

        # "at_date" behavior: an explicit date (tomorrow, so it isn't reset to
        # False by the `date == context_today` check) exercises the historical
        # at_date valuation path instead.
        tomorrow = fields.Date.to_string(fields.Date.context_today(self) + timedelta(days=1))
        at_date_values = self._get_report_values(report, f'at_date={tomorrow}', date=tomorrow)
        self.assertEqual(
            at_date_values['data']['ending_stock']['value'],
            today_values['data']['ending_stock']['value'])

    def test_get_report_values_performance_1k(self):
        self._test_get_report_values_performance(1000)

    def test_get_report_values_performance_5k(self):
        self._test_get_report_values_performance(5000)

    def test_get_report_values_performance_10k(self):
        self._test_get_report_values_performance(10000)
