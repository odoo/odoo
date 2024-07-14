# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests.common import new_test_user
from odoo.addons.spreadsheet_edition.tests.spreadsheet_test_case import SpreadsheetTestCase


class SpreadsheetMixinTest(SpreadsheetTestCase):


    def test_copy_revisions(self):
        spreadsheet = self.env["spreadsheet.test"].create({})
        spreadsheet.dispatch_spreadsheet_message(self.new_revision_data(spreadsheet))
        copy = spreadsheet.copy()
        self.assertEqual(
            copy.spreadsheet_revision_ids.commands,
            spreadsheet.spreadsheet_revision_ids.commands,
        )

    def test_dont_copy_revisions_if_provided(self):
        spreadsheet = self.env["spreadsheet.test"].create({})
        spreadsheet.dispatch_spreadsheet_message(self.new_revision_data(spreadsheet))
        copy = spreadsheet.copy({"spreadsheet_revision_ids": []})
        self.assertFalse(copy.spreadsheet_revision_ids)

    def test_reset_spreadsheet_data(self):
        spreadsheet = self.env["spreadsheet.test"].create({})
        # one revision before the snapshot (it's archived by the snapshot)
        spreadsheet.dispatch_spreadsheet_message(self.new_revision_data(spreadsheet))
        self.snapshot(
            spreadsheet,
            spreadsheet.server_revision_id, "snapshot-revision-id", {"sheets": [], "revisionId": "snapshot-revision-id"},
        )
        # one revision after the snapshot
        spreadsheet.dispatch_spreadsheet_message(self.new_revision_data(spreadsheet))
        spreadsheet.spreadsheet_data = r"{}"
        self.assertFalse(spreadsheet.spreadsheet_snapshot)
        self.assertFalse(
            spreadsheet.with_context(active_test=True).spreadsheet_revision_ids,
        )

    def test_save_spreadsheet_snapshot(self):
        spreadsheet = self.env["spreadsheet.test"].create({})
        server_revision_id = spreadsheet.server_revision_id
        snapshot = {"sheets": [], "revisionId": spreadsheet.server_revision_id}
        spreadsheet.save_spreadsheet_snapshot(snapshot)
        self.assertNotEqual(spreadsheet.server_revision_id, server_revision_id)
        self.assertEqual(
            spreadsheet._get_spreadsheet_snapshot(),
            dict(snapshot, revisionId=spreadsheet.server_revision_id),
        )

    def test_save_spreadsheet_snapshot_with_invalid_revision_id(self):
        spreadsheet = self.env["spreadsheet.test"].create({})
        snapshot = {"sheets": [], "revisionId": spreadsheet.server_revision_id}

        # one revision is saved in the meantime (concurrently)
        spreadsheet.dispatch_spreadsheet_message(self.new_revision_data(spreadsheet))

        with self.assertRaises(UserError):
            spreadsheet.save_spreadsheet_snapshot(snapshot)

    def test_company_currency(self):
        spreadsheet = self.env["spreadsheet.test"].create({})
        company_eur = self.env["res.company"].create({"currency_id": self.env.ref("base.EUR").id, "name": "EUR"})
        company_gbp = self.env["res.company"].create({"currency_id": self.env.ref("base.GBP").id, "name": "GBP"})

        data = spreadsheet.with_company(company_eur).join_spreadsheet_session()
        self.assertEqual(data["default_currency"]["code"], "EUR")
        self.assertEqual(data["default_currency"]["symbol"], "€")

        data = spreadsheet.with_company(company_gbp).join_spreadsheet_session()
        self.assertEqual(data["default_currency"]["code"], "GBP")
        self.assertEqual(data["default_currency"]["symbol"], "£")

    def test_fork_history(self):
        spreadsheet = self.env["spreadsheet.test"].create({})
        spreadsheet.dispatch_spreadsheet_message(self.new_revision_data(spreadsheet))
        rev1 = spreadsheet.spreadsheet_revision_ids[0]
        action = spreadsheet.fork_history(rev1.id, {"test": "snapshot"})
        self.assertTrue(isinstance(action, dict))

        self.assertEqual(action["params"]["message"], "test spreadsheet created")
        self.assertEqual(action["tag"], "display_notification")
        self.assertEqual(action["type"], "ir.actions.client")

        next_action = action["params"]["next"]

        self.assertTrue(isinstance(next_action, dict))
        copy_id = next_action["params"]["spreadsheet_id"]
        spreadsheet_copy = self.env["spreadsheet.test"].browse(copy_id)
        self.assertTrue(spreadsheet_copy.exists())
        fork_revision = spreadsheet_copy.with_context(active_test=False).spreadsheet_revision_ids
        self.assertEqual(len(fork_revision), 1)
        self.assertEqual(fork_revision.commands, rev1.commands)
        self.assertEqual(fork_revision.active, False)

    def test_fork_history_before_snapshot(self):
        spreadsheet = self.env["spreadsheet.test"].create({})
        spreadsheet.dispatch_spreadsheet_message(self.new_revision_data(spreadsheet))
        self.snapshot(
            spreadsheet,
            spreadsheet.server_revision_id,
            "snapshot-revision-id",
             {"sheets": [], "revisionId": "snapshot-revision-id"}
        )
        spreadsheet.dispatch_spreadsheet_message(self.new_revision_data(spreadsheet))
        rev1 = spreadsheet.with_context(active_test=False).spreadsheet_revision_ids[0]
        fork_snapshot = {"test": "snapshot"}
        action = spreadsheet.fork_history(rev1.id, fork_snapshot)
        fork_id = action["params"]["next"]["params"]["spreadsheet_id"]
        spreadsheet_fork = self.env["spreadsheet.test"].browse(fork_id)
        self.assertEqual(spreadsheet_fork._get_spreadsheet_snapshot(), fork_snapshot)
        self.assertEqual(
            spreadsheet_fork.with_context(active_test=False).spreadsheet_revision_ids.active,
            False
        )

    def test_rename_revision(self):
        spreadsheet = self.env["spreadsheet.test"].create({})
        spreadsheet.dispatch_spreadsheet_message(self.new_revision_data(spreadsheet))
        revision = spreadsheet.spreadsheet_revision_ids[0]
        self.assertEqual(revision.name, False)

        spreadsheet.rename_revision(revision.id, "new revision name")
        self.assertEqual(revision.name, "new revision name")

    def test_get_spreadsheet_history(self):
        with freeze_time("2020-02-02"):
            spreadsheet = self.env["spreadsheet.test"].create({})
            spreadsheet.dispatch_spreadsheet_message(self.new_revision_data(spreadsheet))
            self.snapshot(
                spreadsheet,
                spreadsheet.server_revision_id, "snapshot-revision-id", {"sheets": [], "revisionId": "snapshot-revision-id"},
            )
            spreadsheet.dispatch_spreadsheet_message(self.new_revision_data(spreadsheet))
        user = spreadsheet.create_uid
        data = spreadsheet.get_spreadsheet_history()
        revisions = data["revisions"]
        self.assertEqual(len(revisions), 3)
        for revision in revisions:
            self.assertEqual(revision["timestamp"], datetime(2020, 2, 2, 0, 0, 0))
            self.assertEqual(revision["user"], (user.id, user.name))

        # from snapshot
        data = spreadsheet.get_spreadsheet_history(True)
        revisions = data["revisions"]
        self.assertEqual(len(revisions), 1)
        self.assertEqual(revisions[0]["timestamp"], datetime(2020, 2, 2, 0, 0, 0))
        self.assertEqual(revisions[0]["user"], (user.id, user.name))

    def test_get_spreadsheet_base_user_access_right_history(self):
        user = new_test_user(self.env, login="test", groups="base.group_user")
        spreadsheet = self.env["spreadsheet.test"].create({})
        spreadsheet.dispatch_spreadsheet_message(self.new_revision_data(spreadsheet))
        spreadsheet.invalidate_recordset()
        data = spreadsheet.with_user(user).get_spreadsheet_history()
        self.assertEqual(len(data["revisions"]), 1)

    def test_empty_spreadsheet_server_revision_id(self):
        spreadsheet = self.env["spreadsheet.test"].create({})
        self.assertEqual(spreadsheet.server_revision_id, "START_REVISION")

    def test_no_data_server_revision_id(self):
        spreadsheet = self.env["spreadsheet.test"].create({})
        spreadsheet.spreadsheet_snapshot = False
        spreadsheet.spreadsheet_data = False
        self.assertEqual(spreadsheet.server_revision_id, False)

    def test_last_revision_is_server_revision_id(self):
        spreadsheet = self.env["spreadsheet.test"].create({})

        revision_data = self.new_revision_data(spreadsheet)
        next_revision_id = revision_data["nextRevisionId"]
        spreadsheet.dispatch_spreadsheet_message(revision_data)
        self.assertEqual(spreadsheet.server_revision_id, next_revision_id)

        # dispatch new revision on top
        revision_data = self.new_revision_data(spreadsheet)
        next_revision_id = revision_data["nextRevisionId"]
        spreadsheet.dispatch_spreadsheet_message(revision_data)
        self.assertEqual(spreadsheet.server_revision_id, next_revision_id)

    def test_snapshotted_server_revision_id(self):
        spreadsheet = self.env["spreadsheet.test"].create({})
        snapshot_revision_id = "snapshot-id"
        self.snapshot(
            spreadsheet,
            spreadsheet.server_revision_id,
            snapshot_revision_id,
            {"revisionId": snapshot_revision_id},
        )
        self.assertEqual(spreadsheet.server_revision_id, snapshot_revision_id)

        # dispatch revision after snapshot
        revision_data = self.new_revision_data(spreadsheet)
        next_revision_id = revision_data["nextRevisionId"]
        spreadsheet.dispatch_spreadsheet_message(revision_data)
        self.assertEqual(spreadsheet.server_revision_id, next_revision_id)
