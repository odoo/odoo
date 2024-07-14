# Part of Odoo. See LICENSE file for full copyright and licensing details.


from .common import SpreadsheetTestCommon
from odoo.exceptions import AccessError
from odoo.tests.common import new_test_user

EXCEL_FILES = [
    {
        "content": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
        "path": "[Content_Types].xml",
    }
]


class SpreadsheetSharing(SpreadsheetTestCommon):
    def test_share_url(self):
        document = self.create_spreadsheet()
        share_vals = {
            "document_ids": [(6, 0, [document.id])],
            "folder_id": document.folder_id.id,
            "type": "ids",
            "spreadsheet_shares": [
            {
                "spreadsheet_data": document.spreadsheet_data,
                "document_id": document.id,
                "excel_files": EXCEL_FILES,
            }
        ]
        }
        url = self.env["documents.share"].action_get_share_url(share_vals)
        share = self.env["documents.share"].search(
            [("document_ids", "in", document.id)]
        )
        self.assertEqual(url, share.full_url)
        spreadsheet_share = share.freezed_spreadsheet_ids
        self.assertEqual(len(spreadsheet_share), 1)
        self.assertEqual(spreadsheet_share.document_id, document)
        self.assertTrue(spreadsheet_share.excel_export)

    def test_two_spreadsheets_share_url(self):
        document1 = self.create_spreadsheet()
        document2 = self.create_spreadsheet()
        documents = document1 | document2
        share_vals = {
            "document_ids": [(6, 0, documents.ids)],
            "folder_id": document1.folder_id.id,
            "type": "ids",
            "spreadsheet_shares": [
            {
                "spreadsheet_data": document1.spreadsheet_data,
                "document_id": document1.id,
                "excel_files": EXCEL_FILES,
            },
            {
                "spreadsheet_data": document2.spreadsheet_data,
                "document_id": document2.id,
                "excel_files": EXCEL_FILES,
            },
        ]
        }
        url = self.env["documents.share"].action_get_share_url(share_vals)
        share = self.env["documents.share"].search(
            [("document_ids", "in", documents.ids)]
        )
        self.assertEqual(url, share.full_url)
        spreadsheet_shares = share.freezed_spreadsheet_ids
        self.assertEqual(len(spreadsheet_shares), 2)

    def test_share_popup(self):
        document = self.create_spreadsheet()
        share_vals = {
            "document_ids": [(6, 0, [document.id])],
            "folder_id": document.folder_id.id,
            "type": "ids",
            "spreadsheet_shares": [
                {
                    "spreadsheet_data": document.spreadsheet_data,
                    "document_id": document.id,
                    "excel_files": EXCEL_FILES,
                }
            ]
        }
        action = self.env["documents.share"].open_share_popup(share_vals)
        share = self.env["documents.share"].search(
            [("document_ids", "in", document.id)]
        )
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_id"], share.id)
        self.assertEqual(action["res_model"], "documents.share")
        spreadsheet_share = share.freezed_spreadsheet_ids
        self.assertEqual(len(spreadsheet_share), 1)
        self.assertEqual(spreadsheet_share.document_id, document)
        self.assertTrue(spreadsheet_share.excel_export)

    def test_can_create_own(self):
        document = self.create_spreadsheet()
        with self.with_user(self.spreadsheet_user.login):
            share = self.share_spreadsheet(document)

        shared_spreadsheet = share.freezed_spreadsheet_ids
        self.assertTrue(shared_spreadsheet)
        self.assertTrue(shared_spreadsheet.create_uid, self.spreadsheet_user)

    def test_cannot_read_others(self):
        document = self.create_spreadsheet()
        share = self.share_spreadsheet(document)
        shared_spreadsheet = share.freezed_spreadsheet_ids
        with self.assertRaises(AccessError):
            shared_spreadsheet.with_user(self.spreadsheet_user).spreadsheet_data

    def test_collaborative_spreadsheet_with_token(self):
        document = self.create_spreadsheet()
        share = self.share_spreadsheet(document)
        raoul = new_test_user(self.env, login="raoul")
        document.folder_id.group_ids = self.env.ref("documents.group_documents_user")
        document = document.with_user(raoul)
        with self.with_user("raoul"):
            # join without token
            with self.assertRaises(AccessError):
                document.join_spreadsheet_session()

            # join with wrong token
            with self.assertRaises(AccessError):
                document.join_spreadsheet_session(share.id, "a wrong token")

            # join with token
            token = share.access_token
            data = document.join_spreadsheet_session(share.id, token)
            self.assertTrue(data)
            self.assertEqual(data["isReadonly"], False)

            revision = self.new_revision_data(document)

            # dispatch revision without token
            with self.assertRaises(AccessError):
                document.dispatch_spreadsheet_message(revision)

            # dispatch revision with wrong token
            with self.assertRaises(AccessError):
                document.dispatch_spreadsheet_message(
                    revision, share.id, "a wrong token"
                )

            # dispatch revision with token
            token = share.access_token
            accepted = document.dispatch_spreadsheet_message(revision, share.id, token)
            self.assertEqual(accepted, True)

            # snapshot without token
            snapshot_revision = {
                "type": "SNAPSHOT",
                "serverRevisionId": document.sudo().server_revision_id,
                "nextRevisionId": "snapshot-revision-id",
                "data": {"revisionId": "snapshot-revision-id"},
            }
            with self.assertRaises(AccessError):
                document.dispatch_spreadsheet_message(snapshot_revision)

            # snapshot with wrong token
            snapshot_revision = {
                "type": "SNAPSHOT",
                "serverRevisionId": document.sudo().server_revision_id,
                "nextRevisionId": "snapshot-revision-id",
                "data": {"revisionId": "snapshot-revision-id"},
            }
            with self.assertRaises(AccessError):
                document.dispatch_spreadsheet_message(
                    snapshot_revision, share.id, "a wrong token"
                )

            # snapshot with token
            snapshot_revision = {
                "type": "SNAPSHOT",
                "serverRevisionId": document.sudo().server_revision_id,
                "nextRevisionId": "snapshot-revision-id",
                "data": {"revisionId": "snapshot-revision-id"},
            }
            accepted = document.dispatch_spreadsheet_message(
                snapshot_revision, share.id, token
            )
            self.assertEqual(accepted, True)

    def test_collaborative_readonly_spreadsheet_with_token(self):
        """Readonly access"""
        document = self.create_spreadsheet()
        document.folder_id.group_ids = self.env.ref("base.group_system")
        document.folder_id.read_group_ids = self.env.ref(
            "documents.group_documents_user"
        )
        with self.with_user(self.spreadsheet_user.login):
            share = self.share_spreadsheet(document)

        user = new_test_user(self.env, login="raoul")
        document = document.with_user(user)
        with self.with_user("raoul"):
            # join without token
            with self.assertRaises(AccessError):
                document.join_spreadsheet_session()

            # join with token
            data = document.join_spreadsheet_session(share.id, share.access_token)
            self.assertEqual(data["isReadonly"], True)

            revision = self.new_revision_data(document)
            # dispatch revision without token
            with self.assertRaises(AccessError):
                document.dispatch_spreadsheet_message(revision)

            # dispatch revision with wrong token
            with self.assertRaises(AccessError):
                document.dispatch_spreadsheet_message(
                    revision, share.id, "a wrong token"
                )

            # dispatch revision with right token but no write access
            with self.assertRaises(AccessError):
                token = share.access_token
                document.dispatch_spreadsheet_message(revision, share.id, token)

            # snapshot without token
            snapshot_revision = {
                "type": "SNAPSHOT",
                "serverRevisionId": document.sudo().server_revision_id,
                "nextRevisionId": "snapshot-revision-id",
                "data": r"{}",
            }
            with self.assertRaises(AccessError):
                document.dispatch_spreadsheet_message(snapshot_revision)

            # snapshot with token
            snapshot_revision = {
                "type": "SNAPSHOT",
                "serverRevisionId": document.sudo().server_revision_id,
                "nextRevisionId": "snapshot-revision-id",
                "data": r"{}",
            }
            with self.assertRaises(AccessError):
                document.dispatch_spreadsheet_message(
                    snapshot_revision, share.id, token
                )

    def test_spreadsheet_with_token_from_workspace_share(self):
        document_1 = self.create_spreadsheet()
        self.create_spreadsheet()
        folder = document_1.folder_id
        self.assertEqual(len(folder.document_ids), 2, "there are more than one document in the folder")
        share = self.env["documents.share"].create(
            {
                "folder_id": folder.id,
                "domain": [("folder_id", "child_of", folder.id)],
                "type": "domain",
            }
        )
        self.env["documents.shared.spreadsheet"].create(
            {
                "share_id": share.id,
                "document_id": document_1.id,
                "spreadsheet_data": document_1.spreadsheet_data,
            }
        )
        result = document_1.join_spreadsheet_session(share.id, share.access_token)
        self.assertTrue(result, "it should grant access")
