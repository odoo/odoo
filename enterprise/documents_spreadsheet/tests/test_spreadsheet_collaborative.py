# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import base64

from .common import SpreadsheetTestCommon
from odoo.tests.common import new_test_user, tagged
from odoo.exceptions import AccessError


@tagged("collaborative_spreadsheet")
class SpreadsheetCollaborative(SpreadsheetTestCommon):
    def test_compute_revision_without_session(self):
        spreadsheet = self.create_spreadsheet()
        self.assertEqual(spreadsheet.current_revision_uuid, "START_REVISION")

    def test_compute_revision_with_session(self):
        spreadsheet = self.create_spreadsheet()
        spreadsheet.join_spreadsheet_session()
        commands = self.new_revision_data(spreadsheet)
        spreadsheet.dispatch_spreadsheet_message(commands)
        revision_data2 = self.new_revision_data(spreadsheet, nextRevisionId="nextone")
        spreadsheet.dispatch_spreadsheet_message(revision_data2)
        self.assertEqual(spreadsheet.current_revision_uuid, "nextone")

    def test_dispatch_new_revision(self):
        spreadsheet = self.create_spreadsheet()
        commands = self.new_revision_data(spreadsheet)
        spreadsheet.join_spreadsheet_session()
        spreadsheet.dispatch_spreadsheet_message(commands)
        self.assertEqual(
            len(spreadsheet.spreadsheet_revision_ids),
            1,
            "It should have recorded one revision",
        )
        self.assertEqual(
            spreadsheet.current_revision_uuid,
            commands["nextRevisionId"],
            "It should have updated its revision",
        )
        self.assertEqual(
            json.loads(spreadsheet.spreadsheet_revision_ids.commands),
            {"commands": commands["commands"], "id": spreadsheet.id, "type": commands["type"]},
            "It should have saved the revision data",
        )

    def test_dispatch_revision_concurrent_first_revision_id(self):
        spreadsheet = self.create_spreadsheet()
        spreadsheet.join_spreadsheet_session()
        start_revision = spreadsheet.current_revision_uuid
        revision1 = self.new_revision_data(spreadsheet, serverRevisionId=start_revision)
        spreadsheet.dispatch_spreadsheet_message(revision1)
        self.assertEqual(
            len(spreadsheet.spreadsheet_revision_ids),
            1,
            "It should have recorded the revision",
        )
        revision2 = self.new_revision_data(spreadsheet, serverRevisionId=start_revision)
        spreadsheet.dispatch_spreadsheet_message(revision2)
        self.assertEqual(
            len(spreadsheet.spreadsheet_revision_ids),
            1,
            "It should not have recorded the revision",
        )
        self.assertEqual(
            spreadsheet.current_revision_uuid,
            revision1["nextRevisionId"],
            "The revision should not have been updated",
        )

    def test_join_spreadsheet_session(self):
        spreadsheet = self.create_spreadsheet()
        data = spreadsheet.join_spreadsheet_session()
        self.assertEqual(data["data"], {})
        self.assertEqual(data["revisions"], [], "It should not have past revisions")

    def test_join_active_spreadsheet_session(self):
        spreadsheet = self.create_spreadsheet()
        commands = self.new_revision_data(spreadsheet)
        spreadsheet.join_spreadsheet_session()
        spreadsheet.dispatch_spreadsheet_message(commands)
        spreadsheet = spreadsheet.join_spreadsheet_session()
        del commands["clientId"]
        self.assertEqual(spreadsheet["data"], {})
        self.assertEqual(spreadsheet["revisions"], [commands], "It should have past revisions")

    def test_snapshot_spreadsheet_save_data(self):
        spreadsheet = self.create_spreadsheet()
        spreadsheet.dispatch_spreadsheet_message(self.new_revision_data(spreadsheet))
        self.assertEqual(
            len(spreadsheet.spreadsheet_revision_ids), 1, "It should have 1 revision"
        )
        is_accepted = self.snapshot(
            spreadsheet,
            spreadsheet.current_revision_uuid, "snapshot-revision-id", {"sheets": [], "revisionId": "snapshot-revision-id"},
        )
        self.assertTrue(is_accepted, "It should have accepted the snapshot")
        self.assertEqual(
            len(spreadsheet.spreadsheet_revision_ids),
            0,
            "It should have archived the revision history",
        )
        snapshot_revision = spreadsheet.with_context(active_test=False).spreadsheet_revision_ids[-1]
        self.assertEqual(
            json.loads(snapshot_revision.commands),
            {"type": "SNAPSHOT_CREATED", "version": 1},
            "It should have saved a snapshot revision"
        )
        self.assertEqual(base64.decodebytes(spreadsheet.spreadsheet_snapshot), b'{"sheets": [], "revisionId": "snapshot-revision-id"}', "It should have saved the data")
        self.assertEqual(
            spreadsheet.current_revision_uuid,
            "snapshot-revision-id",
            "It should have updated the snapshot revision"
        )

    def test_snapshot_inconsistent_revision_id(self):
        spreadsheet = self.create_spreadsheet()
        with self.assertRaises(ValueError):
            self.snapshot(
                spreadsheet,
                spreadsheet.current_revision_uuid, "snapshot-revision-id", {"sheets": [], "revisionId": "another-revision-id"},
            )


    def test_snapshot_spreadsheet_with_invalid_revision(self):
        spreadsheet = self.create_spreadsheet()
        spreadsheet.join_spreadsheet_session()
        first_revision = spreadsheet.current_revision_uuid
        spreadsheet.dispatch_spreadsheet_message(self.new_revision_data(spreadsheet))
        current_data = spreadsheet.spreadsheet_snapshot
        current_revision = spreadsheet.current_revision_uuid
        self.assertEqual(
            len(spreadsheet.spreadsheet_revision_ids), 1, "It should have 1 revision"
        )
        is_accepted = self.snapshot(spreadsheet, first_revision, "snapshot-revision-id", {"revisionId": "snapshot-revision-id"})
        self.assertFalse(is_accepted, "It should not have accepted the snapshot")
        self.assertEqual(spreadsheet.spreadsheet_snapshot, current_data, "It should not have saved the data")
        self.assertEqual(
            current_revision,
            spreadsheet.current_revision_uuid,
            "The revision should not have been updated",
        )

    def test_unlink_revisions(self):
        spreadsheet = self.create_spreadsheet()
        spreadsheet.dispatch_spreadsheet_message(
            self.new_revision_data(spreadsheet)
        )
        ids = spreadsheet.spreadsheet_revision_ids.ids
        spreadsheet.unlink()
        self.assertFalse(self.env["spreadsheet.revision"].browse(ids).exists())

    def test_unlink_archived_revisions(self):
        spreadsheet = self.create_spreadsheet()
        spreadsheet.dispatch_spreadsheet_message(
            self.new_revision_data(spreadsheet)
        )
        self.snapshot(
            spreadsheet,
            spreadsheet.current_revision_uuid, "snapshot-id", {"revisionId": "snapshot-id"},
        )
        revisions = spreadsheet.with_context(active_test=False).spreadsheet_revision_ids
        self.assertTrue(revisions)
        self.assertFalse(any(revisions.mapped('active')))
        spreadsheet.unlink()
        self.assertFalse(revisions.exists())


