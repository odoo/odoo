from odoo.tests import tagged

from odoo.addons.project.tests.test_project_sharing import TestProjectSharingCommon
from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheet


@tagged('post_install', '-at_install')
class TestPortalSaleTimesheet(TestProjectSharingCommon, TestCommonSaleTimesheet):

    def test_sale_timesheet_linked_to_draft_sol_portal(self):
        """
        This test ensure that timesheets that are linked to a sol in draft are not displayed in the portal views.
        """
        timesheet_domain = self.env['account.analytic.line'].with_user(self.user_portal)._timesheet_get_portal_domain()
        sale_order = self.env['sale.order'].create({
            'partner_id': self.user_portal.partner_id.id,
            'partner_invoice_id': self.user_portal.partner_id.id,
            'partner_shipping_id': self.user_portal.partner_id.id,
        })
        so_line_order_no_task = self.env['sale.order.line'].create({
            'product_id': self.product_order_timesheet1.id,
            'product_uom_qty': 10,
            'order_id': sale_order.id,
        })
        self.task_portal.sale_line_id = so_line_order_no_task.id
        timesheet_entry = self.env['account.analytic.line'].create({
            'name': 'Timesheet',
            'project_id': self.project_portal.id,
            'task_id': self.task_portal.id,
            'employee_id': self.employee_user.id,
            'validated': True,
        })

        timesheets = self.env['account.analytic.line'].search(timesheet_domain)
        self.assertIn(timesheet_entry.id, timesheets.ids,
                      "Portal user should see the timesheet when its sol is not set.")

        timesheet_entry.so_line = so_line_order_no_task.id
        timesheets = self.env['account.analytic.line'].search(timesheet_domain)
        self.assertNotIn(timesheet_entry.id, timesheets.ids,
                      "Portal user should not see the timesheet when its sol is in draft.")

        sale_order.action_confirm()
        timesheets = self.env['account.analytic.line'].search(timesheet_domain)
        self.assertIn(timesheet_entry.id, timesheets.ids,
                      "Portal user should see the timesheet when its sol is not in draft.")
