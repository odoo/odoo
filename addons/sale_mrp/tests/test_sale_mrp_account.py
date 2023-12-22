# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import test_multistep_manufacturing
from odoo.tests import common


@common.tagged('post_install', '-at_install')
class TestSaleMrpAccount(test_multistep_manufacturing.TestMultistepManufacturing):
    def test_mo_analytic_distribution(self):
        """ ensure analytic account/distribution is inherited from the SO
            when none is set on the bom
        """
        analytic_plan = self.env['account.analytic.plan'].create({
            'name': 'Plan',
        })
        self.sale_order.analytic_account_id = self.env['account.analytic.account'].create({
            'name': 'test_analytic_account',
            'plan_id': analytic_plan.id,
        })
        self.sale_order.action_confirm()
        self.sale_order.invalidate_recordset(['mrp_production_ids'])
        self.assertTrue(self.sale_order.mrp_production_ids.analytic_distribution)
        self.assertTrue(self.sale_order.mrp_production_ids.analytic_account_ids)
