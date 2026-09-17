import base64
import contextlib
import inspect
import io
from unittest.mock import patch

import psycopg.errors

from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

from odoo.addons.base.models import ir_attachment_storage
from odoo.addons.base.models.ir_attachment_storage import (
    STORAGE_BACKENDS,
    AttachmentStorage,
    DbStorage,
    FileStorage,
    UnknownSchemeStorage,
    register_storage,
)


class TestIrAttachmentStorage(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Attachment = self.env["ir.attachment"]
        self.icp = self.env["ir.config_parameter"]

    def test_location_selection(self):
        self.assertIsInstance(self.Attachment._get_storage_backend(), FileStorage)
        self.icp.set_param("ir_attachment.location", "db")
        self.assertIsInstance(self.Attachment._get_storage_backend(), DbStorage)
        self.icp.set_param("ir_attachment.location", "s3")
        self.assertIsInstance(self.Attachment._get_storage_backend(), FileStorage)

    def test_key_dispatch(self):
        plain = self.Attachment._get_storage_backend_for_key("ab/abcdef0123")
        self.assertIsInstance(plain, FileStorage)
        self.addCleanup(
            ir_attachment_storage._UNKNOWN_SCHEMES_WARNED.discard,
            (self.env.cr.dbname, "weird"),
        )
        with mute_logger("odoo.addons.base.models.ir_attachment_storage"):
            unknown = self.Attachment._get_storage_backend_for_key("weird://bucket/key")
        self.assertIsInstance(unknown, UnknownSchemeStorage)

        class FakeS3Storage(AttachmentStorage):
            location = "fake_s3"
            key_scheme = "fake-s3"

        register_storage(FakeS3Storage)
        try:
            owned = self.Attachment._get_storage_backend_for_key("fake-s3://bucket/key")
            self.assertIsInstance(owned, FakeS3Storage)
            self.icp.set_param("ir_attachment.location", "fake_s3")
            self.assertIsInstance(self.Attachment._get_storage_backend(), FakeS3Storage)
        finally:
            STORAGE_BACKENDS.pop("fake_s3")

    def test_remote_key_removal_waits_for_the_commit(self):
        removed = []

        class FakeRemoteStorage(AttachmentStorage):
            location = "fake_remote"
            key_scheme = "fake-remote"

            def remove(self, key):
                removed.append(key)

        register_storage(FakeRemoteStorage)
        self.addCleanup(STORAGE_BACKENDS.pop, "fake_remote", None)
        attachment = self.Attachment.create({"name": "remote", "raw": b"x"})
        attachment.flush_recordset()
        self.env.cr.execute(
            "UPDATE ir_attachment SET store_fname = %s WHERE id = %s",
            ["fake-remote://bucket/key", attachment.id],
        )
        attachment.invalidate_recordset()

        attachment.unlink()
        self.assertEqual(removed, [], "a remote delete must not precede the commit")
        self.env.cr.postcommit.run()
        self.assertEqual(removed, ["fake-remote://bucket/key"])

    def test_remote_key_referenced_again_before_the_commit_is_kept(self):
        removed = []

        class FakeRemoteStorage(AttachmentStorage):
            location = "fake_remote"
            key_scheme = "fake-remote"

            def remove(self, key):
                removed.append(key)

        register_storage(FakeRemoteStorage)
        self.addCleanup(STORAGE_BACKENDS.pop, "fake_remote", None)
        key = "fake-remote://bucket/shared"
        first, second = self.Attachment.create(
            [{"name": "a", "raw": b"x"}, {"name": "b", "raw": b"y"}]
        )
        (first + second).flush_recordset()
        self.env.cr.execute(
            "UPDATE ir_attachment SET store_fname = %s WHERE id = %s", [key, first.id]
        )
        first.invalidate_recordset()
        first.unlink()
        self.env.cr.execute(
            "UPDATE ir_attachment SET store_fname = %s WHERE id = %s", [key, second.id]
        )
        self.env.cr.postcommit.run()
        self.assertEqual(removed, [], "a key another row took back must survive")

    def test_unknown_scheme_warns_once(self):
        dbname = self.env.cr.dbname
        self.addCleanup(
            ir_attachment_storage._UNKNOWN_SCHEMES_WARNED.discard, (dbname, "ghost-s3")
        )
        with self.assertLogs(
            "odoo.addons.base.models.ir_attachment_storage", level="WARNING"
        ) as cm:
            backend = self.Attachment._get_storage_backend_for_key(
                "ghost-s3://bucket/key"
            )
        self.assertIsInstance(backend, UnknownSchemeStorage)
        self.assertEqual(len(cm.records), 1)
        message = cm.records[0].getMessage()
        self.assertIn("No storage backend registered", message)
        self.assertIn("ghost-s3", message)
        with patch.object(ir_attachment_storage._logger, "warning") as warn:
            again = self.Attachment._get_storage_backend_for_key(
                "ghost-s3://bucket/other"
            )
        self.assertIsInstance(again, UnknownSchemeStorage)
        warn.assert_not_called()

    def test_unknown_scheme_warns_per_database(self):
        dbname = self.env.cr.dbname
        other = f"{dbname}__other"
        for key in ((dbname, "twin-s3"), (other, "twin-s3")):
            self.addCleanup(ir_attachment_storage._UNKNOWN_SCHEMES_WARNED.discard, key)

        with self.assertLogs(
            "odoo.addons.base.models.ir_attachment_storage", level="WARNING"
        ):
            self.Attachment._get_storage_backend_for_key("twin-s3://bucket/key")

        with (
            patch.object(self.env.cr, "dbname", other),
            self.assertLogs(
                "odoo.addons.base.models.ir_attachment_storage", level="WARNING"
            ) as cm,
        ):
            self.Attachment._get_storage_backend_for_key("twin-s3://bucket/key")
        self.assertEqual(len(cm.records), 1, "a second database must be told too")

    def test_register_storage_rejects_a_contested_location(self):

        class FirstStorage(AttachmentStorage):
            location = "contested"
            key_scheme = "first"

        class SecondStorage(AttachmentStorage):
            location = "contested"
            key_scheme = "second"

        register_storage(FirstStorage)
        try:
            with self.assertRaises(ValueError):
                register_storage(SecondStorage)
            self.assertIs(STORAGE_BACKENDS["contested"], FirstStorage)
            self.assertIs(register_storage(FirstStorage), FirstStorage)
        finally:
            STORAGE_BACKENDS.pop("contested", None)

        class NamelessStorage(AttachmentStorage):
            key_scheme = "nameless"

        with self.assertRaises(ValueError):
            register_storage(NamelessStorage)
        self.assertNotIn("", STORAGE_BACKENDS)

    def test_stream_key_dispatch(self):
        att = self.Attachment.create({"name": "ks.bin", "raw": b"ks-payload"})

        class FakeStreamStorage(AttachmentStorage):
            location = "fake_stream"
            key_scheme = "fake-stream"

            def to_stream(self, attachment, stream):
                stream.type = "url"
                stream.url = "fake://served"
                return stream

        register_storage(FakeStreamStorage)
        try:
            self.env.cr.execute(
                "UPDATE ir_attachment SET store_fname = %s WHERE id = %s",
                ["fake-stream://bucket/key", att.id],
            )
            att.invalidate_recordset()
            stream = att._to_http_stream()
            self.assertEqual((stream.type, stream.url), ("url", "fake://served"))
        finally:
            STORAGE_BACKENDS.pop("fake_stream")

    def test_write_fragment_matches_model(self):
        for location, backend_cls in (("file", FileStorage), ("db", DbStorage)):
            self.icp.set_param("ir_attachment.location", location)
            for data in (b"payload", b""):
                with self.subTest(location=location, data=data):
                    model_vals = self.Attachment._prepare_content_vals(
                        data, "text/plain"
                    )
                    checksum = self.Attachment._get_content_checksum(data)
                    fragment = backend_cls(self.env).write(data, checksum)
                    self.assertEqual(fragment["store_fname"], model_vals["store_fname"])
                    self.assertEqual(fragment["db_datas"], model_vals["db_datas"])

    def test_gc_lock_not_available_is_reported_and_sweeps_nothing(self):
        real_execute = self.env.cr.execute
        marker = self.Attachment._get_filestore_dir("checklist") / "zz/lock-probe"
        self.addCleanup(marker.unlink, missing_ok=True)
        self.Attachment._mark_for_gc("zz/lock-probe")
        grace = patch.object(type(self.Attachment), "_GC_CHECKLIST_GRACE", 0)
        grace.start()
        self.addCleanup(grace.stop)

        def fake_execute(query, *args, **kwargs):
            if str(query).startswith("LOCK ir_attachment"):
                raise psycopg.errors.LockNotAvailable("simulated lock timeout")
            return real_execute(query, *args, **kwargs)

        with (
            patch.object(self.env.cr, "commit", lambda: None),
            patch.object(self.env.cr, "rollback", lambda: None),
            patch.object(self.env.cr, "execute", side_effect=fake_execute),
        ):
            result = FileStorage(self.env).autovacuum()
        self.assertIs(result, False)
        with (
            patch.object(self.env.cr, "commit", lambda: None),
            patch.object(self.env.cr, "rollback", lambda: None),
            patch.object(self.env.cr, "execute", side_effect=fake_execute),
            self.assertLogs(
                "odoo.addons.base.models.ir_attachment", level="WARNING"
            ) as logs,
        ):
            result = self.Attachment._gc_file_store()
        self.assertTrue(
            any("could not take its lock" in msg for msg in logs.output),
            f"a silently skipped sweep is invisible to operators: {logs.output!r}",
        )
        self.assertEqual(
            result,
            (0, 0),
            "ir.autovacuum only reads a 2-tuple, and a lock skip makes no "
            "progress, so it must not ask to be requeued",
        )

    def test_unknown_scheme_streams_a_missing_error_not_empty_bytes(self):
        from odoo.exceptions import MissingError

        dbname = self.env.cr.dbname
        self.addCleanup(
            ir_attachment_storage._UNKNOWN_SCHEMES_WARNED.discard, (dbname, "nosuch")
        )
        att = self.Attachment.create({"name": "lost.bin", "raw": b"payload"})
        att.flush_recordset()
        self.env.cr.execute(
            "UPDATE ir_attachment SET store_fname = %s, db_datas = NULL WHERE id = %s",
            ["nosuch://bucket/key", att.id],
        )
        att.invalidate_recordset()
        with mute_logger("odoo.addons.base.models.ir_attachment_storage"):
            self.assertEqual(att.raw, b"")
            with self.assertRaises(MissingError):
                att._to_http_stream()

    def test_gc_reports_a_capped_checklist_as_remaining_work(self):
        Attachment = self.Attachment
        markers = [
            Attachment._get_filestore_dir("checklist") / key
            for key in ("zz/cap-one", "zz/cap-two")
        ]
        for marker in markers:
            self.addCleanup(marker.unlink, missing_ok=True)
        Attachment._mark_for_gc_multi(["zz/cap-one", "zz/cap-two"])
        with (
            patch.object(type(Attachment), "_GC_MAX_ENTRIES", 1),
            patch.object(type(Attachment), "_GC_CHECKLIST_GRACE", 0),
            patch.object(self.env.cr, "commit", lambda: None),
            patch.object(self.env.cr, "rollback", lambda: None),
            mute_logger("odoo.addons.base.models.ir_attachment"),
        ):
            self.assertEqual(FileStorage(self.env).autovacuum(), (1, True))
            Attachment._mark_for_gc_multi(["zz/cap-one", "zz/cap-two"])
            self.assertEqual(Attachment._gc_file_store(), (1, 1))
            self.assertEqual(
                Attachment._gc_file_store(),
                (1, 1),
                "a run that fills the cap still reports remaining work",
            )

    def test_no_attachment_autovacuum_answers_in_a_dialect_the_runner_drops(self):
        from odoo.addons.base.models.ir_autovacuum import is_autovacuum

        model_cls = self.env["ir.attachment"].__class__
        vacuums = dict(inspect.getmembers(model_cls, is_autovacuum))
        self.assertIn("_gc_file_store", vacuums, "precondition: the sweep is one")
        for attr, func in sorted(vacuums.items()):
            with self.subTest(method=attr):
                annotation = str(func.__annotations__.get("return", "None"))
                self.assertNotIn(
                    "bool",
                    annotation,
                    f"{attr} is annotated -> {annotation}; ir.autovacuum reads a "
                    "2-tuple and silently drops everything else, so a bool "
                    "signal never reaches it",
                )
                self.assertTrue(
                    annotation == "None" or annotation.startswith("tuple"),
                    f"{attr} is annotated -> {annotation}; an autovacuum either "
                    "reports (done, remaining) or returns None",
                )


class MemoryStorage(AttachmentStorage):
    location = "memory"
    key_scheme = "mem"
    blobs: dict[str, bytes] = {}

    def _key(self, checksum: str) -> str:
        return f"mem://{checksum}"

    def write(self, data, checksum):
        if not data:
            return self._inline_datas_values(data)
        key = self._key(checksum)
        type(self).blobs[key] = bytes(data)
        return {"store_fname": key, "db_datas": False}

    def read(self, key, size=None):
        data = type(self).blobs.get(key, b"")
        return data if size is None else data[:size]

    def remove(self, key):
        self.env.cr.execute(
            "SELECT 1 FROM ir_attachment WHERE store_fname = %s LIMIT 1", [key]
        )
        if not self.env.cr.fetchone():
            type(self).blobs.pop(key, None)

    def to_stream(self, attachment, stream):
        data = self.read(attachment.store_fname)
        stream.type = "data"
        stream.data = data
        stream.size = len(data)
        stream.last_modified = attachment.write_date
        return stream


@contextlib.contextmanager
def activate_memory_storage(env):
    register_storage(MemoryStorage)
    env["ir.config_parameter"].set_param("ir_attachment.location", "memory")
    try:
        yield MemoryStorage
    finally:
        STORAGE_BACKENDS.pop("memory", None)
        MemoryStorage.blobs.clear()
        env["ir.config_parameter"].set_param("ir_attachment.location", "file")


class TestMemoryStorageCRUD(TransactionCase):
    def test_crud_lifecycle(self):
        payload = b"mem-payload"
        with activate_memory_storage(self.env):
            Attachment = self.env["ir.attachment"]
            att = Attachment.create(
                {"name": "m.txt", "raw": payload, "mimetype": "text/plain"}
            )
            self.assertTrue(att.store_fname.startswith("mem://"))
            self.assertFalse(att.db_datas)

            att.invalidate_recordset()
            self.assertEqual(att.raw, payload)
            self.assertEqual(att.datas, base64.b64encode(payload))

            stream = att._to_http_stream()
            self.assertEqual((stream.type, stream.data), ("data", payload))

            copy = att.copy()
            self.assertEqual(copy.store_fname, att.store_fname)
            copy.invalidate_recordset()
            self.assertEqual(copy.raw, payload)

            shared_key = copy.store_fname
            att.write({"raw": b"mem-rewritten"})
            self.env.cr.postcommit.run()
            self.assertIn(
                shared_key,
                MemoryStorage.blobs,
                "the rewrite must not delete the key the copy still holds",
            )
            att.invalidate_recordset()
            self.assertEqual(att.raw, b"mem-rewritten")
            copy.invalidate_recordset()
            self.assertEqual(copy.raw, payload)

            copy.unlink()
            self.assertIn(shared_key, MemoryStorage.blobs, "not before the commit")
            self.env.cr.postcommit.run()
            self.assertNotIn(shared_key, MemoryStorage.blobs)

    def test_streamed_upload_lifecycle(self):
        payload = b"streamed-into-a-custom-backend-" * 40
        text = b"hello indexable streamed content " * 30
        with activate_memory_storage(self.env):
            Attachment = self.env["ir.attachment"]

            att = Attachment._create_from_stream(
                io.BytesIO(payload), name="s.bin", mimetype="application/octet-stream"
            )
            self.assertTrue(att.store_fname.startswith("mem://"))
            self.assertEqual(att.file_size, len(payload))
            self.assertEqual(att.checksum, Attachment._get_content_checksum(payload))
            att.invalidate_recordset()
            self.assertEqual(att.raw, payload)
            self.assertEqual(att._get_content_prefix(16), payload[:16])
            self.assertEqual(att._to_http_stream().size, len(payload))

            indexed = Attachment._create_from_stream(
                io.BytesIO(text), name="s.txt", mimetype="text/plain"
            )
            self.assertTrue(
                indexed.index_content,
                "the index read must reach the backend, not the filestore",
            )

            empty = Attachment._create_from_stream(
                io.BytesIO(b""), name="e.bin", mimetype="application/octet-stream"
            )
            self.assertFalse(
                empty.store_fname, "empty content is never keyed externally"
            )
            self.assertEqual(empty.file_size, 0)

    def test_unreadable_content_copy_preserves_metadata(self):
        payload = b"e1-payload"
        with activate_memory_storage(self.env):
            att = self.env["ir.attachment"].create({"name": "e1.bin", "raw": payload})
            MemoryStorage.blobs.clear()
            att.invalidate_recordset()
            self.assertEqual(att.raw, b"")
            copy = att.copy()
            self.assertEqual(copy.file_size, len(payload))
            self.assertEqual(copy.store_fname, att.store_fname)
