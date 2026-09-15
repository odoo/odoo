import threading
from unittest.mock import patch

import odoo
import odoo.tests.cursor
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.test_http.tests.test_common import TestHttpBase


@tagged("post_install", "-at_install")
class TestHttpLifecycleOrder(TestHttpBase):
    def setUp(self):
        super().setUp()
        self.events: list[tuple[int, str]] = []

    def _instrument(self):
        events = self.events
        real_commit = odoo.db.cursor.Cursor.commit
        real_test_commit = odoo.tests.cursor.TestCursor.commit
        real_persist = odoo.http.request_class.Request._persist_session

        def commit(cr, *args, **kwargs):
            events.append((threading.get_ident(), "commit"))
            return real_commit(cr, *args, **kwargs)

        def test_commit(cr, *args, **kwargs):
            events.append((threading.get_ident(), "commit"))
            return real_test_commit(cr, *args, **kwargs)

        def persist_session(request, *args, **kwargs):
            events.append((threading.get_ident(), "save_session"))
            return real_persist(request, *args, **kwargs)

        return (
            patch.object(odoo.db.cursor.Cursor, "commit", commit),
            patch.object(odoo.tests.cursor.TestCursor, "commit", test_commit),
            patch.object(
                odoo.http.request_class.Request, "_persist_session", persist_session
            ),
        )

    def _serving_thread_events(self) -> list[str]:
        threads = {tid for tid, event in self.events if event == "save_session"}
        self.assertEqual(
            len(threads),
            1,
            f"expected exactly one serving thread, saw {len(threads)}",
        )
        (serving,) = threads
        return [event for tid, event in self.events if tid == serving]

    def test_session_is_saved_after_the_commit(self):
        self.authenticate("admin", "admin")
        milky_way = self.env.ref("test_http.milky_way")
        self.events.clear()

        commit_patch, test_commit_patch, save_patch = self._instrument()
        with commit_patch, test_commit_patch, save_patch:
            res = self.url_open(
                f"/test_http/{milky_way.id}/setname?readonly=0",
                {
                    "name": "Ordering Way",
                    "csrf_token": odoo.http.Request.csrf_token(self),
                },
            )
        res.raise_for_status()

        sequence = self._serving_thread_events()
        self.assertIn("save_session", sequence)
        self.assertIn(
            "commit",
            sequence,
            "the serving thread never committed; retrying() no longer commits",
        )
        self.assertGreater(
            sequence.index("save_session"),
            sequence.index("commit"),
            f"the session must be saved after the commit, got {sequence}",
        )

    def test_session_publication_finishes_the_request(self):
        self.authenticate("admin", "admin")
        milky_way = self.env.ref("test_http.milky_way")
        self.events.clear()

        commit_patch, test_commit_patch, save_patch = self._instrument()
        with commit_patch, test_commit_patch, save_patch:
            res = self.url_open(
                f"/test_http/{milky_way.id}/setname?readonly=0",
                {
                    "name": "Last Way",
                    "csrf_token": odoo.http.Request.csrf_token(self),
                },
            )
        res.raise_for_status()

        sequence = self._serving_thread_events()
        self.assertEqual(
            sequence[-1],
            "save_session",
            f"session publication must follow retrying()'s commit, got {sequence}",
        )

    @mute_logger("odoo.http._serve")
    def test_promotion_saves_the_successful_session_after_committing(self):
        self.authenticate("admin", "admin")
        milky_way = self.env.ref("test_http.milky_way")
        self.events.clear()

        commit_patch, test_commit_patch, save_patch = self._instrument()
        with commit_patch, test_commit_patch, save_patch:
            res = self.url_open(
                f"/test_http/{milky_way.id}/setname?readonly=1",
                {
                    "name": "Promoted Way",
                    "csrf_token": odoo.http.Request.csrf_token(self),
                },
            )
        res.raise_for_status()

        sequence = self._serving_thread_events()
        self.assertGreater(
            sequence.index("save_session"),
            sequence.index("commit"),
            f"the promoted attempt saved before committing, got {sequence}",
        )
        self.assertEqual(sequence[-1], "save_session", f"got {sequence}")

        milky_way.invalidate_recordset()
        self.assertEqual(milky_way.name, "Promoted Way")