@tagged("collaborative_spreadsheet")
class SpreadsheetORMAccess(SpreadsheetTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.folder.access_internal = 'none'
        cls.user = new_test_user(cls.env, login="John", groups="base.group_user")
        cls.admin = new_test_user(cls.env, login="John's manager", groups="base.group_system")
        cls.spreadsheet = cls.env["documents.document"].create(
            {
                "spreadsheet_data": b"{}",
                "folder_id": cls.folder.id,
                "handler": "spreadsheet",
                "mimetype": "application/o-spreadsheet",
                "access_internal": "none",
            }
        )
        cls.env['documents.access'].create({'document_id': cls.spreadsheet.id, 'partner_id': cls.admin.partner_id.id, 'role': 'edit'})
        cls.spreadsheet.join_spreadsheet_session()

    def test_create_user(self):
        with self.assertRaises(AccessError):
            self.env["spreadsheet.revision"].with_user(self.user).create(
                {
                    "commands": self.new_revision_data(self.spreadsheet),
                    "document_id": self.spreadsheet.id,
                    "revision_uuid": "a revision id",
                }
            )

    def test_create_user_with_doc_access(self):
        # the user can write the document
        self._give_user_access('edit')
        with self.assertRaises(AccessError):
            self.env["spreadsheet.revision"].with_user(self.user).create(
                {
                    "commands": self.new_revision_data(self.spreadsheet),
                    "res_id": self.spreadsheet.id,
                    "res_model": "documents.document",
                    "revision_uuid": "a revision id",
                }
            )

    def test_create_manager(self):
        revision = (
            self.env["spreadsheet.revision"]
            .with_user(self.admin)
            .create(
                {
                    "commands": self.new_revision_data(self.spreadsheet),
                    "res_id": self.spreadsheet.id,
                    "res_model": "documents.document",
                    "revision_uuid": "a revision id",
                }
            )
        )
        self.assertTrue(revision)

    def _give_user_access(self, role='view'):
        self.env['documents.access'].create({
            'document_id': self.spreadsheet.id,
            'partner_id': self.user.partner_id.id,
            'role': role,
        })

    def test_read_user(self):
        with self.assertRaises(AccessError):
            self.spreadsheet.with_user(self.user).spreadsheet_revision_ids.read()
        with self.assertRaises(AccessError):
            self.env["spreadsheet.revision"].with_user(self.user).search([])

    def test_read_user_with_doc_access(self):
        with self.assertRaises(AccessError):
            self.spreadsheet.with_user(self.user).read()
        self._give_user_access()
        self.spreadsheet.with_user(self.user).read()  # the user can read the document
        with self.assertRaises(AccessError):
            self.spreadsheet.with_user(self.user).spreadsheet_revision_ids.read()
        with self.assertRaises(AccessError):
            self.env["spreadsheet.revision"].with_user(self.user).search([])

    def test_read_manager(self):
        self.spreadsheet.dispatch_spreadsheet_message(
            self.new_revision_data(self.spreadsheet)
        )
        self.env.invalidate_all()
        revision = self.env["spreadsheet.revision"].with_user(self.admin).search([])
        self.assertTrue(revision)
        self.assertTrue(revision.read())

    def test_write_user(self):
        with self.assertRaises(AccessError):
            self.spreadsheet.with_user(self.user).spreadsheet_revision_ids.write({})

    def test_write_user_with_doc_access(self):
        self._give_user_access('edit')
        self.env.invalidate_all()
        self.spreadsheet.with_user(self.user).write(
            {"name": "new name"}
        )  # the user can write the document
        with self.assertRaises(AccessError):
            self.spreadsheet.with_user(self.user).spreadsheet_revision_ids.write({})

    def test_write_manager(self):
        self.spreadsheet.dispatch_spreadsheet_message(
            self.new_revision_data(self.spreadsheet)
        )
        self.env.invalidate_all()
        self.spreadsheet.with_user(self.admin).spreadsheet_revision_ids.write(
            {"commands": "coucou"}
        )
        self.assertEqual(self.spreadsheet.spreadsheet_revision_ids.commands, "coucou")

    def test_unlink_user(self):
        with self.assertRaises(AccessError):
            self.spreadsheet.with_user(self.user).spreadsheet_revision_ids.unlink()

    def test_unlink_user_with_doc_access(self):
        self._give_user_access()
        with self.assertRaises(AccessError):
            self.spreadsheet.with_user(self.user).spreadsheet_revision_ids.unlink()

    def test_unlink_manager(self):
        self.spreadsheet.dispatch_spreadsheet_message(
            self.new_revision_data(self.spreadsheet)
        )
        self.assertTrue(self.spreadsheet.spreadsheet_revision_ids)
        self.env.invalidate_all()
        self.spreadsheet.with_user(self.admin).spreadsheet_revision_ids.unlink()
        self.assertFalse(self.spreadsheet.spreadsheet_revision_ids)

    def test_join_user(self):
        with self.assertRaises(AccessError):
            self.spreadsheet.with_user(self.user).join_spreadsheet_session()

    def test_join_user_with_doc_access(self):
        self._give_user_access()
        self.env.invalidate_all()
        self.spreadsheet.with_user(self.user).join_spreadsheet_session()

    def test_join_user_with_read_doc_access(self):
        self.spreadsheet.access_internal = 'view'

        self.env.invalidate_all()
        self.spreadsheet.with_user(self.user).join_spreadsheet_session()
        with self.assertRaises(AccessError):
            self.spreadsheet.with_user(self.user).dispatch_spreadsheet_message(
                self.new_revision_data(self.spreadsheet)
            )

    def test_join_portal_user_with_doc_access(self):
        portal_user = new_test_user(self.env, login="Raoul", groups="base.group_portal")

        self.env['documents.access'].create({
            'document_id': self.spreadsheet.id,
            'partner_id': portal_user.partner_id.id,
            'role': 'view',
        })

        # can read
        self.spreadsheet.with_user(portal_user).join_spreadsheet_session()

        # can't write
        with self.assertRaises(AccessError):
            self.spreadsheet.with_user(portal_user).dispatch_spreadsheet_message(
                self.new_revision_data(self.spreadsheet)
            )

    def test_join_new_spreadsheet_user(self):
        # only read access
        self.spreadsheet.access_internal = 'view'
        spreadsheet = self.env["documents.document"].create(
            {
                "spreadsheet_data": b"{}",
                "folder_id": self.folder.id,
                "handler": "spreadsheet",
                "mimetype": "application/o-spreadsheet",
                "access_internal": "edit",
            }
        )
        # no one ever joined this spreadsheet
        result = spreadsheet.with_user(self.user).join_spreadsheet_session()
        self.assertEqual(result["data"], {})

    def test_join_snapshot_request(self):
        with self._freeze_time("2020-02-02 18:00"):
            self.spreadsheet.dispatch_spreadsheet_message(
                self.new_revision_data(self.spreadsheet)
            )
        self.spreadsheet.access_internal = 'view'
        with self._freeze_time("2020-02-03 18:00"):
            self.assertFalse(
                self.spreadsheet.with_user(self.user).join_spreadsheet_session().get("snapshot_requested"),
                "It should not have requested a snapshot",
            )
            self.spreadsheet.access_internal = 'edit'
            self.folder.access_internal = 'edit'
            self.assertTrue(self.spreadsheet._should_be_snapshotted())
            self.assertTrue(
                self.spreadsheet.with_user(self.user).join_spreadsheet_session().get("snapshot_requested"),
                "It should have requested a snapshot",
            )

    def test_snapshot_user(self):
        with self.assertRaises(AccessError):
            self.snapshot(
                self.spreadsheet.with_user(self.user),
                self.spreadsheet.current_revision_uuid, "snapshot-id", {"revisionId": "snapshot-id"},
            )

    def test_snapshot_user_with_doc_access(self):
        self._give_user_access('edit')
        self.spreadsheet.dispatch_spreadsheet_message(
            # add at least one revision
            self.new_revision_data(self.spreadsheet)
        )
        self.env.invalidate_all()
        self.snapshot(
            self.spreadsheet.with_user(self.user),
            self.spreadsheet.current_revision_uuid, "snapshot-id", {"revisionId": "snapshot-id"},
        )
        self.assertEqual(len(self.spreadsheet.spreadsheet_revision_ids), 0)

    def test_snapshot_user_with_read_doc_access(self):
        self._give_user_access()
        self.spreadsheet.current_revision_uuid
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            self.snapshot(
                self.spreadsheet.with_user(self.user),
                self.spreadsheet.current_revision_uuid, "snapshot-id", "{}"
            )

    def test_dispatch_user(self):
        with self.assertRaises(AccessError):
            self.spreadsheet.with_user(self.user).dispatch_spreadsheet_message(
                self.new_revision_data(self.spreadsheet)
            )

    def test_dispatch_user_with_doc_access(self):
        self._give_user_access('edit')
        commands = self.new_revision_data(self.spreadsheet)
        self.env.invalidate_all()
        self.spreadsheet.with_user(self.user).dispatch_spreadsheet_message(commands)
        self.assertEqual(
            json.loads(self.spreadsheet.spreadsheet_revision_ids.commands),
            {"commands": commands["commands"], "id": self.spreadsheet.id, "type": commands["type"]},
        )

    def test_dispatch_user_with_read_doc_access(self):
        self._give_user_access()
        commands = self.new_revision_data(self.spreadsheet)
        with self.assertRaises(AccessError):
            self.spreadsheet.with_user(self.user).dispatch_spreadsheet_message(
                commands
            )

    def test_dispatch_user_with_read_doc_access_move(self):
        self._give_user_access()
        self.env.invalidate_all()
        self.spreadsheet.with_user(self.user).dispatch_spreadsheet_message(
            {"type": "CLIENT_MOVED"}
        )
