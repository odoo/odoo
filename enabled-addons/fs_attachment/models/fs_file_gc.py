# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging
import threading
from contextlib import closing, contextmanager

from odoo import api, fields, models
from odoo.sql_db import Cursor

_logger = logging.getLogger(__name__)


class FsFileGC(models.Model):
    _name = "fs.file.gc"
    _description = "Filesystem storage file garbage collector"

    store_fname = fields.Char("Stored Filename")
    fs_storage_code = fields.Char("Storage Code")

    _sql_constraints = [
        (
            "store_fname_uniq",
            "unique (store_fname)",
            "The stored filename must be unique!",
        ),
    ]

    def _is_test_mode(self) -> bool:
        """Return True if we are running the tests, so we do not mark files for
        garbage collection into a separate transaction.
        """
        return (
            getattr(threading.current_thread(), "testing", False)
            or self.env.registry.in_test_mode()
        )

    @contextmanager
    def _in_new_cursor(self) -> Cursor:
        """Context manager to execute code in a new cursor"""
        if self._is_test_mode() or not self.env.registry.ready:
            yield self.env.cr
            return

        with closing(self.env.registry.cursor()) as cr:
            try:
                yield cr
            except Exception:
                cr.rollback()
                raise
            else:
                # disable pylint error because this is a valid commit,
                # we are in a new env
                cr.commit()  # pylint: disable=invalid-commit

    @api.model
    def _mark_for_gc(self, store_fname: str) -> None:
        """Mark a file for garbage collection"

        This process is done in a separate transaction since the data must be
        preserved even if the transaction is rolled back.
        """
        with self._in_new_cursor() as cr:
            code = store_fname.partition("://")[0]
            # use plain SQL to avoid the ORM ignore conflicts errors
            cr.execute(
                """
                INSERT INTO
                    fs_file_gc (
                        store_fname,
                        fs_storage_code,
                        create_date,
                        write_date,
                        create_uid,
                        write_uid
                    )
                    VALUES (
                        %s,
                        %s,
                        now() at time zone 'UTC',
                        now() at time zone 'UTC',
                        %s,
                        %s
                    )
                ON CONFLICT DO NOTHING
            """,
                (store_fname, code, self.env.uid, self.env.uid),
            )

    @api.autovacuum
    def _gc_files(self) -> None:
        """Garbage collect files"""
        # This method is mainly a copy of the method _gc_file_store_unsafe()
        # from the module fs_attachment. The only difference is that the list
        # of files to delete is retrieved from the table fs_file_gc instead
        # of the odoo filestore.

        # Continue in a new transaction. The LOCK statement below must be the
        # first one in the current transaction, otherwise the database snapshot
        # used by it may not contain the most recent changes made to the table
        # ir_attachment! Indeed, if concurrent transactions create attachments,
        # the LOCK statement will wait until those concurrent transactions end.
        # But this transaction will not see the new attachements if it has done
        # other requests before the LOCK (like the method _storage() above).
        cr = self._cr
        cr.commit()  # pylint: disable=invalid-commit

        # prevent all concurrent updates on ir_attachment and fs_file_gc
        # while collecting, but only attempt to grab the lock for a little bit,
        # otherwise it'd start blocking other transactions.
        # (will be retried later anyway)
        cr.execute("SET LOCAL lock_timeout TO '10s'")
        cr.execute("LOCK fs_file_gc IN SHARE MODE")
        cr.execute("LOCK ir_attachment IN SHARE MODE")

        self._gc_files_unsafe()

        # commit to release the lock
        cr.commit()  # pylint: disable=invalid-commit

    def _gc_files_unsafe(self) -> None:
        # get the list of fs.storage codes that must be autovacuumed
        codes = (
            self.env["fs.storage"].search([]).filtered("autovacuum_gc").mapped("code")
        )
        if not codes:
            return
        # we process by batch of storage codes.
        self._cr.execute(
            """
            SELECT
                fs_storage_code,
                array_agg(store_fname)

            FROM
                fs_file_gc
            WHERE
                fs_storage_code IN %s
                AND NOT EXISTS (
                    SELECT 1
                    FROM ir_attachment
                    WHERE store_fname = fs_file_gc.store_fname
                )
            GROUP BY
                fs_storage_code
            """,
            (tuple(codes),),
        )
        for code, store_fnames in self._cr.fetchall():
            self.env["fs.storage"].get_by_code(code)
            fs = self.env["fs.storage"].get_fs_by_code(code)
            for store_fname in store_fnames:
                try:
                    file_path = store_fname.partition("://")[2]
                    fs.rm(file_path)
                except Exception:
                    _logger.debug("Failed to remove file %s", store_fname)

        # delete the records from the table fs_file_gc
        self._cr.execute(
            """
            DELETE FROM
                fs_file_gc
            WHERE
                fs_storage_code IN %s
            """,
            (tuple(codes),),
        )
