import shutil
from unittest.mock import MagicMock, patch

import pytest

from odoo.service.db import lifecycle


@pytest.fixture
def renaming(tmp_path):
    def _run(*, old_exists=True, new_exists=False, move=None, rollback=None):
        stores = {"old": tmp_path / "old", "new": tmp_path / "new"}
        if old_exists:
            (stores["old"] / "a").mkdir(parents=True)
            (stores["old"] / "a" / "att.bin").write_bytes(b"payload")
        if new_exists:
            stores["new"].mkdir(parents=True)

        cfg = MagicMock()
        cfg.filestore.side_effect = lambda name: str(stores[name])
        cr = MagicMock()
        conn = MagicMock()
        conn.cursor.return_value = cr
        rolled = []

        def _rollback(_cr, old, new):
            rolled.append((old, new))
            if rollback is not None:
                raise rollback

        with (
            patch.object(lifecycle.odoo.tools, "config", cfg),
            patch.object(lifecycle, "check_db_name"),
            patch.object(lifecycle, "_check_filestore_dest_free"),
            patch.object(lifecycle, "_retry_terminate_then_ddl"),
            patch.object(lifecycle, "invalidate_catalog_caches"),
            patch.object(lifecycle, "_rollback_db_rename", side_effect=_rollback),
            patch.object(lifecycle.odoo.db, "db_connect", return_value=conn),
            patch.object(lifecycle.odoo.db, "close_db"),
            patch.object(
                lifecycle.odoo.modules.registry.Registry, "clear_database_state"
            ),
            patch.object(
                lifecycle,
                "shutil",
                MagicMock(move=move if move is not None else shutil.move),
            ),
        ):
            try:
                result = lifecycle.rename_database("old", "new")
            except Exception as exc:
                result = exc
        return result, rolled, stores

    return _run


class TestRenameSucceeds:
    def test_the_filestore_follows_the_database(self, renaming):
        result, rolled, stores = renaming()
        assert result is True
        assert rolled == [], "nothing to roll back"
        assert (stores["new"] / "a" / "att.bin").read_bytes() == b"payload"
        assert not stores["old"].exists()

    def test_a_database_with_no_filestore_yet_is_still_renamed(self, renaming):
        result, rolled, stores = renaming(old_exists=False)
        assert result is True
        assert rolled == []
        assert not stores["new"].exists(), "nothing to move, nothing created"


class TestRenameRollsBack:
    def test_a_destination_that_appeared_mid_rename_undoes_the_rename(self, renaming):
        result, rolled, _ = renaming(new_exists=True)
        assert isinstance(result, RuntimeError)
        assert "appeared between pre-flight and move" in str(result)
        assert "rolled back" in str(result).lower()
        assert rolled == [("old", "new")], (
            "the pre-flight said the destination was free and it is not, so "
            "the rename has to be undone — leaving it renamed points the "
            "database at somebody else's filestore"
        )

    def test_a_failed_move_undoes_the_rename(self, renaming):
        boom = MagicMock(side_effect=OSError("cross-device link"))
        result, rolled, _ = renaming(move=boom)
        assert isinstance(result, RuntimeError)
        assert "Database rename rolled back" in str(result)
        assert rolled == [("old", "new")]

    def test_the_original_cause_is_kept(self, renaming):
        boom = MagicMock(side_effect=OSError("cross-device link"))
        result, _, _ = renaming(move=boom)
        assert isinstance(result.__cause__, OSError), (
            "the filestore error is the only thing that says WHY the move "
            "failed; the rollback message replaces it otherwise"
        )
        assert "cross-device link" in str(result)


class TestRenameCannotRollBack:
    def test_a_failed_rollback_says_the_two_are_out_of_sync(self, renaming):
        result, rolled, _ = renaming(
            move=MagicMock(side_effect=OSError("disk full")),
            rollback=RuntimeError("database is being accessed by other users"),
        )
        assert isinstance(result, RuntimeError)
        message = str(result)
        assert "out of sync" in message
        assert "manual intervention required" in message, (
            "this is the only path that cannot be recovered automatically, so "
            "it must not read like the ordinary rollback message"
        )
        assert rolled == [("old", "new")], "the rollback was at least attempted"

    def test_it_names_both_failures(self, renaming):
        result, _, _ = renaming(
            move=MagicMock(side_effect=OSError("disk full")),
            rollback=RuntimeError("still connected"),
        )
        message = str(result)
        assert "disk full" in message, "what went wrong first"
        assert "still connected" in message, "and why it could not be undone"

    def test_the_first_failure_stays_the_cause(self, renaming):
        result, _, _ = renaming(
            move=MagicMock(side_effect=OSError("disk full")),
            rollback=RuntimeError("still connected"),
        )
        assert isinstance(result.__cause__, OSError)
        assert "disk full" in str(result.__cause__)


class TestNonCTemplateWarning:
    def _warn(self, collate):
        cr = MagicMock()
        cr.fetchone.return_value = None if collate is None else (collate,)
        lifecycle._warn_on_non_c_template(cr, "tpl")
        return cr

    def test_a_c_collation_says_nothing(self, caplog):
        self._warn("C")
        assert not caplog.records

    def test_a_locale_collation_warns(self, caplog):
        self._warn("es_ES.UTF-8")
        assert "es_ES.UTF-8" in caplog.text
        assert "ORDER BY" in caplog.text, (
            "the consequence is what matters: every database created from that "
            "template sorts differently from the one CI measured against"
        )

    def test_a_template_that_does_not_exist_is_not_an_error(self, caplog):
        self._warn(None)
        assert not caplog.records, (
            "the CREATE itself will report a missing template; warning about "
            "its collation first would bury that"
        )


class TestRollbackTerminatesBackends:
    def _rollback(self, execute_effects):
        import psycopg

        cr = MagicMock()
        cr.execute.side_effect = execute_effects
        terminated = []
        with (
            patch.object(lifecycle, "get_database_identifier", lambda _cr, n: n),
            patch.object(
                lifecycle,
                "_terminate_backends",
                lambda _cr, target: terminated.append(target),
            ),
            patch.object(lifecycle.time, "sleep"),
        ):
            try:
                result = lifecycle._rollback_db_rename(cr, "old", "new")
            except Exception as exc:
                result = exc
        return result, terminated, cr, psycopg

    def test_a_backend_on_the_new_name_is_terminated_and_the_rename_retried(
        self,
    ):
        import psycopg

        result, terminated, cr, _ = self._rollback(
            [psycopg.errors.ObjectInUse("accessed by other users"), None]
        )
        assert result is None, (
            "the forward rename recovers from ObjectInUse by terminating "
            "backends and retrying; the rollback of that same rename must "
            "not give up on the first attempt and report the database and "
            "filestore as out of sync"
        )
        assert terminated == ["new", "new"], (
            "the backends squatting the NEW name are the ones holding the "
            "reverse rename"
        )
        assert cr.execute.call_count == 2

    def test_a_rollback_still_in_use_after_all_retries_reports_it(self):
        import psycopg

        result, _, _, _ = self._rollback(
            psycopg.errors.ObjectInUse("accessed by other users")
        )
        assert isinstance(result, RuntimeError)
        assert "still in use" in str(result)
