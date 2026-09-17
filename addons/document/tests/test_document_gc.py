import base64
import io
from unittest.mock import patch

from dateutil.relativedelta import relativedelta
from PIL import Image

from odoo import fields
from odoo.tests.common import TransactionCase, tagged

from .test_document_common import TEXT, TransactionCaseDocuments
from odoo.addons.base.models.ir_cron import IrCron


def _png(color):
    buffer = io.BytesIO()
    Image.new("RGB", (400, 300), color).save(buffer, "PNG")
    return base64.b64encode(buffer.getvalue())


class TestDocumentsAccessTrackingCron(TransactionCase):
    def _run_cron(self):
        with patch.object(
            IrCron, "_commit_progress", lambda self, *args, **kwargs: float("inf")
        ):
            self.env["document.access.tracking"]._cron_generate_tracking()

    def test_cron_drops_unrenderable_tracking_instead_of_wedging(self):
        Tracking = self.env["document.access.tracking"]
        Tracking.search([]).unlink()
        folder = self.env["document.document"].create(
            {"name": "Tracked folder", "type": "folder"}
        )
        doomed = self.env["res.partner"].create({"name": "Doomed partner"})
        survivor = self.env["res.partner"].create({"name": "Surviving partner"})

        folder.action_update_access_rights(partners={doomed: ("view", False)})
        folder.action_update_access_rights(partners={survivor: ("view", False)})
        self.assertEqual(Tracking.search_count([]), 2)

        doomed.unlink()

        self._run_cron()

        self.assertEqual(
            Tracking.search_count([]),
            0,
            "the queue must drain even when one entry cannot be rendered",
        )

    def test_cron_drains_the_whole_queue_in_one_run(self):
        Tracking = self.env["document.access.tracking"]
        Tracking.search([]).unlink()
        folder = self.env["document.document"].create(
            {"name": "Batched folder", "type": "folder"}
        )
        for index in range(3):
            partner = self.env["res.partner"].create({"name": f"Member {index}"})
            folder.action_update_access_rights(partners={partner: ("view", False)})
        self.assertEqual(Tracking.search_count([]), 3)

        self._run_cron()

        self.assertEqual(Tracking.search_count([]), 0)


class TestDocumentsAccessGc(TransactionCase):
    def test_gc_expired_keeps_the_last_access_date(self):
        document = self.env["document.document"].create(
            {"name": "Visited document", "type": "binary"}
        )
        partner = self.env["res.partner"].create({"name": "Visitor"})
        access = self.env["document.access"].create(
            {
                "document_id": document.id,
                "partner_id": partner.id,
                "role": "view",
                "last_access_date": fields.Datetime.now(),
                "expiration_date": fields.Datetime.subtract(
                    fields.Datetime.now(), days=1
                ),
            }
        )

        self.env["document.access"]._gc_expired()

        self.assertTrue(access.exists(), "the access log row must survive")
        self.assertFalse(access.role, "the expired membership must be revoked")
        self.assertFalse(access.expiration_date)
        self.assertTrue(access.last_access_date, "the visit must still be recorded")

    def test_gc_expired_runs_in_the_autovacuum_environment(self):
        other_company = self.env["res.company"].create({"name": "Round4 Other Co"})
        documents = self.env["document.document"].create(
            [
                {"name": "Local doc", "type": "binary"},
                {
                    "name": "Other-company doc",
                    "type": "binary",
                    "company_id": other_company.id,
                },
            ]
        )
        partner = self.env["res.partner"].create({"name": "Expiring member"})
        accesses = self.env["document.access"].create(
            [
                {
                    "document_id": document.id,
                    "partner_id": partner.id,
                    "role": "view",
                    "last_access_date": fields.Datetime.now(),
                    "expiration_date": fields.Datetime.subtract(
                        fields.Datetime.now(), days=1
                    ),
                }
                for document in documents
            ]
        )

        cron_env = self.env["document.access"].with_user(self.env.ref("base.user_root"))
        cron_env._gc_expired()

        self.assertTrue(all(accesses.mapped("last_access_date")))
        self.assertFalse(any(accesses.mapped("role")), "memberships must be revoked")
        self.assertFalse(
            any(accesses.mapped("expiration_date")),
            "clearing the date is what stops the GC reselecting these rows forever",
        )

    def test_gc_expired_still_removes_pure_memberships(self):
        document = self.env["document.document"].create(
            {"name": "Unvisited document", "type": "binary"}
        )
        partner = self.env["res.partner"].create({"name": "Never visited"})
        access = self.env["document.access"].create(
            {
                "document_id": document.id,
                "partner_id": partner.id,
                "role": "view",
                "expiration_date": fields.Datetime.subtract(
                    fields.Datetime.now(), days=1
                ),
            }
        )

        self.env["document.access"]._gc_expired()

        self.assertFalse(access.exists())


