# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.project.tests.test_project_base import TestProjectCommon
from odoo.tests import tagged
from odoo import Command

@tagged('-at_install', 'post_install')
class TestProjectMrp(TestProjectCommon):
    def test_project_profitability_with_manufacturing_orders(self):
        #  When the analytic account has some manufacturing orders , they should be counted only once
        analytic_plan = self.env['account.analytic.plan'].create({
            'name': 'Plan A',
            'company_id': False,
        })
        analytic_account = self.env['account.analytic.account'].create({
            'name': 'Project - AA',
            'code': 'AA-1234',
            'plan_id': analytic_plan.id,
        })
        project = self.env['project.project'].with_context({'mail_create_nolog': True}).create({
            'name': 'Project',
            'analytic_account_id': analytic_account.id,
        })
        product, component = self.env['product.product'].create([
            {
                'name': 'Product',
                'type': 'product',
                'standard_price': 233.0,
            },
            {
                'name': 'Component',
                'type': 'product',
                'standard_price': 10.0,
            },
        ])
        bom = self.env['mrp.bom'].create({
            'product_id': product.id,
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                Command.create({'product_id': component.id, 'product_qty': 1.0}),
            ]})
        product.button_bom_cost()
        mo = self.env['mrp.production'].create({
            'product_id': product.id,
            'bom_id': bom.id,
            'product_qty': 10.0,
            'analytic_account_id': analytic_account.id,
        })
        mo.action_confirm()
        mo.button_mark_done()
        items = project._get_profitability_items(False)
        self.assertDictEqual(
            items,
            {
                'revenues': {'data': [], 'total': {'invoiced': 0.0, 'to_invoice': 0.0}},
                'costs': {'data': [{'id': 'manufacturing_order', 'sequence': project._get_profitability_sequence_per_invoice_type()['manufacturing_order'],
                                    'billed': -100.0, 'to_bill': 0.0}], 'total': {'billed': -100.0, 'to_bill': 0.0}}
            },
            'The manufacturing orders data should be counted once'
        )
