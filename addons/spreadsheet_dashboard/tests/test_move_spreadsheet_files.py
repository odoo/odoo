from odoo.tests.common import TransactionCase


class TestMoveSpreadsheetFiles(TransactionCase):

    def test_move_spreadsheet_initial_file(self):
        group = self.env["spreadsheet.dashboard.group"].create(
            {"name": "a group"}
        )
        initial_data = b'{"version": 1, "sheets": [{"id": "sheet1", "name": "Sheet1"}]}'
        dashboard = self.env["spreadsheet.dashboard"].create(
            {
                "name": "a dashboard",
                "dashboard_group_id": group.id,
                "raw": initial_data
            }
        )
        attachment = self.env["ir.attachment"].search([
            ("res_model", "=", "spreadsheet.dashboard"),
            ("res_field", "=", "data"),
            ("res_id", "=", dashboard.id),
        ])
        self.assertFalse(attachment.db_datas)
        self.env["ir.attachment"]._move_spreadsheet_files_to_db()
        self.assertEqual(attachment.db_datas, attachment.raw)

        updated_data = b'{"version": 2, "sheets": [{"id": "sheet1", "name": "New sheet name"}]}'
        attachment.db_datas = updated_data
        self.assertEqual(attachment.raw, initial_data)
        self.env["ir.attachment"]._move_spreadsheet_files_to_current_storage()
        self.assertEqual(attachment.raw, updated_data)
        self.assertFalse(attachment.db_datas)
