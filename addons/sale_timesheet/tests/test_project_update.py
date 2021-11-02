# -*- coding: utf-8 -*-
<<<<<<< HEAD
# Part of Odoo. See LICENSE file for full copyright and licensing details.
=======

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
>>>>>>> af15942e8cf... temp
from freezegun import freeze_time

from odoo.tests import tagged
from odoo.addons.project.tests.test_project_update_flow import TestProjectUpdate

@tagged('-at_install', 'post_install')
class TestProjectUpdateSaleTimesheet(TestProjectUpdate):

    def test_project_update_description_profitability(self):
<<<<<<< HEAD
        self.project_pigs.allow_billable = True
        template_values = self.env['project.update']._get_template_values(self.project_pigs)
=======
        today = date.today()
        with freeze_time(today + timedelta(hours=12)):
            template_values = self.env['project.update']._get_template_values(self.project_pigs)

        self.assertEqual(template_values['profitability']['month'], today.strftime('%B %Y'),
                         "The month used in the template should be well defined")
        self.assertEqual(template_values['profitability']['previous_month'], (today + relativedelta(months=-1)).strftime('%B'),
                         "The previous month used in the template should be well defined")
        self.assertTrue(template_values['profitability']['is_timesheet_uom_hour'], "Default timesheet uom is hour.")
        self.assertEqual(template_values['profitability']['timesheet_uom'], "hours", "Default timesheet uom should be displayed as 'hours'")
        self.assertEqual(template_values['profitability']['timesheet_unit_amount'], '0', "Timesheet unit amount used in the template should be defined.")
        self.assertEqual(template_values['profitability']['previous_timesheet_unit_amount'], '0', "Previous Timesheet unit amount used in the template should be defined.")
        self.assertEqual(template_values['profitability']['timesheet_trend'], "0", "Timesheet trend used in the template should be well defined.")
>>>>>>> af15942e8cf... temp
        self.assertEqual(template_values['profitability']['costs'], "$\xa00.00", "Project costs used in the template should be well defined")
        self.assertEqual(template_values['profitability']['revenues'], "$\xa00.00", "Project revenues used in the template should be well defined")
        self.assertEqual(template_values['profitability']['margin'], 0, "Margin used in the template should be well defined")
        self.assertEqual(template_values['profitability']['margin_formatted'], "$\xa00.00", "Margin formatted used in the template should be well defined")
        self.assertEqual(template_values['profitability']['margin_percentage'], "0", "Margin percentage used in the template should be well defined")

    def test_project_update_panel_profitability_no_billable(self):
        panel_data = self.project_pigs.get_panel_data()
        self.assertEqual(panel_data['profitability_items']['allow_billable'], False, "Project should not be billable by default")
        try:
            self.project_pigs.action_view_timesheet()
        except Exception as e:
            raise AssertionError("Error raised unexpectedly while calling the action defined in profitalities action panel data ! Exception : " + e.args[0])

        try:
            self.project_pigs.action_view_timesheet()
        except Exception as e:
            raise AssertionError("Error raised unexpectedly while calling the action defined in profitalities action panel data ! Exception : " + e.args[0])
