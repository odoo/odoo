# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.point_of_sale.tests.common import TestPoSCommon


class TestEmployeeSaleDetails(TestPoSCommon):
    def test_report_only_includes_selected_employee(self):
        self.config = self.basic_config
        session = self.open_new_session()
        product = self.create_product('Report product', self.categ_basic, 10)
        cash_employee, invoice_employee = self.env['hr.employee'].sudo().create([
            {'name': 'A cashier', 'company_id': self.env.company.id},
            {'name': 'B cashier', 'company_id': self.env.company.id},
        ])
        orders = self._create_orders([
            {'pos_order_lines_ui_args': [(product, 1)], 'pos_order_ui_args': {'employee_id': cash_employee.id}},
            {
                'pos_order_lines_ui_args': [(product, 2)],
                'pos_order_ui_args': {'employee_id': invoice_employee.id},
                'payments': [(self.bank_pm1, 20)],
                'customer': self.customer,
                'is_invoiced': True,
            },
        ])
        invoiced_order = next(order for order in orders.values() if order.is_singly_invoiced)

        cash_report, invoice_report = session.get_employees_sale_details()
        wizard = self.env['pos.daily.sales.reports.wizard'].create({'pos_session_id': session.id})
        self.assertEqual(wizard.employee_ids, cash_employee | invoice_employee)

        self.assertEqual(cash_report['employee_name'], cash_employee.name)
        self.assertEqual(cash_report['nbr_orders'], 1)
        self.assertEqual(cash_report['total_paid'], 10)
        self.assertEqual(cash_report['invoiceTotal'], 0)
        self.assertEqual([(payment['id'], payment['total']) for payment in cash_report['payments']], [(self.cash_pm1.id, 10)])

        self.assertEqual(invoice_report['employee_name'], invoice_employee.name)
        self.assertEqual(invoice_report['total_paid'], 20)
        # No session cash count row for an employee who took no cash
        self.assertEqual([(payment['id'], payment['total']) for payment in invoice_report['payments']], [(self.bank_pm1.id, 20)])
        self.assertEqual(invoice_report['invoiceTotal'], 20)
        self.assertEqual(invoice_report['invoiceList'], [{
            'name': session.name,
            'invoices': [{
                'total': invoiced_order.account_move.amount_total_signed,
                'name': invoiced_order.account_move.name,
                'order_ref': invoiced_order.pos_reference,
            }],
        }])