@tagged("post_install", "-at_install")
class TestDocumentsAccessTrackingDrain(TransactionCaseDocuments):
    def test_cron_drains_the_whole_queue_without_recounting(self):
        Tracking = self.env["document.access.tracking"]
        Tracking.search([]).unlink()
        Tracking.create(
            [
                {
                    "changes": {"access_internal": "none"},
                    "documents": [self.folder_a.id],
                }
                for _ in range(3)
            ]
        )
        self.env.flush_all()

        reported = []

        def fake_commit_progress(self, processed=0, remaining=None, **kwargs):
            reported.append(remaining)
            return 1

        self.patch(type(self.env["ir.cron"]), "_commit_progress", fake_commit_progress)
        Tracking._cron_generate_tracking()

        self.assertFalse(Tracking.search([]), "the queue must be drained")
        self.assertEqual(
            reported,
            [2, 1, 0, 0],
            "remaining is decremented, then reported as drained",
        )


@tagged("post_install", "-at_install")
class TestDocumentsVacuumProgress(TransactionCaseDocuments):
    def test_gc_clear_bin_reports_progress(self):
        Document = self.env["document.document"]
        self.assertEqual(Document._gc_clear_bin(), (0, False))

        documents = Document.create(
            [{"name": f"trash {i}", "type": "binary"} for i in range(3)]
        )
        documents.action_archive()
        self.env.flush_all()
        # Age them the way the trash does: the purge reads the `deletion_date`
        # stamped by `action_archive`, not `write_date`, so that a rename can no
        # longer postpone a deletion the user was already promised.
        documents.sudo().deletion_date = fields.Date.today()
        self.env.invalidate_all()

        done, more = Document._gc_clear_bin()
        self.assertEqual(done, 3)
        self.assertFalse(more)
        self.assertFalse(documents.exists())

    def test_gc_expired_access_reports_progress(self):
        Access = self.env["document.access"]
        self.assertEqual(Access._gc_expired(), (0, False))

        document = self.env["document.document"].create(
            {"name": "shared.txt", "type": "binary"}
        )
        partner = self.env["res.partner"].create({"name": "expiring member"})
        Access.create(
            {
                "document_id": document.id,
                "partner_id": partner.id,
                "role": "view",
                "expiration_date": "2000-01-01 00:00:00",
            }
        )

        done, more = Access._gc_expired()
        self.assertEqual(done, 1)
        self.assertFalse(more)
        self.assertFalse(
            document.access_ids.filtered(lambda a: a.partner_id == partner)
        )

    def test_access_rights_update_survives_a_missing_cron(self):
        document = self.env["document.document"].create(
            {"name": "shared.txt", "type": "binary"}
        )
        partner = self.env["res.partner"].create({"name": "new member"})
        self.env.ref("document.ir_cron_documents_access_tracking").sudo().unlink()

        document.action_update_access_rights(
            partners={partner.id: ("view", False)},
        )

        self.assertEqual(
            document.access_ids.filtered(lambda a: a.partner_id == partner).role,
            "view",
        )


