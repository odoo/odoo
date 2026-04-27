# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheet
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestSaleTimesheetEnterpriseRanking(TestCommonSaleTimesheet):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.period_start = datetime(2023, 4, 1, 7, 0, 0)
        cls.period_end = datetime(2023, 4, 30, 18, 0, 0)
        cls.today = datetime(2023, 4, 25, 7, 0, 0)
        cls.so = cls.env['sale.order'].create({
            'company_id': cls.employee_user.company_id.id,
            'partner_id': cls.partner_a.id,
            'partner_invoice_id': cls.partner_a.id,
            'partner_shipping_id': cls.partner_a.id,
            'pricelist_id': cls.company_data['default_pricelist'].id,
        })
        cls.sol = cls.env['sale.order.line'].create({
            'product_id': cls.product_order_timesheet3.id,
            'product_uom_qty': 10,
            'order_id': cls.so.id,
        })
        cls.project_billable = cls.env['project.project'].create({
            'name': 'Billable project',
            'sale_line_id': cls.sol.id,
            'allow_billable': True,
        })
        cls.task_billable = cls.env['project.task'].create({
            'name': 'Billable Task',
            'sale_line_id': cls.sol.id,
            'project_id': cls.project_billable.id,
        })
        cls.employee_user.billable_time_target = 160
        cls.env['res.config.settings'].create({'timesheet_show_rates': True, 'timesheet_show_leaderboard': True})

    def test_fetch_tip(self):
        """ This test will check that a tip is actually returned when calling get_timesheet_ranking_data() with fetch_tip parameter set to true. """
        data = self.company_data['company'].get_timesheet_ranking_data(self.period_start, self.period_end, self.today, True)
        self.assertTrue(data.get('tip'), 'A tip should be set in the company\'s timesheet ranking data.')

    def test_total_time_target(self):
        """ This test will check that the total time target variable is correct when calling get_timesheet_ranking_data(). This
            variable is set if today's date is set in between or after the time window (in between period_start and
            period_end or after period_end).
        """
        data = [self.company_data['company'].get_timesheet_ranking_data(self.period_start, self.period_end, date, False) for date in [
            datetime(2023, 4, 15, 0, 0, 0),
            datetime(2023, 5, 1, 0, 0, 0),
            datetime(2023, 3, 31, 0, 0, 0),
        ]]

        self.assertIsNotNone(data[0].get('total_time_target'), 'Today\'s date is set between the time window, so total_time_target should be set.')
        self.assertIsNotNone(data[1].get('total_time_target'), 'Today\'s date is set after the time window, so total_time_target should be set.')
        self.assertFalse(data[2].get('total_time_target'), 'Today\'s date is set after the time window, so total_time_target should be set to false.')

    def test_total_time(self):
        """ This test will check that the user's total time and total valid time in their ranking is correct. For
        example if the user has timesheeted in the future, this time is invalidated and excluded in the total valid
        time calculation. The total time is the same except there is no invalidation system based on the time.
        """
        self.env['account.analytic.line'].create({
            'employee_id': self.employee_user.id,
            'unit_amount': 8,
            'date': datetime(2023, 4, 15, 7, 0, 0, 0),  # before self.today
            'project_id': self.project_billable.id,
            'task_id': self.task_billable.id,
        })  # self.today is past the timesheet's date so it should be counted in total_valid_time
        ranking_data = self.employee_user.company_id.get_timesheet_ranking_data(self.period_start, self.period_end, self.today, False)
        self.assertEqual(ranking_data['leaderboard'][0]['total_valid_time'], 8.0, 'The employee\'s total valid time should be 8 since today\'s date is past the timesheet\'s date.')
        self.assertEqual(ranking_data['leaderboard'][0]['total_time'], 8.0, 'The employee\'s total time should be 8.')

        self.env['account.analytic.line'].create({
            'employee_id': self.employee_user.id,
            'unit_amount': 8,
            'date': datetime(2023, 4, 26, 7, 0, 0, 0),  # after self.today
            'project_id': self.project_billable.id,
            'task_id': self.task_billable.id,
        })  # the timesheet's date is past self.today so it should be counted in total_valid_time
        ranking_data = self.employee_user.company_id.get_timesheet_ranking_data(self.period_start, self.period_end, self.today, False)
        self.assertEqual(ranking_data['leaderboard'][0]['total_valid_time'], 8.0, 'The employee\'s total valid time should still be 8 since the timesheet\'s date is past today\'s date (and so invalid).')
        self.assertEqual(ranking_data['leaderboard'][0]['total_time'], 16.0, 'The employee\'s total time should be 16.')

    def test_get_billable_time_target(self):
        """ When 2 users from 2 different companies are linked to the same user, we have 2 values for billable_time_target (1 from each employee),
        This Test makes sure we get the value of the employee with company = env.company
        """
        self.employee_company_B.write({"company_id": self.env.company.id, "billable_time_target": 200})
        self.employee_manager.write({
            "company_id": self.company_data_2['company'].id,
            "user_id": self.employee_company_B.user_id.id,
            "billable_time_target": 100,
        })

        self.assertEqual(
            self.env["hr.employee"].get_billable_time_target(self.employee_company_B.user_id.ids), [{
                'id': self.employee_company_B.id,
                'billable_time_target': self.employee_company_B.billable_time_target,
            }]
        )

        self.env.company = self.company_data_2['company']
        self.assertEqual(
            self.env["hr.employee"].get_billable_time_target(self.employee_company_B.user_id.ids), [{
                'id': self.employee_manager.id,
                'billable_time_target': self.employee_manager.billable_time_target
            }]
        )
