from odoo.tests import tagged

from odoo.addons.project.tests.test_project_sharing import TestProjectSharingCommon


@tagged('post_install', '-at_install')
class TestPortalSaleTimesheet(TestProjectSharingCommon):

    def test_sale_timesheet_linked_to_draft_sol_portal(self):
        """
        This test ensure that timesheets that are linked to a sol in draft are not displayed in the portal views.
        """
        partner = self.env['res.partner'].create({'name': "Brick"})
        product_order_service1 = self.env['product.product'].create({
            'name': "Service Ordered, create no task",
            'standard_price': 11,
            'list_price': 13,
            'type': 'service',
            'invoice_policy': 'order',
            'uom_id': self.env.ref('uom.product_uom_hour').id,
            'default_code': 'SERV-ORDERED1',
            'service_tracking': 'no',
            'project_id': False,
        })
        timesheet_domain = self.env['account.analytic.line'].with_user(self.user_portal)._timesheet_get_portal_domain()
        employee = self.env['hr.employee'].create({
            'name': 'Project User Employee',
            'user_id': self.user_projectuser.id,
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
        })
        so_line_order_no_task = self.env['sale.order.line'].create({
            'product_id': product_order_service1.id,
            'product_uom_qty': 10,
            'order_id': sale_order.id,
        })
        task = self.env['project.task'].create({
            'name': 'Task',
            'project_id': self.project_cows.id,
            'sale_line_id': so_line_order_no_task.id,
            'partner_id': self.user_portal.partner_id.id,
        })
        timesheet_entry = self.env['account.analytic.line'].create({
            'name': 'Timesheet',
            'project_id': self.project_cows.id,
            'task_id': task.id,
            'employee_id': employee.id,
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
