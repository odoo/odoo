from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAccountMoveImportTemplate(TransactionCase):

    def setUp(self):
        super().setUp()
        self.AccountMove = self.env['account.move']

    def fetch_template_for_type(self, move_type):
        return self.AccountMove.with_context(default_move_type=move_type).get_import_templates()

    def test_import_template(self):

        def test_template(move_type, file_name):
            template = self.fetch_template_for_type(move_type)
            self.assertEqual(len(template), 1)
            self.assertEqual(template[0].get('template'), file_name)

        test_template('entry', '/account/static/xls/misc_operations_import_template.xlsx')
        test_template('out_invoice', '/account/static/xls/customer_invoices_credit_notes_import_template.xlsx')
        test_template('out_refund', '/account/static/xls/customer_invoices_credit_notes_import_template.xlsx')
        test_template('in_invoice', '/account/static/xls/vendor_bills_refunds_import_template.xlsx')
        test_template('in_refund', '/account/static/xls/vendor_bills_refunds_import_template.xlsx')

        template = self.fetch_template_for_type('unknown_type')
        self.assertEqual(template, [])
        template = self.fetch_template_for_type(None)
        self.assertEqual(template, [])