@tagged("post_install", "-at_install")
class TestDocumentsTrashExpiry(TransactionCaseDocuments):
    """The purge runs on the date the trash promised, and on no other.

    `_get_domain_gc_clear_bin` used to re-derive the date as
    `write_date <= now - document.deletion_delay`, which is a different
    quantity from the one `action_archive` writes into the chatter. It now
    reads the `deletion_date` that archiving stamps, so the promise the user
    was given and the rule the cron applies are one value.
    """

    def _trashed(self, name="trash.txt"):
        doc = self.env["document.document"].create(
            {
                "type": "binary",
                "datas": TEXT,
                "name": name,
                "folder_id": self.folder_b.id,
                "owner_id": self.doc_user.id,
            }
        )
        doc.action_archive()
        self.assertFalse(doc.active)
        return doc

    def test_archiving_stamps_the_date_the_message_promises(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "document.deletion_delay", "30"
        )
        doc = self._trashed()

        self.assertEqual(
            doc.deletion_date,
            fields.Date.today() + relativedelta(days=30),
            "the stored date is the one the archive message quotes",
        )
        body = doc.message_ids[0].body
        self.assertIn(fields.Date.to_string(doc.deletion_date), body)

    def test_gc_clear_bin_purges_on_that_date_and_not_before(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "document.deletion_delay", "30"
        )
        Doc = self.env["document.document"]
        doc = self._trashed()

        Doc._gc_clear_bin()
        self.assertTrue(doc.exists(), "not before the date it was promised")

        doc.sudo().deletion_date = fields.Date.today()
        Doc._gc_clear_bin()
        self.assertFalse(doc.exists(), "and on it, not a day later")

    def test_a_later_write_does_not_move_the_date(self):
        """The whole point: a rename is not a stay of execution.

        Under the old rule any write restarted the countdown -- a rename, a
        stored recompute, a bridge detaching `res_model` when its record was
        deleted -- silently, with no new message and nothing in the UI saying
        the date had moved.
        """
        self.env["ir.config_parameter"].sudo().set_param(
            "document.deletion_delay", "30"
        )
        Doc = self.env["document.document"]
        doc = self._trashed("about-to-be-renamed.txt")
        promised = doc.deletion_date
        doc.sudo().deletion_date = fields.Date.today()

        doc.sudo().write({"name": "renamed.txt"})

        self.assertEqual(
            doc.deletion_date,
            fields.Date.today(),
            "renaming a trashed document must not postpone its deletion",
        )
        self.assertNotEqual(promised, doc.deletion_date)
        Doc._gc_clear_bin()
        self.assertFalse(doc.exists())

    def test_changing_the_delay_does_not_move_documents_already_in_the_trash(self):
        """A settings change is not retroactive on promises already made."""
        self.env["ir.config_parameter"].sudo().set_param(
            "document.deletion_delay", "30"
        )
        Doc = self.env["document.document"]
        doc = self._trashed("promised-30-days.txt")

        self.env["ir.config_parameter"].sudo().set_param("document.deletion_delay", "1")
        Doc._gc_clear_bin()

        self.assertTrue(
            doc.exists(),
            "shortening the delay must not purge, on the next cron run, a "
            "document whose own message promised it weeks more",
        )
        self.assertEqual(
            doc.deletion_date, fields.Date.today() + relativedelta(days=30)
        )

    def test_restoring_takes_a_document_off_the_schedule(self):
        doc = self._trashed("restored.txt")
        self.assertTrue(doc.deletion_date)

        doc.action_unarchive()

        self.assertTrue(doc.active)
        self.assertFalse(
            doc.deletion_date, "out of the trash means off the purge schedule"
        )
        # Even a bare sudo write -- which skips `action_archive` -- puts the
        # document on the schedule, because the stamp happens on the active
        # transition rather than inside the action.
        doc.sudo().write({"active": False})
        self.assertEqual(
            doc.deletion_date,
            fields.Date.today() + relativedelta(days=doc.get_deletion_delay()),
            "no path into the trash may leave a document without a date, or "
            "the purge would never reach it",
        )


