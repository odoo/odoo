# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.website.tests.test_performance import UtilPerf


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestPerformance(UtilPerf):
    def test_10_perf_sql_website_controller_minimalist(self):
        url = '/empty_controller_test'
        select_tables_perf = {
            'orm_signaling_registry': 1,
        }
        self._check_url_hot_query(url, 1, select_tables_perf)
