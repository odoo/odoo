from odoo.tests.common import TransactionCase, new_test_user

class TestDocumentsDocument(TransactionCase):
    def test_can_add_to_dashboard_admin(self):
        admin = new_test_user(
            self.env, "Test user",
            groups="spreadsheet_dashboard.group_dashboard_manager,documents.group_documents_user"
        )
        document = self.env["documents.document"].with_user(admin).create(
            {
                "name": "a document",
                "spreadsheet_data": r'{"sheets": []}',
                "handler": "spreadsheet",
                "mimetype": "application/o-spreadsheet",
            }
        )
        data = document.with_user(admin).join_spreadsheet_session()
        self.assertTrue(data['can_add_to_dashboard'])

    def test_can_add_to_dashboard_non_admin(self):
        user = new_test_user(
            self.env, "Test user", groups="base.group_user,documents.group_documents_user"
        )
        document = self.env["documents.document"].with_user(user).create(
            {
                "name": "a document",
                "spreadsheet_data": r'{"sheets": []}',
                "handler": "spreadsheet",
                "mimetype": "application/o-spreadsheet",
            }
        )
        data = document.with_user(user).join_spreadsheet_session()
        self.assertFalse(data['can_add_to_dashboard'])
