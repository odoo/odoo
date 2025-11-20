import csv
import io
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestExpenseImport(TransactionCase):

    def test_import_expense_with_no_price_unit(self):
        """ Test importing expenses from a CSV file using base_import """

        output = io.StringIO()
        writer = csv.writer(output, quoting=1)
        writer.writerow(['__export__.hr_expense_22_431eb43b', 'Mitchell Admin', 'Test Expense', '2025-10-23', 'Meals', 'Employee (to reimburse)', '', '', '160.00', 'account.1_purchase_tax_template', ''])

        import_wizard = self.env['base_import.import'].create({
            'res_model': 'hr.expense',
            'file': output.getvalue().encode(),
            'file_name': 'test_expenses.csv',
            'file_type': 'text/csv',
        })

        options = {
            'separator': ',',
            'quoting': '"',
            'date_format': '',
            'headers': False,
        }

        # This maps the CSV column index to field technical name
        fields = ['id', 'employee_id', 'name', 'date', 'product_id', 'payment_mode', 'activity_ids', 'analytic_distribution', 'total_amount_currency', 'tax_ids/id', '']
        columns = []

        with mute_logger('odoo.addons.base_import.models.base_import'):
            result = import_wizard.execute_import(
                fields=fields,
                columns=columns,
                options=options
            )

        # Check that there were no error messages in the result
        self.assertFalse(result.get('messages'), "Import failed with messages: %s" % result.get('messages'))

        # Fetch the created expense
        expense = self.env['hr.expense'].search([('name', '=', 'Test Expense')], limit=1)
        self.assertTrue(expense, "Expense record should be created")

        self.assertEqual(expense.total_amount, 160.0, "Total amount should match the imported value")

        # Tax is 15% (included in total amount)
        # Tax amount should 160 - (160/1.15) = 20.87
        self.assertAlmostEqual(expense.tax_amount, 20.87, places=2, msg="Tax amount should be calculated from the total (included)")
