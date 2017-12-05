# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_performance.tests.test_performance import TestPerformance, queryCount


class TestPortalPerformance(TestPerformance):

    @queryCount(admin=3, demo=3)
    def test_read_mail(self):
        pass
