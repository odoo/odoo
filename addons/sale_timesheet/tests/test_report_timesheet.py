from odoo.tests import tagged

from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheet


@tagged('post_install', '-at_install')
class TestReportTimesheetSale(TestCommonSaleTimesheet):
    """ Check the 'Timesheets' printable report is generated with the right entries when
        printed from a sales order or from an invoice.
    """

    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner_a.id,
            'partner_invoice_id': cls.partner_a.id,
            'partner_shipping_id': cls.partner_a.id,
        })
        cls.so_line = cls.env['sale.order.line'].create({
            'product_id': cls.product_delivery_timesheet2.id,
            'product_uom_qty': 50,
            'order_id': cls.sale_order.id,
        })
        cls.sale_order.action_confirm()
        cls.timesheet = cls.env['account.analytic.line'].create({
            'name': 'Timesheet to invoice',
            'project_id': cls.so_line.task_id.project_id.id,
            'task_id': cls.so_line.task_id.id,
            'unit_amount': 4.0,
            'employee_id': cls.employee_user.id,
        })

    def _render_report(self, report_xml_id, records):
        return self.env['ir.actions.report']._render_qweb_html(report_xml_id, records.ids)[0].decode()

    def test_report_from_sale_order(self):
        self.assertEqual(self.so_line.timesheet_ids, self.timesheet)
        report = self._render_report('sale_timesheet.timesheet_report_sale_order', self.sale_order)
        self.assertIn('Timesheet to invoice', report)
        self.assertIn(self.sale_order.name, report)

    def test_report_from_invoice(self):
        invoice = self.sale_order._create_invoices()
        self.assertEqual(self.timesheet.reinvoice_move_id, invoice)
        self.assertEqual(invoice.timesheet_ids, self.timesheet)

        report = self._render_report('sale_timesheet.timesheet_report_account_move', invoice)
        self.assertIn('Timesheet to invoice', report)

    def test_report_from_sale_order_without_timesheet(self):
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'product_id': self.product_delivery_timesheet2.id,
                'product_uom_qty': 1,
            })],
        })
        report = self._render_report('sale_timesheet.timesheet_report_sale_order', sale_order)
        self.assertNotIn('Timesheet to invoice', report)
