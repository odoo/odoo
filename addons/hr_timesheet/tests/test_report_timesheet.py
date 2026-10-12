from odoo.tests import tagged

from odoo.addons.hr_timesheet.tests.test_timesheet import TestCommonTimesheet


@tagged('post_install', '-at_install')
class TestReportTimesheet(TestCommonTimesheet):
    """ Check the 'Timesheets' printable report is generated with the right entries,
        whichever record it is printed from.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.subtask = cls.env['project.task'].create({
            'name': 'Sub Task One',
            'project_id': cls.project_customer.id,
            'parent_id': cls.task1.id,
        })
        cls.timesheet_task1, cls.timesheet_subtask, cls.timesheet_project = cls.env['account.analytic.line'].create([{
            'name': 'Timesheet on the task',
            'project_id': cls.project_customer.id,
            'task_id': cls.task1.id,
            'unit_amount': 3.0,
            'employee_id': cls.empl_employee.id,
        }, {
            'name': 'Timesheet on the sub-task',
            'project_id': cls.project_customer.id,
            'task_id': cls.subtask.id,
            'unit_amount': 2.0,
            'employee_id': cls.empl_employee.id,
        }, {
            'name': 'Timesheet on the project',
            'project_id': cls.project_customer.id,
            'unit_amount': 1.0,
            'employee_id': cls.empl_employee.id,
        }])

    def _render_report(self, report_xml_id, records):
        return self.env['ir.actions.report']._render_qweb_html(report_xml_id, records.ids)[0].decode()

    def test_report_from_timesheets(self):
        report = self._render_report('hr_timesheet.timesheet_report', self.timesheet_task1 + self.timesheet_project)
        self.assertIn('Timesheet on the task', report)
        self.assertIn('Timesheet on the project', report)
        self.assertNotIn('Timesheet on the sub-task', report)
        self.assertIn(self.user_employee.partner_id.name, report)

    def test_report_from_timesheets_grouped_by_task(self):
        report = self._render_report('hr_timesheet.timesheet_report_task_timesheets', self.timesheet_task1 + self.timesheet_subtask)
        self.assertIn('Timesheet on the task', report)
        self.assertIn('Timesheet on the sub-task', report)
        self.assertNotIn('Timesheet on the project', report)

    def test_report_from_task(self):
        """ The report printed from a task contains its timesheets and the ones of its sub-tasks. """
        report = self._render_report('hr_timesheet.timesheet_report_task', self.task1)
        self.assertIn(self.task1.name, report)
        self.assertIn('Timesheet on the task', report)
        self.assertIn(self.subtask.name, report)
        self.assertIn('Timesheet on the sub-task', report)
        self.assertNotIn('Timesheet on the project', report)

    def test_report_from_project(self):
        report = self._render_report('hr_timesheet.timesheet_report_project', self.project_customer)
        self.assertIn(self.project_customer.name, report)
        self.assertIn('Timesheet on the task', report)
        self.assertIn('Timesheet on the sub-task', report)
        self.assertIn('Timesheet on the project', report)

    def test_report_from_project_without_timesheet(self):
        project = self.env['project.project'].create({
            'name': 'Project without timesheet',
            'allow_timesheets': True,
        })
        report = self._render_report('hr_timesheet.timesheet_report_project', project)
        self.assertNotIn('Timesheet on the task', report)
