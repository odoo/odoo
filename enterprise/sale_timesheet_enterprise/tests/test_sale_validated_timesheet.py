# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import Command
from odoo.tests import tagged

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheet


@tagged('-at_install', 'post_install')
class TestSaleValidatedTimesheet(TestCommonSaleTimesheet):
    """ Test timesheet invoicing of "Approved Timesheets Only" with 2 service products that create a task in a new project.
                1. Create SO, add two SO line ordered service and delivered service and confirm it
                2. log some timesheet on task and validate it.
                3. create invoice
                4. log other timesheets
                5. create a second invoice
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # create SO
        cls.sale_order = cls.env['sale.order'].with_context(tracking_disable=True).create({
            'company_id': cls.env.company.id,
            'partner_id': cls.partner_a.id,
            'partner_invoice_id': cls.partner_a.id,
            'partner_shipping_id': cls.partner_a.id,
            'pricelist_id': cls.company_data['default_pricelist'].id,
        })
        cls.ordered_so_line = cls.env['sale.order.line'].with_context(tracking_disable=True).create({
            'product_id': cls.product_order_timesheet3.id,
            'product_uom_qty': 10,
            'order_id': cls.sale_order.id,
        })
        cls.delivered_so_line = cls.env['sale.order.line'].with_context(tracking_disable=True).create({
            'product_id': cls.product_delivery_timesheet3.id,
            'product_uom_qty': 10,
            'order_id': cls.sale_order.id,
        })

    def test_sale_validated_timesheet(self):
        # set invoiced_timesheet as "Approved timesheet only"
        self.env['ir.config_parameter'].sudo().set_param('sale.invoiced_timesheet', 'approved')
        #  confirm SO
        self.sale_order.action_confirm()

        project_1 = self.env['project.project'].search([('sale_order_id', '=', self.sale_order.id)])
        ordered_task = self.env['project.task'].search([('sale_line_id', '=', self.ordered_so_line.id)])
        delivered_task = self.env['project.task'].search([('sale_line_id', '=', self.delivered_so_line.id)])
        # check project, task and analytic account
        self.assertEqual(self.sale_order.tasks_count, 2, "Two task should have been created on SO confirmation")
        self.assertEqual(len(self.sale_order.project_ids), 1, "One project should have been created on SO confirmation")
        self.assertEqual(self.sale_order.project_id, project_1, "The created project should be linked to the project of the SO")

        yesterday = date.today() - relativedelta(days=1)
        week_before = date.today() + relativedelta(weeks=-1)
        # log timesheet on task of delivered So line
        delivered_timesheet1 = self.env['account.analytic.line'].create({
            'name': 'Timesheet delivered 1',
            'project_id': delivered_task.project_id.id,
            'task_id': delivered_task.id,
            'unit_amount': 6,
            'employee_id': self.employee_user.id,
            'date': week_before,
        })
        delivered_timesheet2 = self.env['account.analytic.line'].create({
            'name': 'Timesheet delivered 2',
            'project_id': delivered_task.project_id.id,
            'task_id': delivered_task.id,
            'unit_amount': 4,
            'employee_id': self.employee_user.id,
            'date': yesterday,
        })
        # log timesheet on task of ordered so line
        ordered_timesheet1 = self.env['account.analytic.line'].create({
            'name': 'Timesheet ordered 1',
            'project_id': ordered_task.project_id.id,
            'task_id': ordered_task.id,
            'unit_amount': 8,
            'employee_id': self.employee_user.id,
            'date': week_before,
        })
        ordered_timesheet2 = self.env['account.analytic.line'].create({
            'name': 'Timesheet ordered 2',
            'project_id': ordered_task.project_id.id,
            'task_id': ordered_task.id,
            'unit_amount': 2,
            'employee_id': self.employee_user.id,
            'date': yesterday,
        })

        # check not any timesheet should be validated
        self.assertFalse(any([delivered_timesheet1.validated, delivered_timesheet2.validated, ordered_timesheet1.validated, ordered_timesheet2.validated]), 'Timesheet should not be validated')

        # Validate ordered and delivered some Timesheet
        timesheet_to_validate = delivered_timesheet1 | ordered_timesheet1
        timesheet_to_validate.action_validate_timesheet()
        # check if timesheets are validated
        self.assertTrue(delivered_timesheet1.validated)
        self.assertTrue(ordered_timesheet1.validated)

        self.assertTrue(any([delivered_timesheet1.validated, ordered_timesheet1.validated]), 'Timesheet should be validated')
        # check timesheet is linked to SOL
        self.assertEqual(delivered_timesheet1.so_line.id, self.delivered_so_line.id, "The delivered timesheet should be linked to Delivered SOL")
        self.assertEqual(ordered_timesheet1.so_line.id, self.ordered_so_line.id, "The ordered timesheet should be linked to ordered SOL")
        # check delivered quantity on SOL
        self.assertEqual(self.ordered_so_line.qty_delivered, 8, 'Delivered quantity should be 8 as some timesheet is validated')
        self.assertEqual(self.delivered_so_line.qty_delivered, 6, 'Delivered quantity should be 6 as some timesheet is validated')

        # invoice SO
        invoice1 = self.sale_order._create_invoices()
        # check invoiced amount
        self.assertEqual(invoice1.amount_total, self.ordered_so_line.price_unit * 10 + self.delivered_so_line.price_unit * 6, 'Invoiced amount should be equal to Ordered SOL + Delivered SOL unit price * 6')
        # check timesheet is linked to invoice
        self.assertEqual(delivered_timesheet1.timesheet_invoice_id, invoice1, "The delivered timesheet should be linked to the invoice")
        self.assertFalse(ordered_timesheet1.timesheet_invoice_id, "The ordered timesheet should not be linked to the invoice, since we are in ordered quantity")

        # check invoiced quantity on sale order and on invoice
        ordered_invoice_line = self.ordered_so_line.invoice_lines.filtered(lambda line: line.move_id == invoice1)
        self.assertEqual(self.ordered_so_line.qty_invoiced, ordered_invoice_line.quantity, "The invoiced quantity should be same on sales order line and invoice line")
        delivered_invoice_line = self.delivered_so_line.invoice_lines.filtered(lambda line: line.move_id == invoice1)
        self.assertEqual(self.delivered_so_line.qty_invoiced, delivered_invoice_line.quantity, "The invoiced quantity should be same on sales order line and invoice line")

        # Validate remaining Timesheet
        timesheet_to_validate = delivered_timesheet2 | ordered_timesheet2
        timesheet_to_validate.action_validate_timesheet()

        self.assertTrue(any([delivered_timesheet2.validated, ordered_timesheet2.validated]), 'Timesheet should be validated')
        # check remaining timesheet is linked to SOL
        self.assertEqual(delivered_timesheet2.so_line.id, self.delivered_so_line.id, "The delivered timesheet should be linked to Delivered SOL")
        self.assertEqual(ordered_timesheet2.so_line.id, self.ordered_so_line.id, "The ordered timesheet should be linked to ordered SOL")
        # check delivered quantity on SOL
        self.assertEqual(self.ordered_so_line.qty_delivered, 10, 'All quantity should be delivered')
        self.assertEqual(self.delivered_so_line.qty_delivered, 10, 'All quantity should be delivered')

        # invoice remaining SO
        invoice2 = self.sale_order._create_invoices()

        # check invoiced amount
        self.assertEqual(invoice2.amount_total, self.delivered_so_line.price_unit * 4, 'Invoiced amount should be equal to Delivered SOL unit price * 4')
        self.assertEqual(invoice1.amount_total+invoice2.amount_total, self.ordered_so_line.price_unit * 10 + self.delivered_so_line.price_unit * 10, 'Invoiced amount should be equal to Ordered SOL + Delivered SOL')
        # check invoiced quantity on sale order and on invoice
        ordered_invoice_line2 = self.ordered_so_line.invoice_lines.filtered(lambda line: line.move_id == invoice2)
        self.assertFalse(ordered_invoice_line2, "For ordered quantity so line we already invoiced full quantity on previous invoice so it should not be invoied now")
        delivered_invoice_line2 = self.delivered_so_line.invoice_lines.filtered(lambda line: line.move_id == invoice2)
        self.assertEqual(self.delivered_so_line.qty_invoiced, delivered_invoice_line.quantity + delivered_invoice_line2.quantity, "The invoiced quantity should be same on sales order line and invoice line")
        # order should be fully invoiced
        self.assertEqual(self.sale_order.invoice_status, 'invoiced', "The SO invoice status should be fully invoiced")

    def test_project_sharing_with_validated_timesheet_invoicing(self):
        """ This test check if the portal user in project sharing see only the totals based on the timesheets
            are computed on the validated timesheets only and not all the timesheets related to a task.
            Because the portal user will only see the validated timesheets and not all ones.

            Also assures that internal users will see the same results when they access the portal
            view

            Test Case:
            =========

        """
        # set invoiced_timesheet as "Approved timesheet only"
        self.env['ir.config_parameter'].sudo().set_param('sale.invoiced_timesheet', 'approved')
        #  confirm SO
        self.sale_order.action_confirm()

        project_1 = self.env['project.project'].search([('sale_order_id', '=', self.sale_order.id)])
        ordered_task = self.env['project.task'].search([('sale_line_id', '=', self.ordered_so_line.id)])
        portal_user = mail_new_test_user(self.env, 'Portal user', groups='base.group_portal')

        self.env['project.share.wizard'].create({
            'res_model': 'project.project',
            'res_id': project_1.id,
            'collaborator_ids': [
                Command.create({'partner_id': portal_user.partner_id.id, 'access_mode': 'edit'}),
            ],
        })
        ordered_task.message_subscribe(partner_ids=portal_user.partner_id.ids)
        fields_to_fetch = ['portal_remaining_hours', 'portal_effective_hours', 'portal_total_hours_spent', 'portal_subtask_effective_hours', 'portal_progress']
        basic_task_read = ordered_task.read(fields_to_fetch)[0]
        portal_task_read = ordered_task.with_user(portal_user).read(fields_to_fetch)[0]

        self.assertDictEqual(basic_task_read, portal_task_read)

        today = date.today()
        self.env['account.analytic.line'].create({
            'name': 'Timesheet ordered 1',
            'project_id': ordered_task.project_id.id,
            'task_id': ordered_task.id,
            'unit_amount': 8,
            'employee_id': self.employee_user.id,
            'date': today,
        })

        ordered_task.invalidate_recordset(fields_to_fetch)
        basic_task_read = ordered_task.read(fields_to_fetch)[0]
        ordered_task.invalidate_recordset(fields_to_fetch)
        portal_task_read = ordered_task.with_user(portal_user).read(fields_to_fetch)[0]

        self.assertEqual(basic_task_read['portal_remaining_hours'], 10)
        self.assertEqual(basic_task_read['portal_effective_hours'], 0)
        self.assertEqual(basic_task_read['portal_subtask_effective_hours'], 0)
        self.assertEqual(basic_task_read['portal_total_hours_spent'], 0)
        self.assertEqual(basic_task_read['portal_progress'], 0)

        self.assertEqual(portal_task_read['portal_remaining_hours'], 10)
        self.assertEqual(portal_task_read['portal_effective_hours'], 0)
        self.assertEqual(portal_task_read['portal_subtask_effective_hours'], 0)
        self.assertEqual(portal_task_read['portal_total_hours_spent'], 0)
        self.assertEqual(portal_task_read['portal_progress'], 0)

        self.env['account.analytic.line'].create({
            'name': 'Timesheet ordered 2',
            'project_id': ordered_task.project_id.id,
            'task_id': ordered_task.id,
            'unit_amount': 2,
            'employee_id': self.employee_user.id,
            'date': today,
            'validated': True
        })

        ordered_task.invalidate_recordset(fields_to_fetch)
        basic_task_read = ordered_task.read(fields_to_fetch)[0]
        ordered_task.invalidate_recordset(fields_to_fetch)
        portal_task_read = ordered_task.with_user(portal_user).read(fields_to_fetch)[0]

        self.assertEqual(basic_task_read['portal_remaining_hours'], 8)
        self.assertEqual(basic_task_read['portal_effective_hours'], 2)
        self.assertEqual(basic_task_read['portal_subtask_effective_hours'], 0)
        self.assertEqual(basic_task_read['portal_total_hours_spent'], 2)
        self.assertEqual(basic_task_read['portal_progress'], 0.2)

        self.assertEqual(portal_task_read['portal_remaining_hours'], 8)
        self.assertEqual(portal_task_read['portal_effective_hours'], 2)
        self.assertEqual(portal_task_read['portal_subtask_effective_hours'], 0)
        self.assertEqual(portal_task_read['portal_total_hours_spent'], 2)
        self.assertEqual(portal_task_read['portal_progress'], 0.2)

    def test_block_edit_so_line_validated_timesheet(self):
        """
            The purpose is to check that it is not possible to modify the sale order line
            if the timesheet is validated when we call the logic that updates the
            timesheet sale order lines.
        """
        self.sale_order.action_confirm()
        ordered_task = self.env['project.task'].search([('sale_line_id', '=', self.ordered_so_line.id)])
        today = date.today()
        not_validated_timesheet, validated_timesheet = self.env['account.analytic.line'].create([
            {
                'name': 'Timesheet ordered not validated',
                'project_id': ordered_task.project_id.id,
                'task_id': ordered_task.id,
                'unit_amount': 2,
                'employee_id': self.employee_user.id,
                'date': today,
            },
            {
                'name': 'Timesheet ordered validated',
                'project_id': ordered_task.project_id.id,
                'task_id': ordered_task.id,
                'unit_amount': 2,
                'employee_id': self.employee_user.id,
                'date': today,
            }
        ])
        employee_map = self.env['project.sale.line.employee.map'].create(
        {
            'project_id': ordered_task.project_id.id,
            'employee_id': self.employee_user.id,
            'sale_line_id': ordered_task.sale_line_id.id,
        })
        employee_map.sale_line_id = ordered_task.sale_line_id.id
        validated_timesheet.validated = True

        other_sale_line = self.sale_order.order_line.filtered(lambda sl: sl.id != ordered_task.sale_line_id.id)[-1]
        employee_map.sale_line_id = other_sale_line
        ordered_task.project_id._update_timesheets_sale_line_id()

        self.assertEqual(not_validated_timesheet.so_line, other_sale_line)  # sale order line is updated
        self.assertEqual(validated_timesheet.so_line, ordered_task.sale_line_id)  # sale order line is not updated

    def test_create_invoice_for_past_validated_timesheet(self):
        self.env['ir.config_parameter'].sudo().set_param('sale.invoiced_timesheet', 'approved')
        self.employee_user.timesheet_manager_id = self.user_manager_company_B
        sale_order_2 = self.env['sale.order'].with_context(tracking_disable=True).create({
            'company_id': self.env.company.id,
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
        })

        delivered_so_line = self.env['sale.order.line'].with_context(tracking_disable=True).create({
            'product_id': self.product_delivery_timesheet3.id,
            'product_uom_qty': 10,
            'order_id': sale_order_2.id,
        })
        sale_order_2.action_confirm()

        delivered_task = self.env['project.task'].search([('sale_line_id', '=', delivered_so_line.id)])
        month_before = date.today() + relativedelta(months=-1)
        start_of_month_before = month_before.replace(day=1)
        end_of_month_before = date.today().replace(day=1) - relativedelta(days=1)

        delivered_timesheet1 = self.env['account.analytic.line'].create({
            'name': 'Timesheet delivered 1',
            'project_id': delivered_task.project_id.id,
            'task_id': delivered_task.id,
            'unit_amount': 6,
            'employee_id': self.employee_user.id,
            'date': month_before,
        })
        delivered_timesheet1.action_validate_timesheet()
        self.employee_user.last_validated_timesheet_date = date.today()
        user = self.env['res.users'].create({
            'name': 'Basic User',
            'login': 'basic_user',
            'password': 'password',
            'groups_id': [(6, 0, [
                self.env.ref('project.group_project_user').id,
                self.env.ref('hr_timesheet.group_hr_timesheet_approver').id,
                self.env.ref('sales_team.group_sale_manager').id,
                self.env.ref('account.group_account_user').id,  # Add the accounting accountant group
            ])],
        })
        invoice1 = sale_order_2.with_user(user).with_context(
            timesheet_start_date=start_of_month_before,
            timesheet_end_date=end_of_month_before
        )._create_invoices()
        self.assertTrue(invoice1, 'Invoice should be created')
