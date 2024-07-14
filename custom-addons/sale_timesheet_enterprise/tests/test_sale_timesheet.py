# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo.fields import Date
from odoo.tests import tagged
from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheet


@tagged('-at_install', 'post_install')
class TestSaleTimesheet(TestCommonSaleTimesheet):
    def test_invoice_creation_running_timer(self):
        """ Test that the creation of invoice stop and take into account the running timers. """
        self.env.user.employee_id = self.env['hr.employee'].create({'user_id': self.env.uid})
        Timesheet = self.env['account.analytic.line']
        Task = self.env['project.task']
        today = Date.context_today(self.env.user)

        task = Task.with_context(default_project_id=self.project_template.id).create({
            'name': 'first task',
            'partner_id': self.partner_b.id,
            'allocated_hours': 48,
            'sale_line_id': self.so.order_line[0].id,
        })

        self.project_template.allow_billable = True
        timesheet = Timesheet.create({
            'project_id': self.project_template.id,
            'task_id': task.id,
            'name': 'my first timesheet',
            'unit_amount': 30,
        })
        self.assertEqual(timesheet.so_line, task.sale_line_id)
        timesheet.action_timer_start()
        timesheet.user_timer_id.timer_start = today - timedelta(days=1)

        context = {
            'active_model': 'sale.order',
            'active_ids': [self.so.id],
            'active_id': self.so.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }

        wizard = self.env['sale.advance.payment.inv'].with_context(context).create({
            'advance_payment_method': 'percentage',
            'amount': 50,
        })
        self.assertTrue(wizard.has_timer_running)
        wizard.create_invoices()
        self.assertTrue(timesheet.is_timer_running, 'The running timer should still be running since we did not create a regular invoice.')
        wizard.advance_payment_method = 'delivered'
        wizard.create_invoices()
        self.assertFalse(timesheet.is_timer_running, 'The running timer should be stopped since we generate a regular invoice.')
        self.assertGreater(timesheet.unit_amount, 30)
