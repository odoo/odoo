import base64
import io
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from odoo.service.db import restore


def _zip_bytes(entries: dict[str, bytes], *, dirs: tuple[str, ...] = ()) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name in dirs:
            z.writestr(zipfile.ZipInfo(name), b"")
        for name, payload in entries.items():
            z.writestr(name, payload)
    return buf.getvalue()


class TestExtractMembersBounded:
    def _extract(self, tmp_path, blob, members, budget=10 * 1024 * 1024):
        archive = tmp_path / "in.zip"
        archive.write_bytes(blob)
        dest = tmp_path / "out"
        dest.mkdir()
        with zipfile.ZipFile(archive) as z:
            written = restore._extract_members_bounded(z, members, str(dest), budget)
        return written, dest

    def test_a_directory_member_is_created_not_opened(self, tmp_path):
        blob = _zip_bytes({"filestore/a/f.bin": b"x" * 10}, dirs=("filestore/a/",))
        written, dest = self._extract(
            tmp_path, blob, ["filestore/a/", "filestore/a/f.bin"]
        )
        assert (dest / "filestore" / "a").is_dir()
        assert written == 10, (
            "a directory entry has no bytes; counting it against the budget "
            "would make an archive's directory depth part of its size"
        )

    def test_a_file_in_an_undeclared_directory_still_lands(self, tmp_path):
        blob = _zip_bytes({"filestore/deep/nested/f.bin": b"y" * 5})
        _, dest = self._extract(tmp_path, blob, ["filestore/deep/nested/f.bin"])
        assert (
            dest / "filestore" / "deep" / "nested" / "f.bin"
        ).read_bytes() == b"y" * 5

    def test_an_over_budget_archive_is_refused(self, tmp_path):
        blob = _zip_bytes({"dump.sql": b"z" * 4096})
        with pytest.raises(RuntimeError, match=r"expands to more than"):
            self._extract(tmp_path, blob, ["dump.sql"], budget=16)


@pytest.fixture
def restoring(tmp_path):
    def _run(blob, *, on_extract=None):
        archive = tmp_path / "backup.zip"
        archive.write_bytes(blob)
        moved = []
        with (
            patch.object(restore, "exp_db_exist", return_value=False),
            patch.object(restore, "create_empty_database"),
            patch.object(restore, "_rollback_new_database"),
            patch.object(restore, "_check_filestore_dest_free"),
            patch.object(restore, "_check_dump_sql_safe"),
            patch.object(restore, "check_db_name"),
            patch.object(restore, "shutil", MagicMock(move=lambda *a: moved.append(a))),
            patch.object(restore.odoo.tools, "config", MagicMock()),
            patch.object(restore, "subprocess") as sub,
            patch.object(restore.odoo.modules.registry, "Registry") as registry,
        ):
            sub.run.return_value = MagicMock(returncode=0, stderr=b"")
            registry.new.return_value.cursor.return_value.__enter__ = MagicMock()
            registry.new.return_value.cursor.return_value.__exit__ = MagicMock(
                return_value=False
            )
            if on_extract is not None:
                on_extract(restore)
            restore.restore_db("target", str(archive))
        return moved

    return _run


class TestArchiveMustBeAnOdooBackup:
    def test_an_archive_without_dump_sql_is_refused(self, restoring):
        blob = _zip_bytes({"filestore/a.bin": b"x", "README.txt": b"hello"})
        with pytest.raises(RuntimeError, match=r"no 'dump\.sql' member"):
            restoring(blob)

    def test_the_message_says_what_the_file_is_not(self, restoring):
        blob = _zip_bytes({"notes.txt": b"x"})
        with pytest.raises(RuntimeError, match="not an Odoo database"):
            restoring(blob)

    def test_a_zip_of_the_wrong_kind_is_refused_before_any_sql_runs(self, restoring):
        blob = _zip_bytes({"notes.txt": b"x"})
        with (
            patch.object(restore, "_check_dump_sql_safe") as scanned,
            pytest.raises(RuntimeError),
        ):
            restoring(blob)
        assert not scanned.called, (
            "the refusal must come before the dump scanner, or a hostile "
            "archive gets a scan it should never have earned"
        )


class TestRawRestoreNeedsAPath:
    def test_a_file_object_holding_plain_sql_is_refused(self):
        handle = io.BytesIO(b"-- not a zip\nSELECT 1;\n")
        with (
            patch.object(restore, "exp_db_exist", return_value=False),
            patch.object(restore, "create_empty_database"),
            patch.object(restore, "_rollback_new_database"),
            patch.object(restore, "_check_filestore_dest_free"),
            patch.object(restore, "check_db_name"),
            patch.object(restore.odoo.tools, "config", MagicMock()),
            pytest.raises(TypeError, match="needs a file path"),
        ):
            restore.restore_db("target", handle)


class TestExpRestoreTrailingQuad:
    def _roundtrip(self, payload, *, chunk=None):
        encoded = base64.b64encode(payload).decode()
        seen = {}

        def fake_restore(db_name, path, copy=False):
            seen["bytes"] = Path(path).read_bytes()

        with patch.object(restore, "restore_db", side_effect=fake_restore):
            if chunk is None:
                assert restore.exp_restore("db", encoded) is True
            else:
                with patch.object(restore, "CHUNK", chunk):
                    assert restore.exp_restore("db", encoded) is True
        return seen["bytes"]

    def test_a_truncated_upload_is_refused_rather_than_silently_restored(self):
        truncated = base64.b64encode(b"a database dump").decode()[:-3]
        assert len(truncated) % 4 != 0, truncated
        with (
            patch.object(restore, "restore_db") as restored,
            pytest.raises(Exception, match=r"(?i)base64|padding"),
        ):
            restore.exp_restore("db", truncated)
        assert not restored.called, "nothing may be restored from a broken upload"

    def test_whitespace_in_the_upload_is_stripped_not_decoded(self):
        payload = b"hello world"
        encoded = "\n".join(
            base64.b64encode(payload).decode()[i : i + 4] for i in range(0, 16, 4)
        )
        seen = {}
        with patch.object(
            restore,
            "restore_db",
            side_effect=lambda d, p, copy=False: seen.update(b=Path(p).read_bytes()),
        ):
            restore.exp_restore("db", encoded)
        assert seen["b"] == payload, (
            "an HTTP form wraps long base64; failing to strip the newlines "
            "makes every wrapped upload a corrupt dump"
        )

    def test_the_temporary_file_is_removed_even_when_the_restore_raises(self):
        encoded = base64.b64encode(b"payload").decode()
        leaked = {}
        with (
            patch.object(
                restore,
                "restore_db",
                side_effect=lambda d, p, copy=False: (
                    leaked.update(path=p)
                    or (_ for _ in ()).throw(RuntimeError("restore blew up"))
                ),
            ),
            pytest.raises(RuntimeError, match="blew up"),
        ):
            restore.exp_restore("db", encoded)
        assert not Path(leaked["path"]).exists(), (
            "a failed restore that leaves its upload behind fills the data "
            "directory one attempt at a time"
        )
