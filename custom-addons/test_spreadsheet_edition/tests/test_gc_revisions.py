# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time
import json

from odoo.addons.spreadsheet_edition.tests.spreadsheet_test_case import (
    SpreadsheetTestCase,
)


class SpreadsheetRevisionTest(SpreadsheetTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].set_param(
            "spreadsheet_edition.gc_revisions_inactivity_in_days", 365
        )

    def test_delete_history_after_inactivity(self):
        with freeze_time("2018-01-01"):
            spreadsheet = self.env["spreadsheet.test"].create({})
            spreadsheet.dispatch_spreadsheet_message(
                self.new_revision_data(spreadsheet)
            )
            snapshot = {"revisionId": "next-revision"}
            self.snapshot(
                spreadsheet, spreadsheet.server_revision_id, "next-revision", snapshot
            )
            revisions = spreadsheet.with_context(
                active_test=False
            ).spreadsheet_revision_ids
            # write_date is not mocked when archiving, so we need to set it manually
            revisions.write_date = "2018-01-01"

        # 364 days later, the history is still there
        with freeze_time("2018-12-31"):
            self.env["spreadsheet.revision"]._gc_revisions()
            self.assertEqual(
                len(
                    spreadsheet.with_context(active_test=False).spreadsheet_revision_ids
                ),
                2,
            )

        # 365 days later, the history is gone
        with freeze_time("2019-01-01"):
            self.env["spreadsheet.revision"]._gc_revisions()
            self.assertFalse(
                spreadsheet.with_context(active_test=False).spreadsheet_revision_ids
            )
            self.assertEqual(json.loads(spreadsheet.spreadsheet_data), snapshot)

    def test_do_not_delete_active_revisions(self):
        with freeze_time("2018-01-01"):
            spreadsheet = self.env["spreadsheet.test"].create({})
            spreadsheet.dispatch_spreadsheet_message(
                self.new_revision_data(spreadsheet)
            )
            snapshot = {"revisionId": "next-revision"}
            self.snapshot(
                spreadsheet, spreadsheet.server_revision_id, "next-revision", snapshot
            )
            # revision after the snapshot
            spreadsheet.dispatch_spreadsheet_message(
                self.new_revision_data(spreadsheet)
            )
            revisions = spreadsheet.with_context(
                active_test=False
            ).spreadsheet_revision_ids
            # write_date is not mocked when archiving, so we need to set it manually
            revisions.write_date = "2018-01-01"

        with freeze_time("2019-01-01"):
            self.env["spreadsheet.revision"]._gc_revisions()
            self.assertEqual(json.loads(spreadsheet.spreadsheet_data), snapshot)
            self.assertEqual(
                len(
                    spreadsheet.with_context(active_test=False).spreadsheet_revision_ids
                ),
                1,
                "the active revision should not be deleted",
            )

    def test_do_not_delete_recently_renamed_revisions(self):
        with freeze_time("2018-01-01"):
            spreadsheet = self.env["spreadsheet.test"].create({})
            spreadsheet.dispatch_spreadsheet_message(
                self.new_revision_data(spreadsheet)
            )
            snapshot = {"revisionId": "next-revision"}
            self.snapshot(
                spreadsheet, spreadsheet.server_revision_id, "next-revision", snapshot
            )
            revisions = spreadsheet.with_context(
                active_test=False
            ).spreadsheet_revision_ids
            # write_date is not mocked when archiving, so we need to set it manually
            revisions.write_date = "2018-01-01"

        with freeze_time("2018-08-01"):
            revision = spreadsheet.with_context(
                active_test=False
            ).spreadsheet_revision_ids[0]
            revision.name = "renamed"
            revision.write_date = "2018-08-01"

        with freeze_time("2019-01-01"):
            self.env["spreadsheet.revision"]._gc_revisions()
            self.assertEqual(
                len(
                    spreadsheet.with_context(active_test=False).spreadsheet_revision_ids
                ),
                2,
                "the history should not be deleted",
            )