@tagged("post_install", "-at_install")
class TestDocumentsRecentRetention(TransactionCaseDocuments):
    """ "Recent" rows are history, and history is the thing that needs a sweep.

    `_upsert_last_access_date` inserts one `document.access` row per (document,
    partner) the first time a signed-in user opens a document. Nothing removed
    them: `_gc_expired` only touches rows carrying an `expiration_date`, and a
    Recent row has none. The table grew as users x documents-ever-opened, while
    `document.access.log` -- which records strictly less -- has had a retention
    sweep all along.
    """

    def _recent_row(self, document, partner, days_ago):
        row = self.env["document.access"].create(
            {
                "document_id": document.id,
                "partner_id": partner.id,
                "last_access_date": fields.Datetime.subtract(
                    fields.Datetime.now(), days=days_ago
                ),
            }
        )
        self.assertFalse(row.role, "a Recent row carries no role")
        return row

    def test_a_long_untouched_recent_row_is_collected(self):
        old = self._recent_row(self.document_txt, self.internal_user.partner_id, 400)
        fresh = self._recent_row(self.document_gif, self.internal_user.partner_id, 10)

        removed, more = self.env["document.access"]._gc_recent()

        self.assertEqual(removed, 1)
        self.assertFalse(more)
        self.assertFalse(old.exists())
        self.assertTrue(fresh.exists(), "rows inside the window are kept")

    def test_a_membership_is_never_aged_out(self):
        """A row with a role is access, not history, however old its visit."""
        member = self._recent_row(self.document_txt, self.portal_user.partner_id, 4000)
        member.role = "view"

        self.env["document.access"]._gc_recent()

        self.assertTrue(
            member.exists(),
            "someone keeps their access whatever the date they last looked",
        )

    def test_the_sweep_can_be_switched_off(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "document.recent_retention_days", "0"
        )
        old = self._recent_row(self.document_txt, self.internal_user.partner_id, 4000)

        removed, more = self.env["document.access"]._gc_recent()

        self.assertEqual((removed, more), (0, False))
        self.assertTrue(old.exists())


@tagged("post_install", "-at_install")
class TestDocumentsTrashInvariant(TransactionCaseDocuments):
    """Not active implies a deletion date, whatever route put it there.

    The purge reads `deletion_date`, so a document that reaches the trash
    without one is a document the purge can never reach. `active` can take the
    value False in exactly two places -- `create` and the write transition --
    and both are covered here, because the interesting routes use the first:
    `message_new` creates every mail-gateway document with `active=False`, and
    `document_sign` creates its signed copies the same way.
    """

    def _dated(self, document):
        return document.deletion_date == fields.Date.today() + relativedelta(
            days=document.get_deletion_delay()
        )

    def test_a_document_born_in_the_trash_is_on_the_schedule(self):
        document = self.env["document.document"].create(
            {"name": "born-archived.txt", "type": "binary", "active": False}
        )

        self.assertFalse(document.active)
        self.assertTrue(
            self._dated(document),
            "a document created archived never goes through the write "
            "transition, so `create` is the only place that can date it",
        )

    def test_the_mail_gateway_document_is_on_the_schedule(self):
        """The route that actually does this in production."""
        folder = self.env["document.document"].create(
            {"name": "alias folder", "type": "folder"}
        )
        document = self.env["document.document"].message_new(
            {"subject": "an incoming mail", "from": "someone@example.com"},
            {"folder_id": folder.id},
        )

        self.assertFalse(document.active, "the gateway files mail archived")
        self.assertTrue(self._dated(document))

    def test_a_sudo_write_into_the_trash_is_on_the_schedule(self):
        """The write half: `write` only reroutes to `action_archive` when the
        caller is not superuser, so a sudo write reaches the trash directly."""
        document = self.env["document.document"].create(
            {"name": "sudo-archived.txt", "type": "binary"}
        )

        document.sudo().write({"active": False})

        self.assertFalse(document.active)
        self.assertTrue(self._dated(document))

    def test_no_active_document_carries_one(self):
        """The other half of the invariant, so the fix cannot over-apply."""
        document = self.env["document.document"].create(
            {"name": "plain.txt", "type": "binary"}
        )

        self.assertTrue(document.active)
        self.assertFalse(document.deletion_date)
