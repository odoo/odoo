# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from .test_frontend import TestPosHrHttpCommon
from odoo.addons.point_of_sale.tests.test_pos_report import TestPosReportCommon


@tagged('post_install', '-at_install')
class TestPosReportEmployee(TestPosReportCommon, TestPosHrHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.session.order_ids.employee_id = cls.emp1
        cls.session.order_ids.filtered('is_refund').employee_id = cls.emp2
        cls.session.order_ids.filtered(lambda order: order.state == 'draft').employee_id = cls.emp3
        # An order without an employee must still appear in the unfiltered report.
        cls._create_report_order([(cls.tea, 1, 7, 0)]).employee_id = False

    def test_employee_filter(self):
        info = self.report.get_report_info()
        self.assertIn('employee_id', [f.get('key') for f in info['filters']])
        sections = {
            s['section_id']: s['values']
            for s in self._report_sections(session_id=self.session.id, employee_id=self.emp1.id)
        }

        self.assertEqual(sections['sales']['amount_total'], 330)
        self.assertEqual(sections.get('refunds', {}).get('amount_total', 0), 0)
        self.assertEqual(sections['payments']['amount_total'], 358)
        self.assertNotIn('session_control', sections)

        sections = {
            s['section_id']: s['values']
            for s in self._report_sections(session_id=self.session.id, employee_id=self.emp2.id)
        }
        self.assertEqual(sections.get('sales', {}).get('amount_total', 0), 0)
        self.assertEqual(sections['refunds']['amount_total'], -100)
        self.assertEqual(sections['payments']['amount_total'], -110)
        self.assertNotIn('session_control', sections)

        sections = {
            s['section_id']: s['values']
            for s in self._report_sections(session_id=self.session.id, employee_id=False)
        }
        self.assertEqual(sections['sales']['amount_total'], 337)
        self.assertEqual(sections['refunds']['amount_total'], -100)
        self.assertEqual(sections['payments']['amount_total'], 255)
        self.assertIn('session_control', sections)

    def test_employee_report_scope(self):
        other_config = self.basic_config.copy({'name': 'Other shop'})
        other_config.open_ui()
        self._create_report_order([(self.coffee, 1, 999, 0)], session=other_config.current_session_id).employee_id = self.emp1
        self._create_report_order([(self.coffee, 1, 999, 0)], date='2025-12-31 23:59:59').employee_id = self.emp1
        options = dict(
            config_ids=self.basic_config.ids, employee_id=self.emp1.id,
            date_from='2026-01-01 00:00:00', date_to='2026-01-31 23:59:59',
        )
        sections = {s['section_id']: s['values'] for s in self.report.get_report_data(options)['sections']}
        self.assertEqual(sections['sales']['amount_total'], 330)

        # An employee with only a draft order has no report data or unfold lines.
        options = {**options, 'employee_id': self.emp3.id}
        self.assertEqual(self.report.get_report_data(options)['sections'], [])
        self.assertEqual(self.report.get_unfold_data(options, 'sales')['lines'], [])
