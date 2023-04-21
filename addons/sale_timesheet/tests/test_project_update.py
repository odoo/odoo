# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time

from odoo.tests import tagged
from odoo.tools import format_amount
from odoo.addons.project.tests.test_project_update_flow import TestProjectUpdate

@tagged('-at_install', 'post_install')
class TestProjectUpdateSaleTimesheet(TestProjectUpdate):

    def test_project_update_description_profitability(self):
        self.project_pigs.allow_billable = True
        template_values = self.env['project.update']._get_template_values(self.project_pigs)

        # Store the formatted amount in the same currency as the project to guarantee the same unit
        comparison_amount = format_amount(self.env, 0.0, self.project_pigs.currency_id)

        self.assertEqual(template_values['profitability']['costs'], 0.0, "Project costs used in the template should be well defined")
        self.assertEqual(template_values['profitability']['costs_formatted'], comparison_amount, "Project costs used in the template should be well defined")
        self.assertEqual(template_values['profitability']['revenues'], 0.0, "Project revenues used in the template should be well defined")
        self.assertEqual(template_values['profitability']['revenues_formatted'], comparison_amount, "Project revenues used in the template should be well defined")
        self.assertEqual(template_values['profitability']['margin'], 0, "Margin used in the template should be well defined")
        self.assertEqual(template_values['profitability']['margin_formatted'], comparison_amount, "Margin formatted used in the template should be well defined")
        self.assertEqual(template_values['profitability']['margin_percentage'], "0", "Margin percentage used in the template should be well defined")

    def test_project_update_panel_profitability_no_billable(self):
        try:
            self.project_pigs.action_view_timesheet()
        except Exception as e:
            raise AssertionError("Error raised unexpectedly while calling the action defined in profitalities action panel data ! Exception : " + e.args[0])

        try:
            self.project_pigs.action_view_timesheet()
        except Exception as e:
            raise AssertionError("Error raised unexpectedly while calling the action defined in profitalities action panel data ! Exception : " + e.args[0])
