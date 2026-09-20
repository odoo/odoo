import base64
import contextlib
import hashlib
import io
import os
import shutil
import time
import uuid
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from odoo.api import SUPERUSER_ID
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.hashing import ALGO_TAG
from odoo.models import PREFETCH_MAX
from odoo.tests.common import TransactionCase, skip_if_dev_mode, tagged
from odoo.tools import OrderedSet, human_size, mute_logger
from odoo.tools.image import image_to_base64

from odoo.addons.base.models import ir_attachment as ir_attachment_module
from odoo.addons.base.models.ir_attachment import SECURITY_FIELDS, IrAttachment
from odoo.addons.base.tests.common import (
    TransactionCaseWithUserDemo,
    TransactionCaseWithUserPortal,
)


class TestIrAttachment(TransactionCaseWithUserDemo):
    def setUp(self):
        super().setUp()
        self.Attachment = self.env["ir.attachment"]
        self.filestore = self.Attachment._get_filestore()

        self.blob1 = b"blob1"
        self.blob1_b64 = base64.b64encode(self.blob1)
        self.blob1_hash = self.Attachment._get_content_checksum(self.blob1)
        self.blob1_fname = self.Attachment._get_store_key(self.blob1_hash)

        self.blob2 = b"blob2"
        self.blob2_b64 = base64.b64encode(self.blob2)

    def assertApproximately(self, value, expectedSize, delta=1):
        with contextlib.suppress(UnicodeDecodeError):
            value = base64.b64decode(value.decode())
        size = len(value) / 1024

        self.assertAlmostEqual(size, expectedSize, delta=delta)

    def test_01_store_in_db(self):
        self.env["ir.config_parameter"].set_param("ir_attachment.location", "db")

        a1 = self.Attachment.create({"name": "a1", "raw": self.blob1})
        self.assertEqual(a1.datas, self.blob1_b64)

        self.assertEqual(a1.db_datas, self.blob1)

    def test_02_store_on_disk(self):
        a2 = self.Attachment.create({"name": "a2", "raw": self.blob1})
        self.assertEqual(a2.store_fname, self.blob1_fname)
        self.assertTrue(Path(self.filestore, a2.store_fname).is_file())

    def test_03_no_duplication(self):
        a2 = self.Attachment.create({"name": "a2", "raw": self.blob1})
        a3 = self.Attachment.create({"name": "a3", "raw": self.blob1})
        self.assertEqual(a3.store_fname, a2.store_fname)

    def test_04_keep_file(self):
        a2 = self.Attachment.create({"name": "a2", "raw": self.blob1})
        a3 = self.Attachment.create({"name": "a3", "raw": self.blob1})

        a2_fn = Path(self.filestore, a2.store_fname)

        a3.unlink()
        self.assertTrue(a2_fn.is_file())

    def test_05_change_data_change_file(self):
        a2 = self.Attachment.create({"name": "a2", "raw": self.blob1})
        a2_store_fname1 = a2.store_fname
        a2_fn = Path(self.filestore, a2_store_fname1)

        self.assertTrue(a2_fn.is_file())

        a2.write({"raw": self.blob2})

        a2_store_fname2 = a2.store_fname
        self.assertNotEqual(a2_store_fname1, a2_store_fname2)

        a2_fn = Path(self.filestore, a2_store_fname2)
        self.assertTrue(a2_fn.is_file())

    def test_07_write_mimetype(self):

        Attachment = self.Attachment.with_user(self.user_demo.id)
        a2 = Attachment.create(
            {"name": "a2", "datas": self.blob1_b64, "mimetype": "image/png"}
        )
        self.assertEqual(
            a2.mimetype,
            "image/png",
            "the new mimetype should be the one given on write",
        )
        a3 = Attachment.create(
            {
                "name": "a3",
                "datas": self.blob1_b64,
                "mimetype": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            }
        )
        self.assertEqual(
            a3.mimetype,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "should preserve office mime type",
        )
        a4 = Attachment.create(
            {
                "name": "a4",
                "datas": self.blob1_b64,
                "mimetype": "Application/VND.OpenXMLformats-officedocument.wordprocessingml.document",
            }
        )
        self.assertEqual(
            a4.mimetype,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "should preserve office mime type (lowercase)",
        )

    def _zip_bytes(self, entry):
        import zipfile

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr(entry, entry)
        return buf.getvalue()

    def test_write_mimetype_matches_create_of_the_same_file(self):
        cases = [
            ("sheet.xlsx", self._zip_bytes("first"), self._zip_bytes("second")),
            ("report.csv", b"a,b,c\n1,2,3\n", b"c,d\n3,4\n"),
            ("notes.txt", b"hello there", b"goodbye there"),
        ]
        for name, first, second in cases:
            with self.subTest(name=name):
                attachment = self.Attachment.create({"name": name, "raw": first})
                expected = self.Attachment.create(
                    {"name": name, "raw": second}
                ).mimetype
                attachment.write({"raw": second})
                self.assertEqual(
                    attachment.mimetype,
                    expected,
                    "a content write typed the file differently from a create",
                )

    def test_write_mimetype_explicit_and_heterogeneous(self):
        forced = self.Attachment.create({"name": "a.txt", "raw": b"hello"})
        forced.write({"raw": b"other", "mimetype": "application/vnd.custom"})
        self.assertEqual(forced.mimetype, "application/vnd.custom")

        pair = self.Attachment.create(
            [
                {"name": "one.csv", "raw": b"a,b\n"},
                {"name": "two.xlsx", "raw": b"a,b\n"},
            ]
        )
        pair.write({"raw": b"x,y,z\n4,5,6\n"})
        self.assertEqual(
            set(pair.mapped("mimetype")),
            {self.Attachment._get_mimetype_from_values({"raw": b"x,y,z\n4,5,6\n"})},
            "rows disagreeing on their name must fall back to sniffing",
        )

    def test_bin_size_reports_file_size_without_reading_content(self):
        even = self.Attachment.create({"name": "even.bin", "raw": b"x" * 5000})
        odd = self.Attachment.create({"name": "odd.bin", "raw": b"y" * 4999})
        self.env.flush_all()
        self.env.invalidate_all()

        with patch.object(
            self.registry["ir.attachment"],
            "_read_file",
            side_effect=IrAttachment._read_file,
            autospec=True,
        ) as file_read:
            sized = self.Attachment.with_context(bin_size=True).browse((even + odd).ids)
            reported = [(record.datas, record.raw) for record in sized]
            self.assertEqual(
                file_read.call_count, 0, "bin_size read the content it exists to skip"
            )

        for (datas, raw), record in zip(reported, even + odd, strict=True):
            expected = human_size(record.file_size).encode()
            self.assertEqual(datas, expected)
            self.assertEqual(raw, expected, "raw was sized as base64")

    def test_db_datas_create_goes_through_the_content_pipeline(self):
        payload = b"inline,payload\n1,2\n"
        attachment = self.Attachment.create(
            {"name": "inline.csv", "db_datas": payload, "mimetype": "text/csv"}
        )
        attachment.flush_recordset()
        self.addCleanup(
            Path(self.filestore, attachment.store_fname).unlink, missing_ok=True
        )
        self.assertEqual(attachment.raw, payload)
        self.assertEqual(attachment.file_size, len(payload))
        self.assertEqual(
            attachment.checksum, self.Attachment._get_content_checksum(payload)
        )
        self.assertTrue(attachment.index_content)
        self.assertTrue(
            attachment.store_fname,
            "db_datas must honour ir_attachment.location, not force the column",
        )
        self.assertFalse(attachment.db_datas)
        self.assertEqual(attachment._to_http_stream().etag, attachment.checksum)

    def test_db_datas_write_replaces_the_content(self):
        attachment = self.Attachment.create(
            {"name": "r.txt", "raw": b"original", "mimetype": "text/plain"}
        )
        attachment.flush_recordset()
        first_fname = attachment.store_fname
        self.addCleanup(Path(self.filestore, first_fname).unlink, missing_ok=True)

        attachment.write({"db_datas": b"replacement"})
        attachment.flush_recordset()
        self.addCleanup(
            Path(self.filestore, attachment.store_fname).unlink, missing_ok=True
        )
        self.env.invalidate_all()
        attachment = self.Attachment.browse(attachment.id)

        self.assertEqual(attachment.raw, b"replacement")
        self.assertEqual(attachment.file_size, len(b"replacement"))
        self.assertEqual(
            attachment.checksum, self.Attachment._get_content_checksum(b"replacement")
        )
        self.env.cr.execute(
            "SELECT db_datas FROM ir_attachment WHERE id = %s", [attachment.id]
        )
        self.assertFalse(
            self.env.cr.fetchone()[0],
            "the replaced content must not survive as a dead inline copy",
        )

    def test_copying_a_keyed_row_carries_no_inline_column(self):
        attachment = self.Attachment.create({"name": "src.bin", "raw": self.blob1})
        attachment.flush_recordset()
        self.addCleanup(
            Path(self.filestore, attachment.store_fname).unlink, missing_ok=True
        )
        self.assertNotIn("db_datas", attachment.copy_data()[0])
        _vals, has_content = self.Attachment._normalize_content_vals(
            {"db_datas": False}
        )
        self.assertFalse(
            has_content,
            "a falsy db_datas from any source must not read as empty content",
        )
        self.assertEqual(attachment.copy().raw, self.blob1)

    def test_copy_reapplies_the_derived_columns_it_never_carries(self):
        attachment = self.Attachment.create({"name": "src.bin", "raw": self.blob1})
        attachment.flush_recordset()
        self.addCleanup(
            Path(self.filestore, attachment.store_fname).unlink, missing_ok=True
        )

        vals = attachment.copy_data()[0]
        for field in ("store_fname", "checksum", "file_size", "index_content"):
            self.assertNotIn(field, vals)

        copied = attachment.copy()
        self.assertEqual(copied.store_fname, attachment.store_fname)
        self.assertEqual(copied.checksum, attachment.checksum)
        self.assertEqual(copied.file_size, attachment.file_size)
        self.assertEqual(copied.index_content, attachment.index_content)
        self.assertEqual(copied.raw, self.blob1)

    def test_copying_an_inline_row_keeps_its_index_without_extracting(self):
        self.env["ir.config_parameter"].set_param("ir_attachment.location", "db")
        rows = self.Attachment.create(
            [
                {"name": f"n{i}.txt", "raw": f"alpha bravo {i}".encode()}
                for i in range(3)
            ]
        )
        self.assertFalse(rows[0].store_fname)
        self.assertIn("bravo", rows[1].index_content)
        with patch.object(
            self.registry["ir.attachment"],
            "_extract_index_content",
            side_effect=AssertionError("a copy must not extract again"),
        ):
            copies = rows.copy()
        for origin, copied in zip(rows, copies, strict=True):
            self.assertEqual(copied.index_content, origin.index_content)
            self.assertEqual(copied.checksum, origin.checksum)
            self.assertEqual(copied.raw, origin.raw)
        self.assertNotIn("attachment_index_from_origin", copies.env.context)

    def test_streamed_create_honours_the_index_hook(self):
        vals = self.Attachment._prepare_generated_asset_vals(
            name="web.assets_web.min.js",
            mimetype="text/javascript",
            raw=b"",
            url="/web/assets/abc123/web.assets_web.min.js",
        )
        vals.pop("raw")
        with patch.object(
            self.registry["ir.attachment"],
            "_extract_index_content",
            side_effect=AssertionError("a compiled bundle must not be indexed"),
        ):
            streamed = self.Attachment.sudo()._create_from_stream(
                io.BytesIO(b"function f(){return 1}" * 100), **vals
            )
        self.addCleanup(
            Path(self.filestore, streamed.store_fname).unlink, missing_ok=True
        )
        self.assertFalse(streamed.index_content)
        self.assertTrue(streamed.file_size)

    def test_copying_a_legacy_dual_row_writes_no_new_content(self):
        attachment = self.Attachment.create({"name": "dual.bin", "raw": self.blob1})
        attachment.flush_recordset()
        self.addCleanup(
            Path(self.filestore, attachment.store_fname).unlink, missing_ok=True
        )
        self.env.cr.execute(
            "UPDATE ir_attachment SET db_datas = %s WHERE id = %s",
            [b"stale-inline-bytes", attachment.id],
        )
        attachment.invalidate_recordset()
        self.assertTrue(attachment.db_datas)

        stale_key = self.Attachment._get_store_key(
            self.Attachment._get_content_checksum(b"stale-inline-bytes")
        )
        copied = attachment.copy()
        self.env.flush_all()

        self.assertEqual(copied.raw, self.blob1)
        self.assertEqual(copied.store_fname, attachment.store_fname)
        self.assertFalse(
            Path(self.filestore, stale_key).is_file(),
            "the copy wrote the origin's dead inline bytes to the filestore",
        )

    def test_08_neuter_xml_mimetype(self):
        Attachment = self.Attachment.with_user(self.user_demo.id)
        document = Attachment.create({"name": "document", "datas": self.blob1_b64})
        document.write({"datas": self.blob1_b64, "mimetype": "text/xml"})
        self.assertEqual(
            document.mimetype,
            "text/plain",
            "XML mimetype should be forced to text",
        )
        document.write({"datas": self.blob1_b64, "mimetype": "image/svg+xml"})
        self.assertEqual(
            document.mimetype,
            "text/plain",
            "SVG mimetype should be forced to text",
        )
        document.write({"datas": self.blob1_b64, "mimetype": "text/html"})
        self.assertEqual(
            document.mimetype,
            "text/plain",
            "HTML mimetype should be forced to text",
        )
        document.write({"datas": self.blob1_b64, "mimetype": "application/xhtml+xml"})
        self.assertEqual(
            document.mimetype,
            "text/plain",
            "XHTML mimetype should be forced to text",
        )

    def test_09_dont_neuter_xml_mimetype_for_admin(self):
        document = self.Attachment.create({"name": "document", "datas": self.blob1_b64})
        document.write({"datas": self.blob1_b64, "mimetype": "text/xml"})
        self.assertEqual(
            document.mimetype,
            "text/xml",
            "XML mimetype should not be forced to text, for admin user",
        )

    def test_10_image_autoresize(self):
        Attachment = self.env["ir.attachment"]
        img_bin = io.BytesIO()
        dir_path = Path(__file__).resolve().parent
        with Image.open(str(Path(dir_path, "odoo.jpg")), "r") as logo:
            img = Image.new("RGB", (4000, 2000), "#4169E1")
            img.paste(logo)
            img.save(img_bin, "JPEG")

        img_encoded = image_to_base64(img, "JPEG")
        img_bin = img_bin.getvalue()

        fullsize = 124.99

        attach = Attachment.with_context(image_no_postprocess=True).create(
            {
                "name": "image",
                "datas": img_encoded,
            }
        )
        self.assertApproximately(attach.datas, fullsize)

        attach = attach.with_context(image_no_postprocess=False)
        attach.datas = img_encoded
        self.assertApproximately(attach.datas, 12.06)

        self.env["ir.config_parameter"].set_param(
            "base.image_autoresize_max_px", "1024x768"
        )
        attach.datas = img_encoded
        self.assertApproximately(attach.datas, 3.71)

        self.env["ir.config_parameter"].set_param("base.image_autoresize_quality", "50")
        attach.datas = img_encoded
        self.assertApproximately(attach.datas, 3.57)

        self.env["ir.config_parameter"].set_param("base.image_autoresize_max_px", "0")
        attach.datas = img_encoded
        self.assertApproximately(attach.datas, fullsize)

        self.env["ir.config_parameter"].set_param(
            "base.image_autoresize_max_px", "10000x10000"
        )
        self.env["ir.config_parameter"].set_param("base.image_autoresize_quality", "50")
        attach.datas = img_encoded
        self.assertApproximately(attach.datas, fullsize)

        self.env["ir.config_parameter"].search(
            [("key", "ilike", "base.image_autoresize%")]
        ).unlink()

        attach = Attachment.with_context(image_no_postprocess=True).create(
            {
                "name": "image",
                "raw": img_bin,
            }
        )
        self.assertApproximately(attach.raw, fullsize)

        attach = attach.with_context(image_no_postprocess=False)
        attach.raw = img_bin
        self.assertApproximately(attach.raw, 12.06)

        self.env["ir.config_parameter"].set_param(
            "base.image_autoresize_max_px", "1024x768"
        )
        attach.raw = img_bin
        self.assertApproximately(attach.raw, 3.71)

        self.env["ir.config_parameter"].set_param("base.image_autoresize_quality", "0")
        attach.raw = img_bin
        self.assertApproximately(attach.raw, 4.09)

        self.env["ir.config_parameter"].set_param("base.image_autoresize_quality", "50")
        attach.raw = img_bin
        self.assertApproximately(attach.raw, 3.57)

        self.env["ir.config_parameter"].set_param("base.image_autoresize_max_px", "0")
        attach.raw = img_bin
        self.assertApproximately(attach.raw, fullsize)

        self.env["ir.config_parameter"].set_param("base.image_autoresize_max_px", "0x0")
        gif_bin = b"GIF89a\x01\x00\x01\x00\x00\xff\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x00;"
        attach.raw = gif_bin
        self.assertEqual(attach.raw, gif_bin)

    def test_11_copy(self):
        document = self.Attachment.create({"name": "document", "datas": self.blob2_b64})
        document2 = document.copy({"name": "document (copy)"})
        self.assertEqual(document2.name, "document (copy)")
        self.assertEqual(document2.datas, document.datas)
        self.assertEqual(document2.db_datas, document.db_datas)
        self.assertEqual(document2.store_fname, document.store_fname)
        self.assertEqual(document2.checksum, document.checksum)

        document3 = document.copy({"datas": self.blob1_b64})
        self.assertEqual(document3.datas, self.blob1_b64)
        self.assertEqual(document3.raw, self.blob1)
        self.assertTrue(document3.store_fname)
        self.assertEqual(document3.db_datas, False)
        self.assertEqual(document3.store_fname, self.blob1_fname)
        self.assertEqual(document3.checksum, self.blob1_hash)

    def test_12_gc(self):
        self.patch(IrAttachment, "_GC_CHECKLIST_GRACE", 0)
        unique_blob = os.urandom(16)
        a1 = self.Attachment.create({"name": "a1", "raw": unique_blob})
        store_path = Path(self.filestore, a1.store_fname)
        self.assertTrue(store_path.is_file(), "file exists")
        a1.unlink()
        self.Attachment._gc_file_store_unsafe()
        self.assertFalse(store_path.is_file(), "file removed")

    def test_13_rollback(self):
        self.patch(IrAttachment, "_GC_CHECKLIST_GRACE", 0)
        unique_blob = os.urandom(16)
        with contextlib.closing(self.cr.savepoint()):
            a1 = self.env["ir.attachment"].create({"name": "a1", "raw": unique_blob})
            store_path = Path(self.filestore, a1.store_fname)
            self.assertTrue(store_path.is_file(), "file exists")
        self.env["ir.attachment"]._gc_file_store_unsafe()
        self.assertFalse(store_path.is_file(), "file removed")

    def test_gc_prewalked_checklist(self):
        self.patch(IrAttachment, "_GC_CHECKLIST_GRACE", 0)
        Attachment = self.env["ir.attachment"]
        orphan = Attachment.create({"name": "orphan", "raw": os.urandom(16)})
        kept = Attachment.create({"name": "kept", "raw": os.urandom(16)})
        orphan_fname = orphan.store_fname
        kept_fname = kept.store_fname
        orphan_path = Path(self.filestore, orphan_fname)
        kept_path = Path(self.filestore, kept_fname)

        orphan.unlink()
        Attachment._mark_for_gc(kept_fname)
        Attachment.flush_recordset(["store_fname"])

        checklist = Attachment._get_gc_checklist()
        self.assertIn(orphan_fname, checklist)
        self.assertIn(kept_fname, checklist)

        Attachment._gc_file_store_unsafe(checklist)
        self.assertFalse(orphan_path.is_file(), "orphan file must be collected")
        self.assertTrue(kept_path.is_file(), "referenced file must be spared")

    def _checklist_marker(self, fname):
        return Path(self.filestore, "checklist", fname)

    def _age_marker(self, fname, age_seconds):
        marker = self._checklist_marker(fname)
        past = marker.stat().st_mtime - age_seconds
        os.utime(marker, (past, past))

    def test_gc_grace_spares_fresh_markers(self):
        unique_blob = os.urandom(16)
        a1 = self.Attachment.create({"name": "a1", "raw": unique_blob})
        fname = a1.store_fname
        store_path = Path(self.filestore, fname)
        a1.unlink()

        checklist = self.Attachment._get_gc_checklist()
        self.assertNotIn(fname, checklist, "fresh marker must be grace-skipped")
        self.Attachment._gc_file_store_unsafe()
        self.assertTrue(store_path.is_file(), "file within grace must survive")
        self.assertTrue(
            self._checklist_marker(fname).is_file(),
            "marker within grace must stay for a later run",
        )

        self._age_marker(fname, IrAttachment._GC_CHECKLIST_GRACE + 60)
        checklist = self.Attachment._get_gc_checklist()
        self.assertIn(fname, checklist, "aged marker must be sweepable")
        self.Attachment._gc_file_store_unsafe()
        self.assertFalse(store_path.is_file(), "aged orphan must be collected")
        self.assertFalse(self._checklist_marker(fname).is_file())

    def test_gc_grace_remark_refreshes_clock(self):
        unique_blob = os.urandom(16)
        checksum = self.Attachment._get_content_checksum(unique_blob)

        fname = self.Attachment._write_file(unique_blob, checksum)
        self._age_marker(fname, IrAttachment._GC_CHECKLIST_GRACE + 60)
        self.assertIn(fname, self.Attachment._get_gc_checklist())

        self.assertEqual(self.Attachment._write_file(unique_blob, checksum), fname)
        self.assertNotIn(
            fname,
            self.Attachment._get_gc_checklist(),
            "_write_file dedup hit must refresh the marker's grace clock",
        )

        self._age_marker(fname, IrAttachment._GC_CHECKLIST_GRACE + 60)
        self.assertIn(fname, self.Attachment._get_gc_checklist())
        stream_fname, size, stream_checksum = self.Attachment._write_file_stream(
            io.BytesIO(unique_blob)
        )
        self.assertEqual((stream_fname, size, stream_checksum), (fname, 16, checksum))
        self.assertNotIn(
            fname,
            self.Attachment._get_gc_checklist(),
            "_write_file_stream dedup hit must refresh the marker's grace clock",
        )

    def test_gc_sweep_restats_marker_before_unlink(self):
        a1 = self.Attachment.create({"name": "restat", "raw": os.urandom(16)})
        fname = a1.store_fname
        store_path = Path(self.filestore, fname)
        a1.unlink()

        self._age_marker(fname, IrAttachment._GC_CHECKLIST_GRACE + 60)
        checklist = self.Attachment._get_gc_checklist()
        self.assertIn(fname, checklist)

        os.utime(self._checklist_marker(fname), None)
        self.assertTrue(store_path.is_file())

        self.Attachment._gc_file_store_unsafe(checklist)
        self.assertTrue(
            store_path.is_file(),
            "a file whose marker was refreshed after the scan must be spared",
        )

    def test_gc_sweep_flushes_before_reading_the_whitelist(self):
        att = self.Attachment.create({"name": "unflushed", "raw": os.urandom(16)})
        first = att.store_fname
        self.env.flush_all()
        att.write({"raw": os.urandom(16)})
        fname = att.store_fname
        self.assertNotEqual(fname, first)
        store_path = Path(self.filestore, fname)
        self.addCleanup(store_path.unlink, missing_ok=True)
        self.assertTrue(store_path.is_file())

        self.Attachment._gc_file_store_unsafe(
            {fname: self._checklist_marker(fname)}, grace=0
        )
        self.assertTrue(
            store_path.is_file(),
            "a store key assigned in this transaction is referenced, flushed or not",
        )

    def test_prefix_read_of_zero_bytes_is_not_unreadable(self):
        att = self.Attachment.create({"name": "head", "raw": b"0123456789"})
        self.addCleanup(Path(self.filestore, att.store_fname).unlink, missing_ok=True)
        with self.assertNoLogs("odoo.addons.base.models.ir_attachment", "ERROR"):
            self.assertEqual(att._get_content_prefix(0), b"")
            self.assertEqual(att._get_content_prefix(4), b"0123")

    def test_autoresize_config_disables_on_a_bad_or_false_resolution(self):
        icp = self.env["ir.config_parameter"]
        icp.set_param("base.image_autoresize_max_px", "1920x1920")
        subtypes, width, height, quality = (
            self.Attachment._get_image_autoresize_config()
        )
        self.assertEqual((width, height), (1920, 1920))
        self.assertIn("png", subtypes)
        self.assertTrue(quality)
        icp.set_param("base.image_autoresize_max_px", "False")
        self.assertEqual(self.Attachment._get_image_autoresize_config()[1:], (0, 0, 0))
        icp.set_param("base.image_autoresize_max_px", "wide")
        with self.assertLogs("odoo.addons.base.models.ir_attachment", "WARNING"):
            config = self.Attachment._get_image_autoresize_config()
        self.assertEqual(config[1:], (0, 0, 0), "a bad value disables, not crashes")

    def test_an_attachment_cannot_point_at_itself(self):
        attachment = self.Attachment.create({"name": "self", "raw": b"x"})
        self.addCleanup(
            Path(self.filestore, attachment.store_fname).unlink, missing_ok=True
        )
        with self.assertRaises(ValidationError):
            attachment.write({"res_model": "ir.attachment", "res_id": attachment.id})
        other = self.Attachment.create({"name": "other", "raw": b"y"})
        self.addCleanup(Path(self.filestore, other.store_fname).unlink, missing_ok=True)
        attachment.write({"res_model": "ir.attachment", "res_id": other.id})
        self.assertEqual(attachment.res_id, other.id)

    def test_condition_values_read_only_a_conjunctive_positive_term(self):
        get = ir_attachment_module._get_condition_values
        model = self.Attachment
        self.assertEqual(list(get(model, "res_id", Domain("res_id", "=", 7))), [7])
        self.assertEqual(
            sorted(get(model, "res_id", Domain("res_id", "in", [7, 8]))), [7, 8]
        )
        self.assertIsNone(
            get(model, "res_id", Domain("res_id", "not in", [7])),
            "a negative term bounds nothing",
        )
        self.assertIsNone(
            get(model, "res_id", Domain("res_id", "=", 7) | Domain("name", "=", "x")),
            "a term under OR bounds nothing",
        )
        self.assertEqual(
            list(
                get(
                    model,
                    "res_id",
                    Domain("res_id", "=", 7) & Domain("name", "=", "x"),
                )
            ),
            [7],
        )

    def test_xml_like_covers_every_xml_subtype(self):
        forced = (
            "application/x-xml",
            "application/xml-dtd",
            "text/xml",
            "image/svg+xml",
            "text/html",
            "application/xhtml+xml",
            "application/hta",
        )
        for mimetype in forced:
            self.assertTrue(self.Attachment._is_xml_like_mimetype(mimetype), mimetype)
        kept = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "image/png",
            "text/plain",
        )
        for mimetype in kept:
            self.assertFalse(self.Attachment._is_xml_like_mimetype(mimetype), mimetype)

    def test_to_http_stream_ignores_bin_size(self):
        payload = b"X" * 5000
        self.env["ir.config_parameter"].set_param("ir_attachment.location", "db")
        in_db = self.Attachment.create({"name": "d.bin", "raw": payload})
        self.env["ir.config_parameter"].set_param("ir_attachment.location", "file")
        on_disk = self.Attachment.create({"name": "f.bin", "raw": payload})
        self.env.flush_all()
        self.addCleanup(
            Path(self.filestore, on_disk.store_fname).unlink, missing_ok=True
        )
        self.assertFalse(in_db.store_fname)
        self.assertTrue(on_disk.store_fname)

        sized_stream = in_db.with_context(bin_size=True)._to_http_stream()
        self.assertEqual(sized_stream.data, payload)
        self.assertEqual(sized_stream.size, len(payload))

        self.assertEqual(
            on_disk.with_context(bin_size=True)._to_http_stream().size, len(payload)
        )
        self.assertEqual(
            in_db.with_context(bin_size=True).file_size,
            len(payload),
            "bin_size still reports the size where it is asked for it",
        )

    def test_both_search_paths_agree_on_a_non_binary_res_field(self):
        partner = self.env["res.partner"].sudo().create({"name": "IRA-D5"})
        att = self.Attachment.sudo().create(
            {
                "name": "odd-res-field",
                "raw": b"x",
                "mimetype": "text/plain",
                "res_model": "res.partner",
                "res_id": partner.id,
            }
        )
        self.addCleanup(Path(self.filestore, att.store_fname).unlink, missing_ok=True)
        att.flush_recordset()
        self.env.cr.execute(
            "UPDATE ir_attachment SET res_field = 'comment' WHERE id = %s", [att.id]
        )
        att.invalidate_recordset()
        self.env.flush_all()

        Att = self.Attachment.with_user(self.user_demo).with_context(
            skip_res_field_check=True
        )
        wide = [
            "res.partner",
            "res.currency",
            "res.company",
            "res.country",
            "res.users",
            "res.bank",
        ]
        self.assertGreater(
            len(wide),
            self.Attachment._SEARCH_MODEL_DOMAIN_LIMIT,
            "precondition: the wide domain must take the batched access path",
        )
        one_model = Att.search([("res_model", "=", "res.partner")])
        many_models = Att.search([("res_model", "in", wide)])
        allowed = bool(Att.browse(att.id)._filtered_access("read"))

        self.assertEqual(
            att.id in one_model.ids,
            allowed,
            "per-model domain path disagrees with _check_access",
        )
        self.assertEqual(
            att.id in many_models.ids,
            allowed,
            "batched access path disagrees with _check_access",
        )

    def test_res_field_must_name_an_attachment_backed_field(self):
        partner = self.env["res.partner"].sudo().create({"name": "IRA-D7"})
        base = {
            "name": "backed",
            "raw": b"x",
            "mimetype": "text/plain",
            "res_model": "res.partner",
            "res_id": partner.id,
        }
        for field_name in ("comment", "name", "active"):
            with self.subTest(field=field_name), self.assertRaises(ValidationError):
                self.Attachment.sudo().create(base | {"res_field": field_name})

        for field_name in ("image_1920", "avatar_128"):
            with self.subTest(field=field_name):
                att = self.Attachment.sudo().create(base | {"res_field": field_name})
                att.flush_recordset()
                self.addCleanup(
                    Path(self.filestore, att.store_fname).unlink, missing_ok=True
                )
                self.assertEqual(att.res_field, field_name)

        ok = self.Attachment.sudo().create(base)
        ok.flush_recordset()
        self.addCleanup(Path(self.filestore, ok.store_fname).unlink, missing_ok=True)
        with self.assertRaises(ValidationError):
            ok.write({"res_field": "comment"})

        unknown = self.Attachment.sudo().create(
            base | {"res_model": "x.gone", "res_field": "whatever"}
        )
        unknown.flush_recordset()
        self.addCleanup(
            Path(self.filestore, unknown.store_fname).unlink, missing_ok=True
        )
        self.assertEqual(
            unknown.res_field,
            "whatever",
            "an unresolvable model must stay writable for uninstall paths",
        )

    def test_full_path_confines_every_input_to_the_filestore(self):
        root = Path(self.filestore).resolve()
        for path in (
            "../../etc/passwd",
            "/etc/passwd",
            "..",
            "....//....//etc",
            "a/../../b",
            "tmp",
            "checklist",
            self.blob1_fname,
        ):
            resolved = Path(self.Attachment._get_full_path(path))
            self.assertTrue(
                resolved == root or root in resolved.parents,
                f"{path!r} escaped the filestore as {resolved}",
            )

        self.patch(IrAttachment, "_normalize_store_key", lambda self, path: path)
        with self.assertRaises(ValueError):
            self.Attachment._get_full_path("../../etc/passwd")
        with self.assertRaises(ValueError):
            self.Attachment._get_full_path("/etc/passwd")

    def test_full_path_refuses_a_symlink_out_of_the_filestore(self):
        outside = Path(self.filestore).parent / f"outside-{os.urandom(6).hex()}.txt"
        outside.write_bytes(b"outside the filestore")
        self.addCleanup(outside.unlink, missing_ok=True)

        shard = Path(self.filestore, "zz")
        shard.mkdir(parents=True, exist_ok=True)
        self.addCleanup(shard.rmdir)
        link = shard / ("f" * 40)
        link.unlink(missing_ok=True)
        link.symlink_to(outside)
        self.addCleanup(link.unlink, missing_ok=True)

        key = f"zz/{'f' * 40}"
        with self.assertRaises(ValueError):
            self.Attachment._get_full_path(key)
        with mute_logger("odoo.addons.base.models.ir_attachment"):
            self.assertEqual(
                self.Attachment._read_file(key),
                b"",
                "content outside the filestore was served through a symlinked key",
            )

    def test_fixed_subdirs_resolve_to_the_same_place_as_full_path(self):
        for name in ("tmp", "checklist"):
            self.assertEqual(
                str(self.Attachment._get_filestore_dir(name)),
                self.Attachment._get_full_path(name),
            )

    def test_14_invalid_mimetype_with_correct_file_extension_no_post_processing(
        self,
    ):
        unique_blob = b'<svg xmlns="http://www.w3.org/2000/svg"></svg>'
        a1 = self.Attachment.create(
            {"name": "a1", "raw": unique_blob, "mimetype": "image/png"}
        )
        self.assertEqual(a1.raw, unique_blob)
        self.assertEqual(a1.mimetype, "image/png")

    def test_15_read_bin_size_doesnt_read_datas(self):
        self.env.invalidate_all()
        IrAttachment = self.registry["ir.attachment"]
        main_partner = self.env.ref("base.main_partner")
        with patch.object(
            IrAttachment,
            "_read_file",
            side_effect=IrAttachment._read_file,
            autospec=True,
        ) as patch_file_read:
            self.env["res.partner"].with_context(bin_size=True).search_read(
                [("id", "in", main_partner.ids)], ["image_128"]
            )
            self.assertEqual(patch_file_read.call_count, 0)

    def test_read_prefix_filestore_and_db(self):
        on_disk = self.Attachment.create({"name": "a1", "raw": self.blob1})
        self.assertTrue(on_disk.store_fname)
        self.assertEqual(on_disk._get_content_prefix(3), self.blob1[:3])
        self.assertEqual(on_disk._get_content_prefix(), self.blob1)

        self.env["ir.config_parameter"].set_param("ir_attachment.location", "db")
        in_db = self.Attachment.create({"name": "a2", "raw": self.blob2})
        self.assertFalse(in_db.store_fname)
        self.assertEqual(in_db._get_content_prefix(3), self.blob2[:3])
        self.assertEqual(in_db._get_content_prefix(), self.blob2)

    def test_read_prefix_ignores_bin_size(self):
        self.env["ir.config_parameter"].set_param("ir_attachment.location", "db")
        in_db = self.Attachment.create({"name": "a1", "raw": self.blob1})
        self.env.invalidate_all()
        sized = in_db.with_context(bin_size=True)
        self.assertNotEqual(sized.db_datas, self.blob1)
        self.assertEqual(sized._get_content_prefix(), self.blob1)
        self.assertEqual(sized._get_content_prefix(3), self.blob1[:3])

    def test_read_prefix_without_content(self):
        bare = self.Attachment.create({"name": "a1", "type": "binary"})
        self.assertEqual(bare._get_content_prefix(10), b"")

    def test_create_unique_invalid_base64(self):
        from odoo.exceptions import UserError

        with self.assertRaises(UserError) as cm:
            self.Attachment.create_unique(
                [
                    {
                        "name": "bad.txt",
                        "datas": "NOT_VALID_BASE64!!!",
                        "mimetype": "text/plain",
                    }
                ]
            )
        self.assertIsNotNone(
            cm.exception.__cause__, "Exception chain should be preserved"
        )

    def test_create_unique_dedup(self):
        data = base64.b64encode(b"hello dedup").decode()
        ids = self.Attachment.create_unique(
            [
                {"name": "a.txt", "datas": data, "mimetype": "text/plain"},
                {"name": "b.txt", "datas": data, "mimetype": "text/plain"},
            ]
        )
        self.assertEqual(len(ids), 2)
        self.assertEqual(ids[0], ids[1], "Same content should deduplicate")

    def test_create_unique_contentless_matches_create(self):
        created = self.Attachment.create({"name": "bare", "mimetype": "text/plain"})
        ids = self.Attachment.create_unique(
            [
                {"name": "bare-a", "mimetype": "text/plain"},
                {"name": "bare-b", "mimetype": "text/plain"},
            ]
        )
        uniques = self.Attachment.browse(ids)
        self.assertEqual(
            uniques.mapped("checksum"),
            [created.checksum, created.checksum],
            "a content-less value must not be stamped with the digest of b''",
        )
        self.assertNotEqual(
            ids[0], ids[1], "content-less values have nothing to deduplicate on"
        )
        self.assertEqual(uniques.mapped("name"), ["bare-a", "bare-b"])

    def test_create_unique_treats_db_datas_as_content(self):
        vals = {"name": "hatch", "mimetype": "text/plain", "db_datas": b"hand-written"}
        created = self.Attachment.create(dict(vals))
        [unique_id] = self.Attachment.create_unique([dict(vals)])
        self.assertEqual(created.raw, b"hand-written")
        self.assertEqual(
            created.checksum, self.Attachment._get_content_checksum(b"hand-written")
        )
        self.assertEqual(created.file_size, len(b"hand-written"))
        self.assertEqual(
            unique_id,
            created.id,
            "create_unique must dedup a db_datas value against an identical row",
        )

    def test_create_unique_does_not_mutate_caller_values(self):
        values = {
            "name": "keep.txt",
            "mimetype": "text/plain",
            "datas": base64.b64encode(b"payload").decode(),
        }
        self.Attachment.create_unique([values])
        self.assertIn("datas", values, "the caller's dict must not be mutated")

    def _make_other_company_user(self):
        company_b = self.env["res.company"].sudo().create({"name": "IRA-C2 B"})
        return (
            self.env["res.users"]
            .sudo()
            .create(
                {
                    "name": "ira-c2",
                    "login": "ira_c2_b",
                    "company_id": company_b.id,
                    "company_ids": [(6, 0, [company_b.id])],
                    "group_ids": [
                        (
                            6,
                            0,
                            [
                                self.env.ref("base.group_user").id,
                                self.env.ref("base.group_partner_manager").id,
                            ],
                        )
                    ],
                }
            )
        )

    def test_create_unique_dedups_a_cross_company_row_on_a_writable_record(self):
        user_b = self._make_other_company_user()
        payload = b"ira-c2-shared-" + os.urandom(8)
        target = self.env["res.partner"].sudo().create({"name": "ira-c2 target"})
        seeded = self.Attachment.sudo().create(
            {
                "name": "seed",
                "mimetype": "text/plain",
                "raw": payload,
                "res_model": "res.partner",
                "res_id": target.id,
                "company_id": self.env.company.id,
            }
        )
        self.env.flush_all()
        self.assertNotEqual(
            seeded.company_id,
            user_b.company_id,
            "precondition: the seeded row belongs to another company",
        )
        dedup_ids = self.Attachment.with_user(user_b).create_unique(
            [
                {
                    "name": "dup",
                    "mimetype": "text/plain",
                    "raw": payload,
                    "res_model": "res.partner",
                    "res_id": target.id,
                    "company_id": user_b.company_id.id,
                }
            ]
        )
        self.assertEqual(
            dedup_ids,
            [seeded.id],
            "dedup reuses the cross-company row instead of duplicating the file",
        )

    def test_create_unique_refuses_a_record_the_caller_cannot_write(self):
        user_b = self._make_other_company_user()
        parameter = self.env["ir.config_parameter"].search([], limit=1)
        with self.assertRaises(AccessError):
            self.Attachment.with_user(user_b).create_unique(
                [
                    {
                        "name": "dup",
                        "mimetype": "text/plain",
                        "raw": b"ira-c2-unwritable-" + os.urandom(8),
                        "res_model": "ir.config_parameter",
                        "res_id": parameter.id,
                    }
                ]
            )

    def test_create_unique_never_returns_another_users_private_row(self):
        user_b = self._make_other_company_user()
        payload = b"ira-private-" + os.urandom(8)
        private = self.Attachment.with_user(self.user_demo).create(
            {"name": "mine", "mimetype": "text/plain", "raw": payload}
        )
        self.env.flush_all()
        self.assertFalse(private.res_model)
        self.assertFalse(private.res_id)

        [dedup_id] = self.Attachment.with_user(user_b).create_unique(
            [{"name": "theirs", "mimetype": "text/plain", "raw": payload}]
        )
        self.assertNotEqual(dedup_id, private.id, "a private row of another user")
        self.assertEqual(
            self.Attachment.with_user(user_b).browse(dedup_id).raw,
            payload,
            "create_unique must hand back a row its caller can read",
        )
        [again] = self.Attachment.with_user(user_b).create_unique(
            [{"name": "theirs", "mimetype": "text/plain", "raw": payload}]
        )
        self.assertEqual(again, dedup_id, "the caller's own private row still dedups")
        [as_system] = self.Attachment.create_unique(
            [{"name": "sys", "mimetype": "text/plain", "raw": payload}]
        )
        self.assertIn(
            as_system,
            (private.id, dedup_id),
            "a system user still dedups across every unattached row",
        )

    def test_a_short_file_at_the_key_is_replaced_not_adopted(self):
        self.env["ir.config_parameter"].set_param("ir_attachment.location", "file")
        self.env["ir.config_parameter"].set_param(
            "ir_attachment.verify_content_collision", "False"
        )
        payload = b"full-payload-" + os.urandom(64)
        fname = self.Attachment._get_store_key(
            self.Attachment._get_content_checksum(payload)
        )
        full_path = Path(self.Attachment._get_full_path(fname))
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(b"short")
        self.addCleanup(full_path.unlink, missing_ok=True)

        att = self.Attachment.create({"name": "planted", "raw": payload})
        self.assertEqual(att.store_fname, fname)
        self.assertEqual(full_path.stat().st_size, len(payload))
        self.assertEqual(att.raw, payload)

        full_path.write_bytes(b"short")
        stream_fname, size, _checksum = self.Attachment._write_file_stream(
            io.BytesIO(payload)
        )
        self.assertEqual(stream_fname, fname)
        self.assertEqual(size, len(payload))
        self.assertEqual(full_path.read_bytes(), payload)

    @mute_logger("odoo.addons.base.models.ir_attachment")
    def test_create_unique_does_not_dedup_across_a_digest_collision(self):
        self.env["ir.config_parameter"].set_param(
            "ir_attachment.verify_content_collision", "True"
        )
        alpha = b"CONTENT-ALPHA" * 8
        bravo = b"CONTENT-BRAVO" * 8
        self.assertEqual(len(alpha), len(bravo), "a collision pair shares its length")

        real = type(self.Attachment)._get_content_checksum
        digest = "c0" * 20

        def colliding(model, data):
            return digest if data in (alpha, bravo) else real(model, data)

        with patch.object(type(self.Attachment), "_get_content_checksum", colliding):
            first = self.Attachment.create_unique(
                [
                    {
                        "name": "a.bin",
                        "mimetype": "application/octet-stream",
                        "raw": alpha,
                    }
                ]
            )
            self.env.flush_all()
            stored = self.Attachment.browse(first[0])
            self.addCleanup(
                Path(self.filestore, stored.store_fname).unlink, missing_ok=True
            )
            with self.assertRaises(UserError):
                self.Attachment.create_unique(
                    [
                        {
                            "name": "b.bin",
                            "mimetype": "application/octet-stream",
                            "raw": bravo,
                        }
                    ]
                )
        self.assertEqual(stored.raw, alpha, "the stored row must keep its own content")

    @mute_logger("odoo.addons.base.models.ir_attachment")
    def test_to_http_stream_missing_file(self):
        self.env["ir.config_parameter"].set_param("ir_attachment.location", "file")
        att = self.Attachment.create(
            {
                "name": "test.txt",
                "raw": b"test content",
            }
        )
        self.assertTrue(att.store_fname, "Attachment should be stored in filestore")

        full_path = att._get_full_path(att.store_fname)
        Path(full_path).unlink()

        from types import SimpleNamespace

        from odoo.http.core import _request_stack

        fake_request = SimpleNamespace(db=self.env.cr.dbname)
        _request_stack.push(fake_request)
        try:
            with patch("odoo.addons.base.models.ir_attachment.root"):
                stream = att._to_http_stream()
                self.assertEqual(stream.type, "data")
                self.assertEqual(stream.data, b"")
                self.assertEqual(stream.size, 0)
                self.assertIs(
                    stream.etag, False, "empty fallback must not keep the real ETag"
                )
                self.assertIsNone(stream.last_modified)
                self.assertFalse(
                    stream.conditional, "fallback must not serve conditionally"
                )
                self.assertFalse(stream.public, "fallback must not be proxy-cacheable")
        finally:
            _request_stack.pop()

    @mute_logger("odoo.addons.base.models.ir_attachment")
    def test_postprocess_bad_max_resolution(self):
        from PIL import Image as PILImage

        img = PILImage.new("RGB", (2000, 2000), color="red")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_data = buf.getvalue()

        for bad_val in ("1920", "abc", ""):
            self.env["ir.config_parameter"].set_param(
                "base.image_autoresize_max_px", bad_val
            )
            att = self.Attachment.create(
                {
                    "name": "test.png",
                    "raw": png_data,
                }
            )
            self.assertTrue(att.id)

    @mute_logger("odoo.addons.base.models.ir_attachment")
    def test_postprocess_bad_quality(self):
        img = Image.new("RGB", (64, 64), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        jpeg_data = buf.getvalue()

        self.env["ir.config_parameter"].set_param(
            "base.image_autoresize_max_px", "10x10"
        )
        for bad_val in ("notanint", "", "80%"):
            self.env["ir.config_parameter"].set_param(
                "base.image_autoresize_quality", bad_val
            )
            att = self.Attachment.create(
                {"name": "q.jpg", "raw": jpeg_data, "mimetype": "image/jpeg"}
            )
            self.assertTrue(att.id, f"upload must survive quality={bad_val!r}")

    @mute_logger("odoo.addons.base.models.ir_attachment")
    def test_to_http_stream_url_without_request(self):
        from odoo.http.core import _request_stack

        att = self.Attachment.create(
            {"name": "u", "type": "binary", "url": "/web/static/does-not-exist.png"}
        )
        att.db_datas = False
        self.assertFalse(_request_stack(), "test must run with no request bound")
        with patch("odoo.addons.base.models.ir_attachment.root") as mock_root:
            mock_root.get_static_file_path.return_value = None
            stream = att._to_http_stream()
        self.assertEqual(stream.type, "url")
        self.assertEqual(stream.url, att.url)
        self.assertEqual(
            mock_root.get_static_file_path.call_args.kwargs.get("host"), ""
        )

    def test_compute_res_name_orphaned_res_id(self):
        att = self.Attachment.create(
            {
                "name": "orphan",
                "raw": b"x",
                "res_model": "res.partner",
                "res_id": 2147483646,
            }
        )
        att.invalidate_recordset(["res_name"])
        self.assertFalse(att.res_name)

    def test_index_preserves_non_ascii_text(self):
        Att = self.env["ir.attachment"]
        spanish = "Configuración del módulo árbol genealógico".encode()
        indexed = Att._get_index_content(spanish, "text/plain")
        self.assertIn("Configuración", indexed)
        self.assertIn("módulo", indexed)
        self.assertIn("genealógico", indexed)
        self.assertIsNone(Att._get_index_content(b"\x89PNG\r\n", "image/png"))
        ascii_data = b"hello world\nshort\na\nplain ascii text here"
        self.assertEqual(
            Att._get_index_content(ascii_data, "text/plain"),
            "hello world\nshort\nplain ascii text here",
        )

    def test_create_from_stream_unreadable_readback_skips_index(self):
        payload = b"streamed text payload for indexation"
        ok = self.Attachment._create_from_stream(
            io.BytesIO(payload), name="ok.txt", mimetype="text/plain"
        )
        self.assertIn("streamed", ok.index_content)

        IrAttachmentCls = self.registry["ir.attachment"]
        with (
            patch.object(IrAttachmentCls, "_read_file", return_value=b""),
            patch.object(
                IrAttachmentCls,
                "_get_index_content",
                autospec=True,
                side_effect=IrAttachmentCls._get_index_content,
            ) as index_spy,
            self.assertLogs("odoo.addons.base.models.ir_attachment", "WARNING") as log,
        ):
            att = self.Attachment._create_from_stream(
                io.BytesIO(payload), name="s.txt", mimetype="text/plain"
            )
        self.assertEqual(index_spy.call_count, 0, "empty read-back must not be indexed")
        self.assertTrue(any("skipping index extraction" in line for line in log.output))
        self.assertFalse(att.index_content)
        self.assertEqual(att.file_size, len(payload))
        att.invalidate_recordset()
        self.assertEqual(att.raw, payload)

    def test_streamed_create_refuses_a_served_url_before_storing(self):
        Attachment = self.Attachment.with_user(self.user_demo)
        with (
            patch.object(
                self.registry["ir.attachment"],
                "_write_file_stream",
                side_effect=AssertionError("nothing must be stored"),
            ),
            self.assertRaises(ValidationError),
        ):
            Attachment._create_from_stream(
                io.BytesIO(b"served"), name="s.txt", mimetype="text/plain", url="/x"
            )

    def test_invalid_base64_datas_raises_user_error(self):
        bad = b"a"
        with self.assertRaises(UserError):
            self.Attachment.create({"name": "bad", "datas": bad})
        att = self.Attachment.create({"name": "ok", "raw": b"x"})
        with self.assertRaises(UserError):
            att.write({"datas": bad})
        with self.assertRaises(UserError):
            self.Attachment.create_unique(
                [{"name": "bad", "mimetype": "text/plain", "datas": bad}]
            )
        with self.assertRaises(UserError):
            self.Attachment._get_mimetype_from_values({"datas": bad})

    def test_content_derivation_memoized_within_batch(self):
        IrAttachmentCls = self.registry["ir.attachment"]
        payload = b"same text payload for every record in the batch"

        datas = base64.b64encode(payload)
        with patch.object(
            IrAttachmentCls,
            "_get_index_content",
            autospec=True,
            side_effect=IrAttachmentCls._get_index_content,
        ) as index_spy:
            atts = self.Attachment.create(
                [
                    {"name": f"c{i}.txt", "datas": datas, "mimetype": "text/plain"}
                    for i in range(3)
                ]
            )
        self.assertEqual(index_spy.call_count, 1, "create must derive the batch once")
        self.assertEqual(len(set(atts.mapped("store_fname"))), 1)
        for att in atts:
            self.assertEqual(att.raw, payload)
            self.assertIn("payload", att.index_content)

        rewritten = b"rewritten text payload shared by the whole batch"
        with patch.object(
            IrAttachmentCls,
            "_get_index_content",
            autospec=True,
            side_effect=IrAttachmentCls._get_index_content,
        ) as index_spy:
            atts.write({"raw": rewritten})
        self.assertEqual(index_spy.call_count, 1, "write must derive the batch once")
        atts.invalidate_recordset()
        for att in atts:
            self.assertEqual(att.raw, rewritten)
            self.assertIn("rewritten", att.index_content)

    def test_write_res_field_check_grouped_by_model(self):
        partner = self.env["res.partner"].create({"name": "grouped-check"})
        atts = self.Attachment.create(
            [
                {
                    "name": f"g{i}",
                    "raw": b"x",
                    "res_model": "res.partner",
                    "res_id": partner.id,
                }
                for i in range(3)
            ]
        )
        IrAttachmentCls = self.registry["ir.attachment"]
        with patch.object(
            IrAttachmentCls,
            "_check_res_field_access",
            autospec=True,
            side_effect=IrAttachmentCls._check_res_field_access,
        ) as spy:
            atts.write({"res_field": "image_1920"})
        self.assertEqual(spy.call_count, 1, "one ACL check per distinct res_model")
        self.assertEqual(set(atts.mapped("res_field")), {"image_1920"})

    def test_serving_check_on_content_write(self):
        att = self.Attachment.create(
            {"name": "asset", "type": "binary", "url": "/web/assets/x.js", "raw": b"v1"}
        )
        with patch.object(
            IrAttachment,
            "_check_serving_attachments",
            side_effect=IrAttachment._check_serving_attachments,
            autospec=True,
        ) as spy:
            att.write({"raw": b"v2"})
            self.assertGreaterEqual(spy.call_count, 1, "write({'raw'}) must re-check")
            spy.reset_mock()
            att.raw = b"v3"
            att.flush_recordset()
            self.assertGreaterEqual(spy.call_count, 1, "record.raw= must re-check")

    @mute_logger("odoo.addons.base.models.ir_attachment")
    def test_file_write_atomic_no_poison(self):
        self.env["ir.config_parameter"].set_param("ir_attachment.location", "file")
        payload = b"atomic-write-" + os.urandom(16)
        checksum = self.Attachment._get_content_checksum(payload)
        store_path = self.Attachment._get_store_key(checksum)
        target = Path(self.filestore, store_path)
        checklist = Path(self.filestore, "checklist", store_path)
        self.addCleanup(target.unlink, missing_ok=True)
        self.addCleanup(checklist.unlink, missing_ok=True)

        with patch("pathlib.Path.replace", side_effect=OSError("simulated crash")):
            with self.assertRaises(OSError):
                self.env["ir.attachment"]._write_file(payload, checksum)
        self.assertFalse(
            target.exists(), "no truncated file may remain at the real path"
        )
        tmp_dir = Path(self.filestore, "tmp")
        self.assertEqual(
            list(tmp_dir.glob("write-*")) if tmp_dir.is_dir() else [],
            [],
            "staging temp cleaned up on failure",
        )
        self.assertEqual(
            list(target.parent.glob(f"{checksum}.tmp-*")),
            [],
            "no temp file may be staged in the shard dir",
        )

        fname = self.env["ir.attachment"]._write_file(payload, checksum)
        self.assertEqual(self.env["ir.attachment"]._read_file(fname), payload)

    def test_file_write_stages_temp_in_tmp_dir(self):
        payload = b"tmp-staging-" + os.urandom(16)
        checksum = self.Attachment._get_content_checksum(payload)
        store_path = self.Attachment._get_store_key(checksum)
        target = Path(self.filestore, store_path)
        self.addCleanup(target.unlink, missing_ok=True)
        self.addCleanup(
            Path(self.filestore, "checklist", store_path).unlink,
            missing_ok=True,
        )
        tmp_dir = Path(self.filestore, "tmp")

        captured = {}
        orig_replace = Path.replace

        def capture(self, dst):
            captured["src_parent"] = self.parent
            return orig_replace(self, dst)

        with patch.object(Path, "replace", capture):
            self.env["ir.attachment"]._write_file(payload, checksum)
        self.assertEqual(
            captured.get("src_parent"),
            tmp_dir,
            "the staging temp must be created under the filestore tmp/ dir",
        )
        self.assertEqual(
            list(target.parent.glob(f"{checksum}.tmp-*")),
            [],
            "no temp may be staged in the shard dir",
        )

    def test_stale_temp_gc_removes_only_what_outlived_the_window(self):
        tmp_dir = self.Attachment._get_filestore_dir("tmp")
        tmp_dir.mkdir(parents=True, exist_ok=True)
        stale = tmp_dir / f"stale-{uuid.uuid4().hex}"
        fresh = tmp_dir / f"fresh-{uuid.uuid4().hex}"
        for path in (stale, fresh):
            path.write_bytes(b"staged")
            self.addCleanup(path.unlink, missing_ok=True)
        aged = time.time() - self.Attachment._FILESTORE_TMP_MAX_AGE - 60
        os.utime(stale, (aged, aged))

        self.Attachment._gc_stale_filestore_temps()

        self.assertFalse(stale.exists(), "a temp past the window must be collected")
        self.assertTrue(fresh.exists(), "a temp inside the window must be spared")

    def test_stale_temp_gc_survives_a_subdirectory(self):
        tmp_dir = self.Attachment._get_filestore_dir("tmp")
        tmp_dir.mkdir(parents=True, exist_ok=True)
        intruder = tmp_dir / f"dir-{uuid.uuid4().hex}"
        intruder.mkdir()
        self.addCleanup(intruder.rmdir)
        aged = time.time() - self.Attachment._FILESTORE_TMP_MAX_AGE - 60
        os.utime(intruder, (aged, aged))

        self.Attachment._gc_stale_filestore_temps()

        self.assertTrue(intruder.is_dir(), "the sweep must not touch a directory")

    def test_stale_temp_gc_is_a_noop_without_a_tmp_dir(self):
        absent = Path(self.filestore, f"absent-{uuid.uuid4().hex}")
        with patch.object(
            type(self.Attachment), "_get_filestore_dir", return_value=absent
        ):
            self.assertEqual(self.Attachment._gc_stale_filestore_temps(), (0, 0))
        self.assertFalse(absent.exists(), "the sweep must not create the tmp dir")

    def test_marking_for_gc_never_aborts_the_operation_it_bookkeeps(self):
        payload = b"gc-mark-failure-" + os.urandom(16)
        attachment = self.Attachment.create(
            {"name": "gcfail.txt", "raw": payload, "mimetype": "text/plain"}
        )
        self.env.flush_all()
        fname = attachment.store_fname
        self.addCleanup(Path(self.filestore, fname).unlink, missing_ok=True)

        checklist = self.Attachment._get_filestore_dir("checklist")
        checklist.mkdir(parents=True, exist_ok=True)
        shutil.rmtree(checklist / fname.split("/")[0], ignore_errors=True)
        mode = checklist.stat().st_mode
        checklist.chmod(0o500)
        self.addCleanup(checklist.chmod, mode)

        with self.assertLogs(
            "odoo.addons.base.models.ir_attachment", level="WARNING"
        ) as logs:
            attachment.unlink()
        checklist.chmod(mode)

        self.assertTrue(
            any("could not mark" in msg for msg in logs.output),
            f"an unmarkable file must be reported, got: {logs.output!r}",
        )
        self.assertFalse(
            attachment.exists(), "the unlink itself must still have gone through"
        )

    def test_index_stops_at_the_char_limit_instead_of_truncating_after(self):
        self.env["ir.config_parameter"].set_param(
            "ir_attachment.index_max_chars", "500"
        )
        blob = (b"the quick brown fox jumps over the lazy dog " * 4000)[: 128 * 1024]
        indexed = self.Attachment._get_index_content(blob, "text/plain")
        self.assertLessEqual(
            len(indexed),
            600,
            "the extraction must stop near the limit, not build the whole text",
        )
        self.assertGreater(len(indexed), 400, "it must still fill the budget")
        self.assertEqual(
            self.Attachment._extract_index_content(blob, "text/plain"),
            indexed,
            "the backstop truncation must agree with the bounded extraction",
        )

    def test_generated_asset_rows_carry_no_index(self):
        vals = self.Attachment._prepare_generated_asset_vals(
            name="web.assets_web.min.js",
            mimetype="text/javascript",
            raw=b"function f(){return 1}" * 100,
            url="/web/assets/abc123/web.assets_web.min.js",
        )
        with patch.object(
            type(self.Attachment),
            "_extract_index_content",
            side_effect=AssertionError("a compiled bundle must not be indexed"),
        ):
            attachment = self.Attachment.sudo().create(vals)
        self.assertFalse(attachment.index_content)
        self.assertTrue(attachment.public)
        plain = self.Attachment.create(
            {"name": "notes.txt", "mimetype": "text/plain", "raw": b"alpha bravo"}
        )
        self.assertIn("bravo", plain.index_content)
        self.assertIn(
            attachment,
            self.Attachment.sudo().search(
                self.Attachment._get_domain_generated_assets(vals["url"])
            ),
        )

    def test_index_honours_a_disabled_limit(self):
        self.env["ir.config_parameter"].set_param("ir_attachment.index_max_chars", "0")
        blob = b"alpha bravo charlie delta " * 500
        indexed = self.Attachment._get_index_content(blob, "text/plain")
        self.assertGreater(len(indexed), 10_000, "limit <= 0 means no bound")

    def test_a_digest_twin_in_one_batch_never_borrows_the_first_payload(self):
        self.env["ir.config_parameter"].set_param(
            "ir_attachment.verify_content_collision", "True"
        )
        alpha = b"CONTENT-ALPHA" * 8
        bravo = b"CONTENT-BRAVO" * 8
        self.assertEqual(len(alpha), len(bravo), "a collision pair shares its length")
        real = type(self.Attachment)._get_content_checksum
        digest = "c2" * 20

        def colliding(model, data):
            return digest if data in (alpha, bravo) else real(model, data)

        self.addCleanup(
            Path(self.filestore, self.Attachment._get_store_key(digest)).unlink,
            missing_ok=True,
        )
        with patch.object(type(self.Attachment), "_get_content_checksum", colliding):
            with self.assertRaises(UserError):
                self.Attachment.create(
                    [
                        {
                            "name": "a.bin",
                            "mimetype": "application/octet-stream",
                            "raw": alpha,
                        },
                        {
                            "name": "b.bin",
                            "mimetype": "application/octet-stream",
                            "raw": bravo,
                        },
                    ]
                )
            self.env.invalidate_all()
            with self.assertRaises(UserError):
                self.Attachment.create_unique(
                    [
                        {
                            "name": "a2.bin",
                            "mimetype": "application/octet-stream",
                            "raw": alpha,
                        },
                        {
                            "name": "b2.bin",
                            "mimetype": "application/octet-stream",
                            "raw": bravo,
                        },
                    ]
                )

    def test_identical_payloads_in_one_batch_still_derive_once(self):
        self.env["ir.config_parameter"].set_param(
            "ir_attachment.verify_content_collision", "True"
        )
        payload = b"shared payload under the guard"
        IrAttachmentCls = self.registry["ir.attachment"]
        with patch.object(
            IrAttachmentCls,
            "_get_index_content",
            autospec=True,
            side_effect=IrAttachmentCls._get_index_content,
        ) as index_spy:
            atts = self.Attachment.create(
                [
                    {"name": f"g{i}.txt", "raw": payload, "mimetype": "text/plain"}
                    for i in range(3)
                ]
            )
        self.assertEqual(index_spy.call_count, 1, "the guard must not defeat the memo")
        self.assertEqual(len(set(atts.mapped("store_fname"))), 1)

    def test_with_field_rows_owns_the_res_field_precondition(self):
        partner = self.env["res.partner"].create({"name": "field host"})
        field_row = self.Attachment.sudo().create(
            {
                "name": "image_1920",
                "res_model": "res.partner",
                "res_field": "image_1920",
                "res_id": partner.id,
                "raw": b"field-backed",
                "mimetype": "image/png",
            }
        )
        self.env.flush_all()
        domain = [("name", "=", "image_1920"), ("res_id", "=", partner.id)]
        self.assertFalse(
            self.Attachment.sudo().search(domain),
            "the default search hides a field-backed row",
        )
        self.assertEqual(
            self.Attachment.sudo()._with_field_rows().search(domain),
            field_row,
            "_with_field_rows must be the one way to lift that filter",
        )

    def test_full_path_returns_a_confined_absolute_path(self):
        root = str(Path(self.filestore).resolve())
        resolved = self.Attachment._get_full_path("b3/ab/" + "a" * 64)
        self.assertIsInstance(resolved, str)
        self.assertTrue(resolved.startswith(root + os.sep))
        self.assertEqual(
            self.Attachment._get_full_path(""), root, "an empty key is the root itself"
        )

    def test_file_write_single_get_path(self):
        self.env["ir.config_parameter"].set_param("ir_attachment.location", "file")
        unique = b"single-path-" + os.urandom(16)
        with patch.object(
            IrAttachment,
            "_prepare_file_destination",
            side_effect=IrAttachment._prepare_file_destination,
            autospec=True,
        ) as patched:
            att = self.Attachment.create({"name": "sp", "raw": unique})
            self.addCleanup(
                Path(self.filestore, att.store_fname).unlink, missing_ok=True
            )
        self.assertEqual(
            patched.call_count, 1, "exactly one _prepare_file_destination per write"
        )

    def test_stream_write_resolves_path_through_get_path(self):
        self.env["ir.config_parameter"].set_param("ir_attachment.location", "file")
        payload = b"stream-path-" + os.urandom(16)
        with patch.object(
            IrAttachment,
            "_prepare_file_destination",
            side_effect=IrAttachment._prepare_file_destination,
            autospec=True,
        ) as patched:
            fname, size, _checksum = self.Attachment._write_file_stream(
                io.BytesIO(payload)
            )
        self.addCleanup(Path(self.filestore, fname).unlink, missing_ok=True)
        self.assertEqual(
            patched.call_count,
            1,
            "exactly one _prepare_file_destination per stream write",
        )
        self.assertEqual(size, len(payload))
        self.assertEqual(self.Attachment._read_file(fname), payload)

    def test_stream_write_collision_unstages_temp(self):
        self.env["ir.config_parameter"].set_param(
            "ir_attachment.verify_content_collision", "True"
        )
        payload = b"stream-collide-" + os.urandom(16)
        checksum = self.Attachment._get_content_checksum(payload)
        planted = Path(self.filestore, self.Attachment._get_store_key(checksum))
        planted.parent.mkdir(parents=True, exist_ok=True)
        planted.write_bytes(b"different bytes entirely")
        self.addCleanup(planted.unlink, missing_ok=True)

        tmp_dir = Path(self.Attachment._get_full_path("tmp"))
        before = set(tmp_dir.iterdir()) if tmp_dir.is_dir() else set()
        with self.assertRaises(UserError):
            self.Attachment._write_file_stream(io.BytesIO(payload))
        after = set(tmp_dir.iterdir()) if tmp_dir.is_dir() else set()
        self.assertEqual(after, before, "the staged temp must be removed on failure")

    def test_empty_content_checksum_consistency(self):
        empty_sha = self.Attachment._get_content_checksum(b"")
        created = self.Attachment.create({"name": "empty", "raw": b""})
        self.assertEqual(created.checksum, empty_sha, "create must set empty checksum")
        self.assertEqual(created.file_size, 0)
        written = self.Attachment.create({"name": "x", "raw": b"data"})
        written.write({"raw": b""})
        self.assertEqual(written.checksum, empty_sha, "write path agrees")

    def test_audit_url_attachments_warns_on_suspicious(self):
        suspicious = self.Attachment.sudo().create(
            {
                "name": "probe.bin",
                "type": "binary",
                "url": "/suspicious/probe",
                "raw": b"x",
                "public": False,
            }
        )
        self.assertTrue(suspicious.id)

        with self.assertLogs(
            "odoo.addons.base.models.ir_attachment", level="WARNING"
        ) as logs:
            self.env["ir.attachment"]._audit_url_attachments()

        self.assertTrue(
            any("non-public binary attachment" in msg for msg in logs.output),
            f"expected audit warning, got: {logs.output!r}",
        )

    def test_audit_url_attachments_warns_once_per_row(self):
        self.Attachment.sudo().create(
            {
                "name": "probe-once.bin",
                "type": "binary",
                "url": "/suspicious/probe-once",
                "raw": b"x",
                "public": False,
            }
        )
        logger_name = "odoo.addons.base.models.ir_attachment"
        with self.assertLogs(logger_name, level="INFO") as first:
            self.env["ir.attachment"]._audit_url_attachments()
        self.assertTrue(
            any(rec.levelname == "WARNING" for rec in first.records),
            "first sighting must warn",
        )
        with self.assertLogs(logger_name, level="INFO") as second:
            self.env["ir.attachment"]._audit_url_attachments()
        self.assertFalse(
            any(rec.levelname == "WARNING" for rec in second.records),
            "already-reported rows must not re-warn",
        )
        self.assertTrue(
            any("previously reported" in rec.getMessage() for rec in second.records),
            "unresolved rows keep an INFO heartbeat",
        )

    def test_audit_flags_exactly_what_the_fallback_refuses(self):
        hidden, served = self.Attachment.sudo().create(
            [
                {
                    "name": f"{name}.bin",
                    "type": "binary",
                    "url": f"/audit/{name}",
                    "raw": b"x",
                    "public": public,
                }
                for name, public in (("hidden", False), ("served", True))
            ]
        )
        fallback_domain = [("public", "=", True)]
        Attachment = self.Attachment.sudo()
        self.assertFalse(
            Attachment._get_serve_attachment(hidden.url, extra_domain=fallback_domain)
        )
        self.assertEqual(
            Attachment._get_serve_attachment(served.url, extra_domain=fallback_domain),
            served,
        )
        with self.assertLogs(
            "odoo.addons.base.models.ir_attachment", level="WARNING"
        ) as logs:
            self.env["ir.attachment"]._audit_url_attachments()
        warning = "\n".join(logs.output)
        self.assertIn(hidden.url, warning)
        self.assertNotIn(served.url, warning)

    def test_audit_url_attachments_silent_on_clean_fleet(self):
        self.env.cr.execute(
            "UPDATE ir_attachment SET public = TRUE "
            "WHERE type = 'binary' AND url IS NOT NULL"
        )
        with self.assertNoLogs(
            "odoo.addons.base.models.ir_attachment", level="WARNING"
        ):
            self.env["ir.attachment"]._audit_url_attachments()


class TestContentDigestKeys(TransactionCaseWithUserDemo):
    def setUp(self):
        super().setUp()
        self.Attachment = self.env["ir.attachment"]
        self.filestore = self.Attachment._get_filestore()
        self.env["ir.config_parameter"].set_param("ir_attachment.location", "file")

    @contextlib.contextmanager
    def _tagged_digest_build(self):
        with (
            patch.object(ir_attachment_module, "ALGO_TAG", "b3"),
            patch.object(ir_attachment_module, "CONTENT_DIGEST_LEN", 64),
            patch.object(
                ir_attachment_module,
                "content_hash",
                lambda data: hashlib.sha256(data or b"").hexdigest(),
            ),
        ):
            yield

    def _legacy_key(self, payload):
        sha = hashlib.sha1(payload, usedforsecurity=False).hexdigest()
        fname = sha[:2] + "/" + sha
        path = Path(self.filestore, fname)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        self.addCleanup(path.unlink, missing_ok=True)
        return fname, sha

    def test_new_keys_carry_the_algorithm_tag(self):
        att = self.Attachment.create({"name": "tagged", "raw": b"tag-" + os.urandom(8)})
        self.addCleanup(Path(self.filestore, att.store_fname).unlink, missing_ok=True)
        self.assertEqual(att.store_fname, self.Attachment._get_store_key(att.checksum))
        self.assertEqual(Path(self.filestore, att.store_fname).read_bytes(), att.raw)

        with self._tagged_digest_build():
            tagged = self.Attachment.create(
                {"name": "tagged2", "raw": b"tag2-" + os.urandom(8)}
            )
            tagged.flush_recordset()
            self.addCleanup(
                Path(self.filestore, tagged.store_fname).unlink, missing_ok=True
            )
            self.assertTrue(tagged.store_fname.startswith("b3/"))
            self.assertEqual(len(tagged.store_fname.split("/")), 3)
            self.assertEqual(
                tagged.store_fname,
                self.Attachment._get_store_key(tagged.checksum),
            )

    def test_checksum_column_fits_the_digest(self):
        att = self.Attachment.create({"name": "len", "raw": b"len-" + os.urandom(8)})
        self.addCleanup(Path(self.filestore, att.store_fname).unlink, missing_ok=True)
        att.flush_recordset()
        att.invalidate_recordset()
        self.assertEqual(att.checksum, self.Attachment._get_content_checksum(att.raw))
        self.assertLessEqual(len(att.checksum), 64)

    def test_legacy_key_still_reads(self):
        payload = b"legacy-" + os.urandom(16)
        fname, sha = self._legacy_key(payload)
        att = self.Attachment.create({"name": "legacy", "raw": b"placeholder"})
        self.addCleanup(Path(self.filestore, att.store_fname).unlink, missing_ok=True)
        att.flush_recordset()
        self.env.cr.execute(
            "UPDATE ir_attachment SET store_fname = %s, checksum = %s, file_size = %s "
            "WHERE id = %s",
            [fname, sha, len(payload), att.id],
        )
        att.invalidate_recordset()
        self.assertEqual(att.raw, payload, "legacy-keyed content must still read")
        self.assertEqual(self.Attachment._read_file(fname), payload)
        self.assertEqual(len(att.checksum), 40)

    def test_legacy_key_is_gc_collectable(self):
        payload = b"legacy-gc-" + os.urandom(16)
        fname, _sha = self._legacy_key(payload)
        self.Attachment._mark_for_gc(fname)
        marker = Path(self.filestore, "checklist", fname)
        self.assertTrue(marker.is_file(), "marker created at the legacy depth")
        checklist = self.Attachment._get_gc_checklist(grace=0)
        self.assertIn(fname, checklist)
        self.Attachment._gc_file_store_unsafe(
            checklist={fname: checklist[fname]}, grace=0
        )
        self.assertFalse(Path(self.filestore, fname).exists())
        self.assertFalse(marker.exists())

    def test_both_layouts_coexist_in_one_filestore(self):
        payload = b"coexist-" + os.urandom(16)
        legacy_fname, _sha = self._legacy_key(payload)

        with self._tagged_digest_build():
            att = self.Attachment.create({"name": "coexist", "raw": payload})
            att.flush_recordset()
            self.addCleanup(
                Path(self.filestore, att.store_fname).unlink, missing_ok=True
            )
            self.assertNotEqual(
                att.store_fname, legacy_fname, "the two layouts must not collide"
            )
            self.assertEqual(self.Attachment._read_file(legacy_fname), payload)
            self.assertEqual(self.Attachment._read_file(att.store_fname), payload)

        self.assertEqual(
            self.Attachment._read_file(att.store_fname),
            payload,
            "a key written under one layout keeps reading under the other",
        )

    def test_collision_verification_default_follows_the_algorithm(self):
        self.assertEqual(
            self.Attachment._is_content_collision_check_enabled(),
            ALGO_TAG == "s1",
            "sha1 needs the byte-compare; a modern digest does not",
        )

    def test_collision_verification_param_wins(self):
        ICP = self.env["ir.config_parameter"]
        for value, expected in (("True", True), ("False", False)):
            ICP.set_param("ir_attachment.verify_content_collision", value)
            self.assertEqual(
                self.Attachment._is_content_collision_check_enabled(), expected
            )

    def test_legacy_key_domain_matches_shape_not_prefix(self):
        payload = b"shape-" + os.urandom(16)
        good = self.Attachment.create({"name": "well-formed", "raw": payload})
        good.flush_recordset()
        self.addCleanup(Path(self.filestore, good.store_fname).unlink, missing_ok=True)
        self.assertEqual(
            good.store_fname,
            self.Attachment._get_store_key(
                self.Attachment._get_content_checksum(payload)
            ),
        )

        malformed = good.store_fname.rsplit("/", 1)[0] + "/" + "0" * 8
        bad = self.Attachment.create({"name": "malformed", "raw": b"other-" + payload})
        bad.flush_recordset()
        self.addCleanup(Path(self.filestore, bad.store_fname).unlink, missing_ok=True)
        self.env.cr.execute(
            "UPDATE ir_attachment SET store_fname = %s WHERE id = %s",
            [malformed, bad.id],
        )
        bad.invalidate_recordset()

        selected = (
            self.Attachment.sudo()
            .with_context(skip_res_field_check=True)
            .search(
                self.Attachment._get_domain_legacy_keys()
                & Domain("id", "in", (good | bad).ids)
            )
        )
        self.assertEqual(
            selected.ids,
            bad.ids,
            "the domain must select the malformed key and spare the well-formed one",
        )

    def test_untagged_layout_under_the_sha1_tag(self):
        sha = "0" * 40
        with patch.object(ir_attachment_module, "ALGO_TAG", "s1"):
            self.assertEqual(self.Attachment._get_store_key(sha), f"{sha[:2]}/{sha}")

    def test_verification_defaults_on_under_the_sha1_tag(self):
        with patch.object(ir_attachment_module, "ALGO_TAG", "s1"):
            self.assertTrue(self.Attachment._is_content_collision_check_enabled())

    @mute_logger("odoo.addons.base.models.ir_attachment")
    def test_forced_verification_still_detects_a_mismatch(self):
        self.env["ir.config_parameter"].set_param(
            "ir_attachment.verify_content_collision", "True"
        )
        payload = b"verify-" + os.urandom(16)
        checksum = self.Attachment._get_content_checksum(payload)
        fname = self.Attachment._get_store_key(checksum)
        path = Path(self.filestore, fname)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"different bytes entirely")
        self.addCleanup(path.unlink, missing_ok=True)
        with self.assertRaises(UserError):
            self.Attachment._write_file(payload, checksum)

    def test_stream_and_buffered_writes_agree(self):
        payload = b"stream-" + os.urandom(4096)
        fname, size, checksum = self.Attachment._write_file_stream(io.BytesIO(payload))
        self.addCleanup(Path(self.filestore, fname).unlink, missing_ok=True)
        self.assertEqual(size, len(payload))
        self.assertEqual(checksum, self.Attachment._get_content_checksum(payload))
        self.assertEqual(fname, self.Attachment._get_store_key(checksum))
        self.assertEqual(self.Attachment._read_file(fname), payload)

    def _legacy_row(self, payload):
        fname, sha = self._legacy_key(payload)
        att = self.Attachment.create({"name": "legacy-row", "raw": b"placeholder"})
        self.addCleanup(Path(self.filestore, att.store_fname).unlink, missing_ok=True)
        att.flush_recordset()
        self.env.cr.execute(
            "UPDATE ir_attachment SET store_fname = %s, checksum = %s, file_size = %s "
            "WHERE id = %s",
            [fname, sha, len(payload), att.id],
        )
        att.invalidate_recordset()
        return att, fname

    def _drain_legacy_rows(self):
        while self.Attachment._gc_rehash_legacy_keys(limit=1000)[0]:
            pass

    def test_rehash_is_disabled_by_default(self):
        att, fname = self._legacy_row(b"untouched-" + os.urandom(16))
        self.assertEqual(self.Attachment._gc_rehash_legacy_keys(), (0, 0))
        att.invalidate_recordset()
        self.assertEqual(att.store_fname, fname, "no re-key without the opt-in")

    def test_rehash_rekeys_and_preserves_content(self):
        with self._tagged_digest_build():
            self._drain_legacy_rows()
            payload = b"converge-" + os.urandom(16)
            att, old_fname = self._legacy_row(payload)
            size_before, index_before = att.file_size, att.index_content

            self.assertEqual(self.Attachment._gc_rehash_legacy_keys(limit=10), (1, 0))

            att.invalidate_recordset()
            self.addCleanup(
                Path(self.filestore, att.store_fname).unlink, missing_ok=True
            )
            self.assertTrue(att.store_fname.startswith("b3/"))
            self.assertEqual(att.raw, payload, "bytes must survive the re-key")
            self.assertEqual(
                att.checksum, self.Attachment._get_content_checksum(payload)
            )
            self.assertEqual(
                att.store_fname, self.Attachment._get_store_key(att.checksum)
            )
            self.assertEqual(att.file_size, size_before)
            self.assertEqual(att.index_content, index_before)
            self.assertTrue(Path(self.filestore, old_fname).exists())
            self.assertTrue(Path(self.filestore, "checklist", old_fname).exists())

    def test_rehash_respects_its_limit_and_is_resumable(self):
        with self._tagged_digest_build():
            self._drain_legacy_rows()
            rows = [
                self._legacy_row(f"batch-{i}".encode() + os.urandom(8))[0]
                for i in range(3)
            ]
            self.assertEqual(self.Attachment._gc_rehash_legacy_keys(limit=2), (2, 1))
            self.assertEqual(self.Attachment._gc_rehash_legacy_keys(limit=2), (1, 0))
            self.assertEqual(self.Attachment._gc_rehash_legacy_keys(limit=2), (0, 0))
            for att in rows:
                att.invalidate_recordset()
                self.addCleanup(
                    Path(self.filestore, att.store_fname).unlink, missing_ok=True
                )
                self.assertTrue(att.store_fname.startswith("b3/"))
                self.assertEqual(
                    att.store_fname,
                    self.Attachment._get_store_key(att.checksum),
                )

    def test_rehash_leaves_shared_legacy_content_readable(self):
        with self._tagged_digest_build():
            self._drain_legacy_rows()
            payload = b"shared-" + os.urandom(16)
            first, legacy_fname = self._legacy_row(payload)
            second, _ = self._legacy_row(payload)
            self.assertEqual(second.store_fname, legacy_fname)

            self.assertEqual(self.Attachment._gc_rehash_legacy_keys(limit=1)[0], 1)
            first.invalidate_recordset()
            second.invalidate_recordset()
            self.addCleanup(
                Path(self.filestore, first.store_fname).unlink, missing_ok=True
            )

            checklist = self.Attachment._get_gc_checklist(grace=0)
            if legacy_fname in checklist:
                self.Attachment._gc_file_store_unsafe(
                    checklist={legacy_fname: checklist[legacy_fname]}, grace=0
                )
            self.assertEqual(second.raw, payload, "the sibling row must still read")

    @mute_logger("odoo.addons.base.models.ir_attachment")
    def test_rehash_reports_no_remaining_when_it_makes_no_progress(self):
        with self._tagged_digest_build():
            self._drain_legacy_rows()
            att, _fname = self._legacy_row(b"unreadable-" + os.urandom(16))
            with patch.object(IrAttachment, "_read_file", return_value=b""):
                self.assertEqual(
                    self.Attachment._gc_rehash_legacy_keys(limit=10),
                    (0, 0),
                    "no progress must report nothing remaining",
                )
            att.invalidate_recordset()
            self.assertFalse(att.store_fname.startswith("b3/"))

    def test_rehash_skips_other_backends_keys(self):
        with self._tagged_digest_build():
            att = self.Attachment.create({"name": "remote", "raw": b"remote-ish"})
            self.addCleanup(
                Path(self.filestore, att.store_fname).unlink, missing_ok=True
            )
            att.flush_recordset()
            self.env.cr.execute(
                "UPDATE ir_attachment SET store_fname = %s WHERE id = %s",
                ["s3://bucket/deadbeef", att.id],
            )
            att.invalidate_recordset()
            self.Attachment._gc_rehash_legacy_keys(limit=10)
            att.invalidate_recordset()
            self.assertEqual(att.store_fname, "s3://bucket/deadbeef")

    def test_rehash_is_a_noop_under_db_storage(self):
        att, fname = self._legacy_row(b"dbmode-" + os.urandom(16))
        self.env["ir.config_parameter"].set_param("ir_attachment.location", "db")
        self.assertEqual(self.Attachment._gc_rehash_legacy_keys(limit=10), (0, 0))
        att.invalidate_recordset()
        self.assertEqual(att.store_fname, fname)


class TestPermissions(TransactionCaseWithUserDemo):
    def setUp(self):
        super().setUp()
        self.env = self.env(user=self.user_demo)
        self.Attachments = self.env["ir.attachment"]

        record = self.Attachments.create({"name": "record1"})
        self.vals = {
            "name": "attach",
            "res_id": record.id,
            "res_model": record._name,
        }
        a = self.attachment = self.Attachments.create(self.vals)

        self.rule = (
            self.env["ir.rule"]
            .sudo()
            .create(
                {
                    "name": "remove access to record %d" % record.id,
                    "model_id": self.env["ir.model"]._get_id(record._name),
                    "domain_force": "[('id', '!=', %s)]" % record.id,
                    "perm_read": False,
                }
            )
        )
        self.env.flush_all()
        a.invalidate_recordset()

    def test_read_permission(self):
        _ = self.attachment.datas
        self.rule.perm_read = True
        self.attachment.invalidate_recordset()
        with self.assertRaises(AccessError):
            _ = self.attachment.datas

        self.attachment.sudo().public = True
        _ = self.attachment.datas
        self.attachment.sudo().public = False
        with self.assertRaises(AccessError):
            _ = self.attachment.datas

        attachment_user = self.Attachments.create({"name": "foo"})
        _ = attachment_user.datas
        attachment_admin = self.Attachments.with_user(SUPERUSER_ID).create(
            {"name": "foo"}
        )
        with self.assertRaises(AccessError):
            _ = attachment_admin.with_user(self.env.user).datas
        admin_user = self.env.ref("base.user_admin")
        self.assertNotEqual(SUPERUSER_ID, admin_user.id)
        _ = attachment_admin.with_user(admin_user).datas

    @mute_logger("odoo.addons.base.models.ir_rule", "odoo.models")
    def test_field_read_permission(self):
        skip_if_dev_mode("xml")
        main_partner = self.env.ref("base.main_partner")
        self.assertTrue(main_partner.image_128)
        attachment = self.env["ir.attachment"].search(
            [
                ("res_model", "=", "res.partner"),
                ("res_id", "=", main_partner.id),
                ("res_field", "=", "image_128"),
            ]
        )
        self.assertTrue(attachment.datas)
        with self.assertQueries(
            [
                """
            SELECT "ir_attachment"."id"
            FROM "ir_attachment"
            WHERE ("ir_attachment"."res_field" IN (%s) AND "ir_attachment"."res_id" IN (%s) AND "ir_attachment"."res_model" IN (%s) AND (
                "ir_attachment"."public" IS TRUE
                OR (
                    ("ir_attachment"."res_field" IN (%s) OR "ir_attachment"."res_field" IS NULL)
                    AND "ir_attachment"."res_id" IN (
                        SELECT "res_partner"."id"
                        FROM "res_partner"
                        WHERE "res_partner"."id" IN (%s) AND (
                            (
                                ("res_partner"."company_id" IN (%s) OR "res_partner"."company_id" IS NULL)
                                OR "res_partner"."partner_share" IS NOT TRUE
                            )
                            AND (
                                "res_partner"."parent_id" IN (%s)
                                OR ("res_partner"."type" NOT IN (%s) OR "res_partner"."type" IS NULL)
                            )
                        )
                    )
                    AND "ir_attachment"."res_model" IN (%s)
                )
            ))
            ORDER BY "ir_attachment"."id" DESC
            """
            ]
        ):
            self.env["ir.attachment"].search(
                [
                    ("res_model", "=", "res.partner"),
                    ("res_id", "=", main_partner.id),
                    ("res_field", "=", "image_128"),
                ]
            )

        self.patch(
            self.env.registry["res.partner"]._fields["image_128"],
            "groups",
            "base.group_system",
        )

        with self.assertRaises(AccessError):
            _ = main_partner.image_128
        with self.assertRaises(AccessError):
            _ = attachment.datas

    def test_field_read_permission_uses_comodel_acl(self):
        main_partner = self.env.ref("base.main_partner")
        attachment = self.env["ir.attachment"].search(
            [
                ("res_model", "=", "res.partner"),
                ("res_id", "=", main_partner.id),
                ("res_field", "=", "image_128"),
            ]
        )
        self.assertTrue(attachment.datas)

        partner_field = self.env.registry["res.partner"]._fields["image_128"]
        attach_called, partner_called = [], []
        attach_orig = self.env.registry["ir.attachment"]._has_field_access
        partner_orig = self.env.registry["res.partner"]._has_field_access

        def attach_spy(this, field, operation, _o=attach_orig):
            if field is partner_field:
                attach_called.append(operation)
            return _o(this, field, operation)

        def partner_deny(this, field, operation, _o=partner_orig):
            if field is partner_field:
                partner_called.append(operation)
                if operation == "read":
                    return False
            return _o(this, field, operation)

        self.patch(self.env.registry["ir.attachment"], "_has_field_access", attach_spy)
        self.patch(self.env.registry["res.partner"], "_has_field_access", partner_deny)

        attachment.invalidate_recordset()
        with self.assertRaises(AccessError):
            _ = attachment.datas

        self.assertIn("read", partner_called, "comodel ACL must be consulted")
        self.assertNotIn(
            "read", attach_called, "field ACL must not be checked on ir.attachment"
        )

    @mute_logger("odoo.addons.base.models.ir_rule", "odoo.models")
    def test_search_unbounded_model_fallback(self):
        public_att = self.Attachments.sudo().create({"name": "public", "public": True})
        admin_orphan = self.Attachments.with_user(SUPERUSER_ID).create(
            {"name": "admin-orphan"}
        )
        own_orphan = self.Attachments.create({"name": "demo-orphan"})

        probe_ids = (public_att + admin_orphan + own_orphan).ids
        found = self.Attachments.search([("id", "in", probe_ids)])
        self.assertIn(public_att.id, found.ids)
        self.assertIn(own_orphan.id, found.ids)
        self.assertNotIn(
            admin_orphan.id,
            found.ids,
            "the superuser-owned orphan attachment must not leak to the demo user",
        )

    def test_search_unbounded_matches_limited(self):
        atts = self.Attachments.sudo().create(
            [{"name": f"pub{i}", "public": True} for i in range(12)]
        )
        ids = atts.ids
        unbounded = self.Attachments.search([("id", "in", ids)])
        limited = self.Attachments.search([("id", "in", ids)], limit=len(ids))
        self.assertEqual(set(unbounded.ids), set(ids), "unbounded must return all")
        self.assertEqual(
            set(unbounded.ids), set(limited.ids), "unbounded must match limited"
        )

    def test_a_limited_search_returns_the_head_of_the_unbounded_order(self):
        atts = self.Attachments.create(
            [{"name": f"headtest-{i:02d}", "public": True} for i in range(6)]
        )
        domain = [("name", "=like", "headtest-%")]
        unbounded = self.Attachments.search(domain).ids
        self.assertEqual(
            set(unbounded), set(atts.ids), "precondition: all rows are accessible"
        )
        for n in (1, 3, 5):
            with self.subTest(limit=n):
                self.assertEqual(
                    self.Attachments.search(domain, limit=n).ids,
                    unbounded[:n],
                    "a limited search must be the head of the unbounded order",
                )

    def test_search_keyset_pagination_crosses_batches(self):
        all_ids = []
        for i in range(24):
            kind = i % 3
            if kind == 0:
                a = self.Attachments.sudo().create(
                    {"name": f"p{i:02d}", "public": True}
                )
            elif kind == 1:
                a = self.Attachments.create({"name": f"o{i:02d}"})
            else:
                a = self.Attachments.with_user(SUPERUSER_ID).create(
                    {"name": f"a{i:02d}"}
                )
            all_ids.append(a.id)
        domain = [("id", "in", all_ids)]
        forbidden = set(all_ids[2::3])

        def run():
            search = self.Attachments.search
            return {
                "limit=None": search(domain).ids,
                "limit=5": search(domain, limit=5).ids,
                "limit=7": search(domain, limit=7).ids,
                "offset=3,limit=4": search(domain, offset=3, limit=4).ids,
                "order=name": search(domain, order="name").ids,
                "order=name,limit=6": search(domain, order="name", limit=6).ids,
                "order=name,offset=5,limit=5": search(
                    domain, order="name", offset=5, limit=5
                ).ids,
            }

        truth = run()
        with patch("odoo.addons.base.models.ir_attachment.PREFETCH_MAX", 3):
            batched = run()

        for label, ids in batched.items():
            self.assertEqual(
                ids,
                truth[label],
                f"{label}: multi-batch result diverged from single fetch",
            )
            self.assertEqual(
                len(ids), len(set(ids)), f"{label}: duplicate id across batch boundary"
            )
            self.assertFalse(
                set(ids) & forbidden, f"{label}: leaked an inaccessible row"
            )

    def test_batch_seek_keysets_the_order_search_actually_passes(self):
        model = self.Attachments
        anchor = model.create({"name": "anchor"})

        for order in (model._order, "id desc", "id", "id ASC", "id desc, name"):
            with self.subTest(order=order):
                effective, keyset = model._get_seek_order_and_keyset(order)
                self.assertEqual(effective, order, "an id-led order is already total")
                self.assertIsNotNone(keyset, "no keyset derived for an id-led order")
                seek = keyset(anchor)
                expected = "<" if "desc" in order else ">"
                self.assertEqual(
                    [
                        (c.field_expr, c.operator, c.value)
                        for c in seek.iter_conditions()
                    ],
                    [("id", expected, anchor.id)],
                )

        effective, keyset = model._get_seek_order_and_keyset("name")
        self.assertEqual(effective, "name, id", "a caller order must be made total")
        self.assertIsNone(keyset, "an unvetted leading term must stay on OFFSET")

        effective, keyset = model._get_seek_order_and_keyset("name desc, id")
        self.assertEqual(effective, "name desc, id", "an order ending in id is total")
        self.assertIsNone(keyset)

        effective, keyset = model._get_seek_order_and_keyset(None)
        self.assertEqual(
            effective, "id desc", "the order-less scan must use the model order"
        )
        self.assertIsNotNone(keyset, "the order-less scan must keep its keyset")

    @mute_logger("odoo.addons.base.models.ir_rule", "odoo.models")
    def test_write_access_is_enforced_without_the_duplicate_check(self):
        outsider = (
            self.env["res.users"]
            .sudo()
            .create(
                {
                    "name": "Write Outsider",
                    "login": "attachment_write_outsider",
                    "group_ids": [(6, 0, self.env.ref("base.group_user").ids)],
                }
            )
        )
        mine = self.Attachments.create({"name": "mine", "raw": b"mine"})
        self.env.flush_all()

        theirs = mine.with_user(outsider)
        theirs.invalidate_recordset()
        for vals in (
            {"name": "renamed"},
            {"raw": b"replaced"},
            {"res_model": "res.partner", "res_id": self.env.user.partner_id.id},
            {"public": True},
        ):
            with self.subTest(vals=list(vals)), self.assertRaises(AccessError):
                theirs.write(vals)
        self.assertEqual(mine.name, "mine")
        self.assertEqual(mine.raw, b"mine")

    @mute_logger("odoo.addons.base.models.ir_rule", "odoo.models")
    def test_res_field_write_access(self):
        partner = self.user_demo.partner_id
        self.patch(
            self.env.registry["res.partner"]._fields["image_1920"],
            "groups",
            "base.group_system",
        )

        with self.assertRaises(AccessError):
            self.Attachments.create(
                {
                    "name": "field-attach",
                    "res_model": "res.partner",
                    "res_id": partner.id,
                    "res_field": "image_1920",
                }
            )

        existing = self.Attachments.create(
            {
                "name": "field-attach",
                "res_model": "res.partner",
                "res_id": partner.id,
            }
        )
        with self.assertRaises(AccessError):
            existing.write({"res_field": "image_1920"})

    @mute_logger("odoo.addons.base.models.ir_rule", "odoo.models")
    def test_res_model_write_retargets_res_field_and_is_gated(self):
        partner = self.user_demo.partner_id
        attachment = self.Attachments.create(
            {
                "name": "avatar",
                "res_model": "res.partner",
                "res_id": partner.id,
                "res_field": "image_1920",
                "raw": b"x",
            }
        )
        self.patch(
            self.env.registry["res.users"]._fields["image_1920"],
            "groups",
            "base.group_system",
        )
        with self.assertRaises(AccessError):
            attachment.write({"res_model": "res.users", "res_id": self.env.uid})
        self.assertEqual(attachment.res_model, "res.partner")

    def _revoke_model_read(self, model_name):
        self.env["ir.model.access"].sudo().search(
            [("model_id.model", "=", model_name), ("perm_read", "=", True)]
        ).write({"perm_read": False})
        self.env.flush_all()
        self.env.registry.clear_cache()
        self.addCleanup(self.env.registry.clear_cache)
        self.assertFalse(
            self.env[model_name].with_user(self.user_demo).has_access("read"),
            f"{model_name} was expected to become unreadable",
        )

    def _unprefiltered(self, func):
        with patch.object(
            IrAttachment,
            "_get_domain_security_prefilter",
            lambda self, sec_domain: sec_domain | Domain("res_model", "!=", False),
        ):
            return func()

    @mute_logger("odoo.addons.base.models.ir_rule", "odoo.models")
    def test_scan_prefilter_agrees_with_the_unprefiltered_scan(self):
        view = self.env["ir.ui.view"].sudo().search([], limit=1)
        self.Attachments.sudo().create(
            [
                {
                    "name": f"scan-{i}.txt",
                    "raw": f"c{i}".encode(),
                    "res_model": "ir.ui.view",
                    "res_id": view.id,
                    "public": bool(i % 3 == 0),
                }
                for i in range(9)
            ]
        )
        self.env.flush_all()
        self._revoke_model_read("ir.ui.view")

        for domain in ([], [("name", "like", "scan-")], [("public", "=", False)]):
            with self.subTest(domain=domain):
                self.assertEqual(
                    self.Attachments.search(domain).ids,
                    self._unprefiltered(
                        lambda d=domain: self.Attachments.search(d).ids
                    ),
                )
                self.assertEqual(
                    self.Attachments.search_count(domain),
                    self._unprefiltered(
                        lambda d=domain: self.Attachments.search_count(d)
                    ),
                )

    @mute_logger("odoo.addons.base.models.ir_rule", "odoo.models")
    def test_scan_prefilter_keeps_public_rows_of_an_unreadable_model(self):
        view = self.env["ir.ui.view"].sudo().search([], limit=1)
        public, private = self.Attachments.sudo().create(
            [
                {
                    "name": "public-on-hidden-model.txt",
                    "raw": b"visible",
                    "res_model": "ir.ui.view",
                    "res_id": view.id,
                    "public": True,
                },
                {
                    "name": "private-on-hidden-model.txt",
                    "raw": b"hidden",
                    "res_model": "ir.ui.view",
                    "res_id": view.id,
                },
            ]
        )
        self.env.flush_all()
        self._revoke_model_read("ir.ui.view")

        found = self.Attachments.search([("name", "like", "-on-hidden-model.txt")])
        self.assertEqual(found, public)
        self.assertNotIn(private, found)
        self.assertEqual(public.raw, b"visible")

    @mute_logger("odoo.addons.base.models.ir_rule", "odoo.models")
    def test_scan_prefilter_keeps_rows_with_no_res_model(self):
        mine = self.Attachments.create({"name": "mine-unlinked.txt", "raw": b"mine"})
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE ir_attachment SET res_model = NULL, res_id = NULL WHERE id = %s",
            [mine.id],
        )
        mine.invalidate_recordset()
        view = self.env["ir.ui.view"].sudo().search([], limit=1)
        self.Attachments.sudo().create(
            {
                "name": "on-hidden.txt",
                "raw": b"x",
                "res_model": "ir.ui.view",
                "res_id": view.id,
            }
        )
        self.env.flush_all()
        self._revoke_model_read("ir.ui.view")
        self.assertIn(
            "ir.ui.view",
            self.Attachments._get_model_names_attached()[0],
            "this test needs the unreadable model to be discovered",
        )

        found = self.Attachments.search([("name", "like", "-unlinked.txt")])
        self.assertEqual(found, mine)
        self.assertEqual(
            found.ids,
            self._unprefiltered(
                lambda: self.Attachments.search([("name", "like", "-unlinked.txt")]).ids
            ),
        )

    def test_scan_prefilter_declines_past_the_discovery_cap(self):
        sec_domain = Domain("public", "=", True)
        with patch.object(
            IrAttachment,
            "_get_model_names_attached",
            lambda self: (["res.partner"], True),
        ):
            self.assertEqual(
                self.Attachments._get_domain_security_prefilter(sec_domain),
                sec_domain | Domain("res_model", "!=", False),
            )

    def test_res_field_cannot_outlive_its_res_model(self):
        backed = self.Attachments.create(
            {
                "name": "avatar",
                "res_model": "res.partner",
                "res_id": self.user_demo.partner_id.id,
                "res_field": "image_1920",
                "raw": b"x",
            }
        )
        for records in (backed, backed.sudo()):
            with self.subTest(su=records.env.su), self.assertRaises(ValidationError):
                records.write({"res_model": False})
        self.assertEqual(backed.res_model, "res.partner")

        with self.assertRaises(ValidationError):
            self.Attachments.sudo().create(
                {"name": "orphan", "res_field": "image_1920", "raw": b"x"}
            )

        backed.write({"res_model": False, "res_field": False})
        self.assertFalse(backed.res_model)
        self.assertFalse(backed.res_field)

    @mute_logger("odoo.addons.base.models.ir_rule", "odoo.models")
    def test_a_non_string_res_model_is_refused_not_crashed_on(self):
        partner = self.user_demo.partner_id
        for res_model in ([], ["res.partner"], {"a": 1}, 42, 0.5):
            with self.subTest(res_model=res_model):
                try:
                    self.Attachments.create(
                        {"name": "odd", "res_model": res_model, "res_id": partner.id}
                    )
                except (AccessError, ValidationError, ValueError, TypeError) as exc:
                    self.assertNotIsInstance(
                        exc, TypeError, "the access check crashed on client input"
                    )

        row = self.Attachments.create({"name": "plain", "raw": b"x"})
        for res_model in ([], ["res.partner"], 42):
            with (
                self.subTest(write=res_model),
                contextlib.suppress(AccessError, ValidationError, ValueError),
            ):
                row.write({"res_model": res_model})

    def test_res_field_targets_cover_every_way_the_pair_moves(self):
        partner = self.user_demo.partner_id
        backed = self.Attachments.create(
            {
                "name": "avatar",
                "res_model": "res.partner",
                "res_id": partner.id,
                "res_field": "image_1920",
                "raw": b"x",
            }
        )
        self.assertEqual(
            set(backed._get_res_field_targets({"res_model": "res.users"})),
            {("res.users", "image_1920")},
        )
        self.assertEqual(
            set(backed._get_res_field_targets({"res_field": "avatar_128"})),
            {("res.partner", "avatar_128")},
        )
        self.assertEqual(
            set(
                backed._get_res_field_targets(
                    {"res_model": "res.users", "res_field": "avatar_128"}
                )
            ),
            {("res.users", "avatar_128")},
        )
        self.assertEqual(backed._get_res_field_targets({"name": "x"}), OrderedSet())
        self.assertEqual(
            set(self.attachment._get_res_field_targets({"res_model": "res.users"})),
            {("res.users", False)},
            "a row with no res_field must yield a pair the check returns on",
        )

    def test_derive_mode_reproduces_the_buffered_create(self):

        class _FakeFile:
            def __init__(self, content, filename):
                self._buf = io.BytesIO(content)
                self.filename = filename
                self.content_type = "application/octet-stream"

            def read(self, size=-1):
                return self._buf.read(size)

            def seek(self, offset, whence=0):
                return self._buf.seek(offset, whence)

        png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
            b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        )
        for filename, content in (
            ("report.csv", b"a,b,c\n1,2,3\n"),
            ("sheet.xlsx", b"PK\x03\x04" + b"\x00" * 60),
            ("noext", b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n" + b"x" * 100),
            ("photo.png", png),
            ("plain.txt", b"hello world"),
        ):
            with self.subTest(filename=filename):
                buffered = self.Attachments.create({"name": filename, "raw": content})
                streamed = self.Attachments._create_from_request_file(
                    _FakeFile(content, filename)
                )
                for field in ("name", "mimetype", "file_size", "checksum", "raw"):
                    self.assertEqual(
                        streamed[field],
                        buffered[field],
                        f"{field} differs between the two upload paths",
                    )

    def test_from_request_file_mimetype_modes(self):

        class _FakeFile:
            def __init__(self, content, content_type, filename):
                self._buf = io.BytesIO(content)
                self.content_type = content_type
                self.filename = filename

            def read(self, size=-1):
                return self._buf.read(size)

            def seek(self, offset, whence=0):
                return self._buf.seek(offset, whence)

        explicit = self.Attachments._create_from_request_file(
            _FakeFile(b"hello", "application/octet-stream", "note.txt"),
            mimetype="text/plain",
        )
        self.assertEqual(explicit.mimetype, "text/plain")

        png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
            b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        )
        guessed = self.Attachments._create_from_request_file(
            _FakeFile(png, "application/octet-stream", "img"),
            mimetype="GUESS",
        )
        self.assertEqual(guessed.mimetype, "image/png")

        trusted_html = self.Attachments._create_from_request_file(
            _FakeFile(b"<script>alert(1)</script>", "text/html", "evil.html"),
            mimetype="TRUST",
        )
        self.assertEqual(
            trusted_html.mimetype,
            "text/plain",
            "TRUST-ed text/html must be neutered for a non-view writer",
        )
        trusted_svg = self.Attachments._create_from_request_file(
            _FakeFile(b"<svg/>", "image/svg+xml", "evil.svg"),
            mimetype="TRUST",
        )
        self.assertEqual(
            trusted_svg.mimetype,
            "text/plain",
            "TRUST-ed image/svg+xml must be neutered for a non-view writer",
        )

    def test_with_write_permissions(self):
        self.rule.perm_write = False
        attachment = self.Attachments.create(self.vals)
        attachment.copy()
        attachment.write({"raw": b"test"})
        attachment.unlink()

    def test_basic_modifications(self):
        with self.assertRaises(AccessError):
            self.Attachments.create(self.vals)
        with self.assertRaises(AccessError):
            self.attachment.write({"raw": b"yay"})
        with self.assertRaises(AccessError):
            self.attachment.unlink()
        with self.assertRaises(AccessError):
            self.attachment.copy()

    def test_cross_record_copies(self):
        unwritable = self.env["res.users.apikeys.description"].create(
            {"name": "Unwritable"}
        )
        with self.assertRaises(AccessError):
            unwritable.write({})
        writable = self.Attachments.create({"name": "yes"})
        writable.name = "canwrite"

        copied = self.attachment.copy(
            {"res_model": writable._name, "res_id": writable.id}
        )
        copied.copy()
        with self.assertRaises(AccessError):
            copied.copy({"res_id": self.vals["res_id"]})

        with self.assertRaises(AccessError):
            self.attachment.copy(
                {"res_model": unwritable._name, "res_id": unwritable.id}
            )
        with self.assertRaises(AccessError):
            copied.copy({"res_model": unwritable._name, "res_id": unwritable.id})

    def test_write_error(self):
        key = "te/test_write_error"
        self.patch(
            IrAttachment,
            "_prepare_file_destination",
            lambda self, _binary, _checksum: (key, "/proc/dummy_test"),
        )
        self.addCleanup(
            (self.Attachments._get_filestore_dir("checklist") / key).unlink, True
        )
        with self.assertRaises(OSError):
            self.env["ir.attachment"]._write_file(b"test", "test")

    def test_write_create_url_binary_attachment(self):
        with self.assertRaises(ValidationError):
            self.Attachments.create(
                {"name": "Py", "url": "/blabla.js", "raw": b"Something"}
            )
        with self.assertRaises(ValidationError):
            self.Attachments.create(
                {"name": "Py", "url": "/blabla.js", "raw": b"Something"}
            )
        with self.assertRaises(ValidationError):
            self.Attachments.with_context(default_url="/blabla.js").create(
                {"name": "Py", "raw": b"Something"}
            )

        existing_attachment = self.Attachments.create({"name": "aaa"})
        with self.assertRaises(ValidationError):
            existing_attachment.url = "/blabla.js"
        existing_attachment.type = "url"
        existing_attachment.url = "/blabla.js"

        with self.assertRaises(ValidationError):
            existing_attachment.type = "binary"

    def test_res_id_without_res_model_stays_owner_only(self):
        other_user = (
            self.env["res.users"]
            .sudo()
            .create(
                {
                    "name": "Attachment Outsider",
                    "login": "attachment_outsider",
                    "group_ids": [(6, 0, self.env.ref("base.group_user").ids)],
                }
            )
        )
        orphan = self.Attachments.create(
            {"name": "orphan", "raw": b"owner-only", "res_id": 1}
        )
        self.env.flush_all()
        self.assertFalse(orphan.sudo().res_model)

        outsider_view = orphan.with_user(other_user)
        outsider_view.invalidate_recordset()
        with self.assertRaises(AccessError):
            _ = outsider_view.raw
        with self.assertRaises(AccessError):
            outsider_view.write({"name": "taken over"})
        with self.assertRaises(AccessError):
            outsider_view.unlink()

        self.assertEqual(orphan.raw, b"owner-only", "the creator kept access")
        self.assertIn(
            orphan,
            self.Attachments.search([("name", "=", "orphan")]),
            "_search and _check_access disagree on what counts as unlinked",
        )
        self.assertNotIn(
            orphan,
            self.Attachments.with_user(other_user).search([("name", "=", "orphan")]),
            "an outsider found the attachment through search",
        )

    def _rule_free_comodel(self):
        for name in ("res.country", "res.country.state", "res.groups"):
            comodel = self.env.get(name)
            if comodel is not None and not comodel._search(Domain.TRUE).where_clause:
                return comodel
        self.skipTest("no rule-free readable comodel available")
        return None

    def test_search_by_model_excludes_unlinked_rows_of_others(self):
        comodel = self._rule_free_comodel()
        real_id = comodel.search([], limit=1).id
        rows = {
            label: self.Attachments.with_user(SUPERUSER_ID).create(
                {
                    "name": f"secret-{label}",
                    "res_model": comodel._name,
                    "res_id": res_id,
                    "raw": f"payload {label}".encode(),
                }
            )
            for label, res_id in (
                ("false", False),
                ("zero", 0),
                ("real", real_id),
            )
        }
        self.env.flush_all()

        by_model = self.Attachments.search([("res_model", "=", comodel._name)])
        broad = self.Attachments.search([("id", "in", [r.id for r in rows.values()])])
        for label, row in rows.items():
            reachable = row.with_user(self.env.user).has_access("read")
            self.assertEqual(
                row.id in by_model.ids,
                reachable,
                f"{label}: the per-model search path disagrees with _check_access",
            )
            self.assertEqual(
                row.id in broad.ids,
                reachable,
                f"{label}: the two search paths disagree with each other",
            )
        self.assertFalse(
            rows["false"].with_user(self.env.user).has_access("read"),
            "the unlinked row must stay owner-only, or this test proves nothing",
        )

    @mute_logger("odoo.addons.base.models.ir_rule", "odoo.models")
    def test_search_by_unreadable_model_is_empty_not_an_error(self):
        forbidden = next(
            (
                name
                for name in ("ir.model", "decimal.precision", "ir.config_parameter")
                if not self.env[name].browse().has_access("read")
            ),
            None,
        )
        if forbidden is None:
            self.skipTest("no readable-model-free candidate available")

        self.assertEqual(
            self.Attachments.search([("res_model", "=", forbidden)]).ids, []
        )
        self.assertEqual(
            self.Attachments.search_count([("res_model", "=", forbidden)]), 0
        )

        mine = self.Attachments.create(
            {"name": "mine", "res_model": forbidden, "res_id": False}
        )
        self.env.flush_all()
        self.assertIn(
            mine.id,
            self.Attachments.search([("res_model", "=", forbidden)]).ids,
            "an own unlinked row stays reachable even under an unreadable model",
        )


class TestFilestoreDedup(TransactionCaseWithUserDemo):
    def setUp(self):
        super().setUp()
        self.Attachment = self.env["ir.attachment"]
        self.tmp_dir = Path(self.Attachment._get_full_path("tmp"))

    def _temps(self):
        if not self.tmp_dir.is_dir():
            return set()
        return {path.name for path in self.tmp_dir.iterdir()}

    def test_unlink_and_content_replacement_share_the_delete_hook(self):
        seen = []
        real = IrAttachment._mark_for_gc_multi

        def spy(records, fnames):
            seen.append(tuple(fnames))
            return real(records, fnames)

        self.patch(IrAttachment, "_mark_for_gc_multi", spy)

        attachment = self.Attachment.create(
            {"name": "gone.bin", "raw": b"unlink-me" * 8}
        )
        self.env.flush_all()
        store_fname = attachment.store_fname
        attachment.unlink()
        self.assertTrue(
            any(store_fname in call for call in seen),
            "unlink() must schedule the old key through _mark_for_gc_multi",
        )

        seen.clear()
        attachment = self.Attachment.create(
            {"name": "replaced.bin", "raw": b"first-content" * 8}
        )
        self.env.flush_all()
        old_fname = attachment.store_fname
        attachment.write({"raw": b"second-content" * 8})
        self.env.flush_all()
        self.assertTrue(
            any(old_fname in call for call in seen),
            "content replacement must use the same hook",
        )

    def test_raw_and_read_prefix_agree_on_stored_content(self):
        for location in ("file", "db"):
            with self.subTest(location=location):
                self.env["ir.config_parameter"].sudo().set_param(
                    "ir_attachment.location", location
                )
                payload = f"triage-{location}".encode() * 6
                attachment = self.Attachment.create(
                    {"name": f"{location}.bin", "raw": payload}
                )
                self.env.flush_all()
                attachment.invalidate_recordset()
                self.assertEqual(attachment.raw, payload)
                self.assertEqual(attachment._get_content_prefix(), payload)
                self.assertEqual(attachment._get_content_prefix(4), payload[:4])
        self.env["ir.config_parameter"].sudo().set_param(
            "ir_attachment.location", "file"
        )

    def test_read_prefix_keeps_the_static_url_leg_raw_does_not(self):
        attachment = self.Attachment.create(
            {
                "name": "logo.png",
                "type": "url",
                "url": "/web/static/img/logo.png",
                "mimetype": "image/png",
            }
        )
        self.assertTrue(attachment._get_content_prefix())
        self.assertFalse(attachment.raw)

    @mute_logger("odoo.addons.base.models.ir_attachment")
    def test_unreadable_content_is_reported_not_silently_empty(self):
        attachment = self.Attachment.create(
            {"name": "vanishing.bin", "raw": b"here-then-gone" * 8}
        )
        self.env.flush_all()
        Path(self.Attachment._get_full_path(attachment.store_fname)).unlink()
        attachment.invalidate_recordset()
        self.assertEqual(attachment.raw, b"")
        self.assertTrue(attachment.file_size)

    def test_both_writers_stage_and_leave_no_temp(self):
        before = self._temps()

        payload = b"buffered-payload" * 8
        payload_checksum = self.Attachment._get_content_checksum(payload)
        buffered_fname = self.Attachment._write_file(payload, payload_checksum)
        self.assertEqual(
            Path(self.Attachment._get_full_path(buffered_fname)).read_bytes(), payload
        )
        self.assertEqual(self._temps(), before, "buffered write left a temp behind")

        streamed = b"streamed-payload" * 8
        stream_fname, size, checksum = self.Attachment._write_file_stream(
            io.BytesIO(streamed)
        )
        self.assertEqual(
            Path(self.Attachment._get_full_path(stream_fname)).read_bytes(), streamed
        )
        self.assertEqual(size, len(streamed))
        self.assertEqual(checksum, self.Attachment._get_content_checksum(streamed))
        self.assertEqual(self._temps(), before, "stream write left a temp behind")

        self.assertEqual(
            self.Attachment._write_file(payload, payload_checksum), buffered_fname
        )
        self.assertEqual(
            self.Attachment._write_file_stream(io.BytesIO(streamed))[0], stream_fname
        )
        self.assertEqual(self._temps(), before, "a dedup hit left a temp behind")

    def test_empty_stream_stays_inline_and_stages_nothing(self):
        before = self._temps()
        fname, size, checksum = self.Attachment._write_file_stream(io.BytesIO(b""))
        self.assertEqual(fname, "")
        self.assertEqual(size, 0)
        self.assertEqual(checksum, self.Attachment._get_content_checksum(b""))
        self.assertEqual(self._temps(), before)

    @mute_logger("odoo.addons.base.models.ir_attachment")
    def test_a_failed_stage_never_leaks_its_temp(self):
        before = self._temps()
        boom = OSError("disk on fire")

        def exploding_replace(self, target):
            raise boom

        self.patch(Path, "replace", exploding_replace)
        with self.assertRaises(OSError):
            self.Attachment._write_file(b"never-lands" * 8, "deadbeef" * 8)
        self.assertEqual(self._temps(), before, "buffered writer leaked a temp")

        with self.assertRaises(OSError):
            self.Attachment._write_file_stream(io.BytesIO(b"never-lands" * 8))
        self.assertEqual(self._temps(), before, "streaming writer leaked a temp")

    def test_content_comparison_helpers_agree(self):
        payload = b"compare-me" * 9
        checksum = self.Attachment._get_content_checksum(payload)
        path = self.Attachment._get_full_path(
            self.Attachment._write_file(payload, checksum)
        )

        self.assertTrue(self.Attachment._is_same_bytes_as_file(payload, path))
        self.assertFalse(self.Attachment._is_same_bytes_as_file(payload + b"!", path))
        self.assertFalse(
            self.Attachment._is_same_bytes_as_file(b"Z" * len(payload), path)
        )
        self.assertTrue(self.Attachment._is_same_file(path, path))

        other = b"different" * 9
        other_path = self.Attachment._get_full_path(
            self.Attachment._write_file(
                other, self.Attachment._get_content_checksum(other)
            )
        )
        self.assertFalse(self.Attachment._is_same_file(path, other_path))

    def test_all_readers_resolve_the_same_content_location(self):
        payload = b"precedence" * 7

        on_disk = self.Attachment.create({"name": "disk.bin", "raw": payload})
        self.env.flush_all()
        self.assertTrue(on_disk.store_fname)
        self.assertEqual(on_disk.raw, payload)
        self.assertEqual(on_disk._get_content_prefix(), payload)
        self.assertEqual(on_disk._to_http_stream().type, "path")

        self.env["ir.config_parameter"].sudo().set_param("ir_attachment.location", "db")
        in_db = self.Attachment.create({"name": "db.bin", "raw": payload})
        self.env.flush_all()
        self.env["ir.config_parameter"].sudo().set_param(
            "ir_attachment.location", "file"
        )
        self.assertFalse(in_db.store_fname)
        self.assertEqual(in_db.raw, payload)
        self.assertEqual(in_db._get_content_prefix(), payload)
        db_stream = in_db._to_http_stream()
        self.assertEqual(db_stream.type, "data")
        self.assertEqual(db_stream.data, payload)

        remote = self.Attachment.create(
            {"name": "remote", "type": "url", "url": "https://example.com/x.png"}
        )
        self.assertFalse(remote.raw)
        self.assertEqual(remote._get_content_prefix(), b"")
        self.assertEqual(remote._to_http_stream().type, "url")

        empty = self.Attachment.create({"name": "empty.bin"})
        self.assertFalse(empty.raw)
        self.assertEqual(empty._get_content_prefix(), b"")
        empty_stream = empty._to_http_stream()
        self.assertEqual(empty_stream.type, "data")
        self.assertEqual(empty_stream.size, 0)

    def test_fetch_content_answers_the_stored_bytes(self):
        """Without a provider, fetching is reading: same bytes, same prefix.

        The method exists so a provider module can override it; base must
        answer exactly what this database holds, or every caller that moved to
        it would read something different from `_get_content_prefix`.
        """
        payload = b"the-content" * 4
        on_disk = self.Attachment.create({"name": "disk.bin", "raw": payload})
        self.env.flush_all()
        self.assertEqual(on_disk._fetch_content(), payload)
        self.assertEqual(on_disk._fetch_content(5), payload[:5])

        bare = self.Attachment.create({"name": "bare.bin"})
        self.assertEqual(bare._fetch_content(), b"")

    def test_store_key_wins_over_inline_data_for_every_reader(self):
        payload = b"the-real-content" * 5
        attachment = self.Attachment.create({"name": "both.bin", "raw": payload})
        self.env.flush_all()
        self.assertTrue(attachment.store_fname)

        self.env.cr.execute(
            "UPDATE ir_attachment SET db_datas = %s WHERE id = %s",
            [b"decoy-inline-content", attachment.id],
        )
        attachment.invalidate_recordset()

        self.assertEqual(attachment.raw, payload, "raw took the decoy")
        self.assertEqual(
            attachment._get_content_prefix(),
            payload,
            "_get_content_prefix took the decoy",
        )
        self.assertEqual(
            attachment._to_http_stream().type,
            "path",
            "_to_http_stream took the decoy",
        )


class TestBinSizeIsNeverContent(TransactionCaseWithUserDemo):
    def setUp(self):
        super().setUp()
        self.Attachment = self.env["ir.attachment"]
        self.payload = b"REAL-CONTENT-" + b"z" * 5000

    def _sized(self, records):
        return records.with_context(bin_size=True)

    def _reread(self, record):
        self.env.flush_all()
        self.env.invalidate_all()
        return self.Attachment.browse(record.id)

    def test_bin_size_really_hides_the_payload(self):
        attachment = self.Attachment.create({"name": "p.bin", "raw": self.payload})
        attachment = self._reread(attachment)
        self.assertEqual(
            self._sized(attachment).raw,
            human_size(len(self.payload)).encode(),
            "bin_size no longer substitutes the size; these tests need a new premise",
        )

    def test_content_write_under_bin_size_keeps_the_bytes(self):
        for key, value in (
            ("raw", self.payload),
            ("datas", base64.b64encode(self.payload)),
        ):
            with self.subTest(key=key):
                attachment = self.Attachment.create(
                    {"name": f"w-{key}.bin", "raw": b"initial"}
                )
                attachment = self._reread(attachment)
                self._sized(attachment).write({key: value})
                attachment = self._reread(attachment)
                self.assertEqual(attachment.raw, self.payload)
                self.assertEqual(attachment.file_size, len(self.payload))

    def test_copy_under_bin_size_keeps_the_bytes(self):
        for location in ("db", "file"):
            with self.subTest(location=location):
                self.env["ir.config_parameter"].set_param(
                    "ir_attachment.location", location
                )
                origin = self.Attachment.create(
                    {"name": f"c-{location}.bin", "raw": self.payload}
                )
                origin = self._reread(origin)
                copied = self._reread(self._sized(origin).copy())
                self.assertEqual(copied.raw, self.payload)
                self.assertEqual(copied.file_size, len(self.payload))

    def test_pdf_raw_under_bin_size_keeps_the_bytes(self):
        pdf = b"%PDF-1.4\n" + b"x" * 3000
        attachment = self.Attachment.create(
            {"name": "d.pdf", "raw": pdf, "mimetype": "application/pdf"}
        )
        attachment = self._reread(attachment)
        self.assertEqual(self._sized(attachment)._get_pdf_raw(), pdf)

    def test_per_field_bin_size_is_neutralized_too(self):
        attachment = self.Attachment.create({"name": "pf.bin", "raw": self.payload})
        attachment = self._reread(attachment)
        scoped = attachment.with_context(bin_size_raw=True, bin_size_db_datas=True)
        self.assertEqual(scoped._get_stored_content(), self.payload)
        self.assertEqual(scoped._get_content_prefix(), self.payload)
        self.assertEqual(scoped._with_bin_size_disabled().raw, self.payload)

        scoped.write({"raw": b"replacement-payload"})
        self.assertEqual(self._reread(attachment).raw, b"replacement-payload")

    def test_per_field_bin_size_does_not_poison_plain_readers(self):
        attachment = self.Attachment.create({"name": "poison.bin", "raw": self.payload})
        attachment = self._reread(attachment)

        sized = attachment.with_context(bin_size_raw=True).raw
        self.assertEqual(sized, human_size(len(self.payload)).encode())
        self.assertEqual(
            self.Attachment.browse(attachment.id).raw,
            self.payload,
            "a bin_size_<field> read answered a caller that never asked for it",
        )

    def test_per_field_flags_shorten_only_their_own_field(self):
        attachment = self.Attachment.create({"name": "ind.bin", "raw": self.payload})
        attachment = self._reread(attachment)
        size = human_size(len(self.payload)).encode()

        raw_only = attachment.with_context(bin_size_raw=True)
        self.assertEqual(raw_only.raw, size)
        self.assertEqual(
            base64.b64decode(raw_only.datas),
            self.payload,
            "bin_size_raw shortened datas as well",
        )

        self.env.invalidate_all()
        datas_only = self.Attachment.browse(attachment.id).with_context(
            bin_size_datas=True
        )
        self.assertEqual(datas_only.datas, size)
        self.assertEqual(
            datas_only.raw, self.payload, "bin_size_datas shortened raw as well"
        )

    def test_attachment_backed_host_field_ignores_the_storage_flags(self):
        image = image_to_base64(Image.new("RGB", (4, 4)), "PNG")
        partner = self.env["res.partner"].create({"name": "host", "image_1920": image})
        self.env.flush_all()

        for flag in ("bin_size_datas", "bin_size_raw", "bin_size_db_datas"):
            with self.subTest(flag=flag):
                self.env.invalidate_all()
                scoped = self.env["res.partner"].browse(partner.id)
                self.assertTrue(
                    scoped.with_context(**{flag: True}).image_1920.startswith(b"iVBOR"),
                    f"{flag} shortened a field it does not name",
                )
                self.assertTrue(
                    self.env["res.partner"]
                    .browse(partner.id)
                    .image_1920.startswith(b"iVBOR"),
                    f"a {flag} read answered a caller that never asked for it",
                )

    def test_attachment_backed_host_field_honours_its_own_flag(self):
        image = image_to_base64(Image.new("RGB", (4, 4)), "PNG")
        partner = self.env["res.partner"].create({"name": "host", "image_1920": image})
        self.env.flush_all()
        self.env.invalidate_all()

        scoped = self.env["res.partner"].browse(partner.id)
        self.assertEqual(
            scoped.with_context(bin_size_image_1920=True).image_1920,
            scoped.with_context(bin_size=True).image_1920,
        )
        self.assertTrue(
            self.env["res.partner"].browse(partner.id).image_1920.startswith(b"iVBOR")
        )

    def test_unsized_is_a_no_op_without_bin_size(self):
        attachment = self.Attachment.create({"name": "n.bin", "raw": b"x"})
        self.assertIs(attachment._with_bin_size_disabled(), attachment)
        self.assertIsNot(
            self._sized(attachment)._with_bin_size_disabled(), self._sized(attachment)
        )


class TestDedupOwnership(TransactionCaseWithUserDemo):
    def setUp(self):
        super().setUp()
        self.Attachment = self.env["ir.attachment"]
        self.payload = b"SHARED-DEDUP-PAYLOAD"
        self.partner = self.env["res.partner"].create({"name": "dedup host"})

    def _field_row(self):
        row = self.Attachment.sudo().create(
            {
                "name": "image_1920",
                "res_model": "res.partner",
                "res_field": "image_1920",
                "res_id": self.partner.id,
                "type": "binary",
                "raw": self.payload,
                "mimetype": "image/png",
            }
        )
        self.env.flush_all()
        return row

    def _create_unique(self):
        return self.Attachment.create_unique(
            [
                {
                    "name": "mine.png",
                    "datas": base64.b64encode(self.payload),
                    "mimetype": "image/png",
                }
            ]
        )

    def test_create_unique_never_reuses_a_field_backing_row(self):
        field_row = self._field_row()
        [reused] = self._create_unique()
        self.assertNotEqual(
            reused,
            field_row.id,
            "create_unique reused an attachment owned by another record's field",
        )
        self.assertFalse(self.Attachment.browse(reused).res_field)
        self.assertEqual(self.Attachment.browse(reused).raw, self.payload)

    def test_a_res_field_value_never_reuses_anything(self):
        free = self.Attachment.create(
            {"name": "free.png", "raw": self.payload, "mimetype": "image/png"}
        )
        self.env.flush_all()

        [created] = self.Attachment.sudo().create_unique(
            [
                {
                    "name": "image_1920",
                    "raw": self.payload,
                    "mimetype": "image/png",
                    "res_model": "res.partner",
                    "res_field": "image_1920",
                    "res_id": self.partner.id,
                }
            ]
        )
        self.assertNotEqual(created, free.id, "a res_field value reused another row")
        backing = self.Attachment.with_context(skip_res_field_check=True).browse(
            created
        )
        self.assertEqual(backing.res_field, "image_1920")
        self.assertEqual(backing.res_id, self.partner.id)

    def test_a_res_field_value_is_never_reused_within_its_own_batch(self):
        [backed, standalone] = self.Attachment.sudo().create_unique(
            [
                {
                    "name": "image_1920",
                    "raw": self.payload,
                    "mimetype": "image/png",
                    "res_model": "res.partner",
                    "res_field": "image_1920",
                    "res_id": self.partner.id,
                },
                {
                    "name": "standalone.png",
                    "raw": self.payload,
                    "mimetype": "image/png",
                },
            ]
        )
        self.assertNotEqual(backed, standalone)
        self.assertFalse(self.Attachment.browse(standalone).res_field)
        self.assertEqual(self.Attachment.browse(standalone).raw, self.payload)

    def test_reused_row_survives_its_lookalike_host(self):
        field_row = self._field_row()
        [reused] = self._create_unique()
        self.env.flush_all()

        self.partner.unlink()
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertFalse(
            field_row.sudo().with_context(skip_res_field_check=True).exists(),
            "the host record must still own its field attachment",
        )
        self.assertTrue(
            self.Attachment.browse(reused).exists(),
            "deleting an unrelated record deleted the caller's attachment",
        )
        self.assertEqual(self.Attachment.browse(reused).raw, self.payload)

    def test_create_unique_still_dedups_free_standing_rows(self):
        free = self.Attachment.create(
            {"name": "free.png", "raw": self.payload, "mimetype": "image/png"}
        )
        self.env.flush_all()
        self.assertEqual(self._create_unique(), [free.id])

    def test_create_unique_never_reuses_a_record_owned_row(self):
        owned = self.Attachment.create(
            {
                "name": "host-doc.png",
                "raw": self.payload,
                "mimetype": "image/png",
                "res_model": "res.partner",
                "res_id": self.partner.id,
            }
        )
        self.env.flush_all()
        [reused] = self._create_unique()
        self.assertNotEqual(
            reused,
            owned.id,
            "create_unique reused a row owned by an unrelated record",
        )

    def test_a_reused_row_outlives_the_record_the_caller_never_named(self):
        self.Attachment.create(
            {
                "name": "host-doc.png",
                "raw": self.payload,
                "mimetype": "image/png",
                "res_model": "res.partner",
                "res_id": self.partner.id,
            }
        )
        self.env.flush_all()
        [reused] = self._create_unique()
        self.env.flush_all()

        self.partner.unlink()
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertTrue(
            self.Attachment.browse(reused).exists(),
            "BaseModel.unlink cascades on res_model/res_id, so a reused "
            "record-owned row dies with a record the caller never asked for",
        )
        self.assertEqual(self.Attachment.browse(reused).raw, self.payload)

    def test_create_unique_dedups_within_the_owner_the_caller_asked_for(self):
        owner = {"res_model": "res.partner", "res_id": self.partner.id}
        first = self.Attachment.create(
            {
                "name": "same-owner.png",
                "raw": self.payload,
                "mimetype": "image/png",
                **owner,
            }
        )
        self.env.flush_all()
        [reused] = self.Attachment.create_unique(
            [
                {
                    "name": "same-owner-again.png",
                    "raw": self.payload,
                    "mimetype": "image/png",
                    **owner,
                }
            ]
        )
        self.assertEqual(
            reused,
            first.id,
            "dedup must still reuse a row under the owner the caller named",
        )


class TestCreateUniqueAccessControl(TransactionCaseWithUserPortal):
    def test_create_unique_denies_a_portal_user_without_comodel_access(self):
        partner = self.env["res.partner"].create({"name": "ATT-1 host"})
        payload = b"ATT-1-portal-cannot-read-this"
        self.env["ir.attachment"].sudo().create(
            {
                "name": "seed",
                "mimetype": "text/plain",
                "raw": payload,
                "res_model": "res.partner",
                "res_id": partner.id,
            }
        )
        self.env.flush_all()

        with self.assertRaises(
            AccessError,
            msg="create_unique must not hand back a dedup match on a record "
            "the caller cannot write to (ATT-1)",
        ):
            self.env["ir.attachment"].with_user(self.user_portal).create_unique(
                [
                    {
                        "name": "dup",
                        "mimetype": "text/plain",
                        "raw": payload,
                        "res_model": "res.partner",
                        "res_id": partner.id,
                    }
                ]
            )


class TestGcChecklistAddressing(TransactionCaseWithUserDemo):
    def setUp(self):
        super().setUp()
        self.Attachment = self.env["ir.attachment"]
        self.checklist = self.Attachment._get_filestore_dir("checklist")

    def test_a_stray_marker_never_unlinks_an_unrelated_file(self):
        live = self.Attachment.create({"name": "live.bin", "raw": b"live-content"})
        self.env.flush_all()
        victim = Path(self.Attachment._get_full_path(live.store_fname))
        self.assertTrue(victim.is_file())

        shard, _, digest = live.store_fname.rpartition("/")
        stray = self.checklist / shard / f"{digest[:-2]}.{digest[-2:]}"
        stray.parent.mkdir(parents=True, exist_ok=True)
        stray.write_bytes(b"")
        self.addCleanup(stray.unlink, True)
        self.assertNotEqual(
            self.Attachment._normalize_store_key(
                str(stray.relative_to(self.checklist))
            ),
            str(stray.relative_to(self.checklist)),
            "this test needs a name the sanitizer rewrites",
        )

        self.Attachment._gc_file_store_unsafe(
            self.Attachment._get_gc_checklist(grace=0), grace=0
        )

        self.assertTrue(
            victim.is_file(),
            "the sweep unlinked a file no checklist entry named",
        )
        self.assertEqual(live.raw, b"live-content")

    @mute_logger("odoo.addons.base.models.ir_attachment")
    def test_a_refused_store_key_does_not_stop_the_sweep(self):
        live = self.Attachment.create({"name": "live.bin", "raw": b"survivor"})
        self.env.flush_all()
        victim = Path(self.Attachment._get_full_path(live.store_fname))
        self.assertTrue(victim.is_file())

        filestore = Path(self.Attachment._get_filestore())
        outside = filestore.parent / "ira_outside_the_filestore"
        outside.mkdir(parents=True, exist_ok=True)
        self.addCleanup(outside.rmdir)
        escaping_shard = filestore / "zz"
        escaping_shard.symlink_to(outside)
        self.addCleanup(escaping_shard.unlink)

        refused = "zz/" + "a" * 40
        with self.assertRaises(ValueError):
            self.Attachment._get_full_path(refused)
        marker = self.checklist / refused
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_bytes(b"")
        self.addCleanup(marker.unlink, True)

        collectable = self.Attachment.create({"name": "gone.bin", "raw": b"collect-me"})
        self.env.flush_all()
        orphan = Path(self.Attachment._get_full_path(collectable.store_fname))
        orphan_key = collectable.store_fname
        collectable.unlink()
        self.env.flush_all()

        self.Attachment._gc_file_store_unsafe(
            {refused: marker, orphan_key: self.checklist / orphan_key}, grace=0
        )

        self.assertFalse(marker.is_file(), "the refused marker was left to recur")
        self.assertFalse(
            orphan.is_file(),
            "a refused entry stopped the sweep before the collectable ones",
        )
        self.assertFalse((self.checklist / orphan_key).is_file())
        self.assertTrue(victim.is_file())
        self.assertEqual(live.raw, b"survivor")

    def test_content_is_marked_before_it_is_published(self):
        payload = b"marked-before-published"
        checksum = self.Attachment._get_content_checksum(payload)
        fname = self.Attachment._get_store_key(checksum)
        marker = self.checklist / fname
        marker.unlink(missing_ok=True)
        Path(self.Attachment._get_full_path(fname)).unlink(missing_ok=True)

        published = []
        original = Path.replace

        def spy(self, target):
            published.append(marker.exists())
            return original(self, target)

        self.patch(Path, "replace", spy)
        self.Attachment._write_file(payload, checksum)

        self.assertEqual(
            published,
            [True],
            "the content was published before its GC marker existed",
        )

    def test_streamed_content_is_marked_before_it_is_published(self):
        payload = b"streamed-marked-before-published"
        checksum = self.Attachment._get_content_checksum(payload)
        fname = self.Attachment._get_store_key(checksum)
        marker = self.checklist / fname
        marker.unlink(missing_ok=True)
        Path(self.Attachment._get_full_path(fname)).unlink(missing_ok=True)

        published = []
        original = Path.replace

        def spy(self, target):
            published.append(marker.exists())
            return original(self, target)

        self.patch(Path, "replace", spy)
        self.Attachment._write_file_stream(io.BytesIO(payload))

        self.assertEqual(published, [True])


class TestAccessibleIdScanFootprint(TransactionCaseWithUserDemo):
    def setUp(self):
        super().setUp()
        self.Attachment = self.env["ir.attachment"]
        self.user = (
            self.env["res.users"]
            .sudo()
            .create(
                {
                    "name": "Scan User",
                    "login": "scan_user",
                    "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
                }
            )
        )
        partner = self.env["res.partner"].create({"name": "scan host"})
        rows = 3 * PREFETCH_MAX + 17
        self.env.cr.execute(
            """
            INSERT INTO ir_attachment
                (name, type, res_model, res_id, public, create_uid, write_uid,
                 create_date, write_date, file_size, company_id)
            SELECT 'scan-' || g, 'binary', 'res.partner', %s, false, 1, 1,
                   now(), now(), 0, %s
            FROM generate_series(1, %s) g
            """,
            [partner.id, self.env.company.id, rows],
        )
        self.env.invalidate_all()
        self.expected = rows

    def _cached_security_rows(self):
        model = self.Attachment.with_user(self.user)
        return max(
            len(self.env.cache.get_records(model, model._fields[name]))
            for name in SECURITY_FIELDS
        )

    def test_unbounded_scan_keeps_only_one_batch_cached(self):
        scanned = self.Attachment.with_user(self.user)
        self.assertGreaterEqual(scanned.search_count([]), self.expected)
        self.assertLessEqual(
            self._cached_security_rows(),
            PREFETCH_MAX,
            "the access scan kept more than one batch of security fields cached",
        )

    def test_scan_still_agrees_with_the_authority(self):
        scanned = self.Attachment.with_user(self.user)
        found = scanned.search([("name", "=like", "scan-%")], order="id")
        self.env.invalidate_all()
        expected = (
            self.Attachment.sudo()
            .search([("name", "=like", "scan-%")], order="id")
            .with_user(self.user)
            ._filtered_access("read")
        )
        self.assertEqual(found.ids, expected.ids)

    def test_deep_paging_agrees_with_a_full_ordered_scan(self):
        scanned = self.Attachment.with_user(self.user)
        domain = [("name", "=like", "scan-%")]
        for order in ("id", "id desc"):
            with self.subTest(order=order):
                whole = scanned.search(domain, order=order).ids
                paged = []
                page = PREFETCH_MAX + 3
                for offset in range(0, len(whole), page):
                    paged.extend(
                        scanned.search(
                            domain, order=order, limit=page, offset=offset
                        ).ids
                    )
                self.assertEqual(paged, whole)


@tagged("post_install", "-at_install")
class TestFromRequestFileValsMerge(TransactionCase):
    class _FakeFile:
        def __init__(self, content, filename):
            self._buf = io.BytesIO(content)
            self.filename = filename
            self.content_type = "application/octet-stream"

        def read(self, size=-1):
            return self._buf.read(size)

        def seek(self, offset, whence=0):
            return self._buf.seek(offset, whence)

    def setUp(self):
        super().setUp()
        self.Attachments = self.env["ir.attachment"]
        self.png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
            b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        )
        self.assertFalse(self.Attachments._is_stream_upload_required("image/png"))
        self.assertTrue(self.Attachments._is_stream_upload_required("text/plain"))

    def test_caller_supplied_name_is_accepted_on_both_branches(self):
        for filename, content in (("photo.png", self.png), ("note.txt", b"hello")):
            with self.subTest(filename=filename):
                attachment = self.Attachments._create_from_request_file(
                    self._FakeFile(content, filename), name="chosen name"
                )
                self.assertEqual(
                    attachment.name,
                    "chosen name",
                    "an explicit name must win on both branches, not raise on one",
                )

    def test_linkage_vals_are_accepted_on_both_branches(self):
        partner = self.env["res.partner"].create({"name": "attachment target"})
        for filename, content in (("photo.png", self.png), ("note.txt", b"hello")):
            with self.subTest(filename=filename):
                attachment = self.Attachments._create_from_request_file(
                    self._FakeFile(content, filename),
                    res_model="res.partner",
                    res_id=partner.id,
                )
                self.assertEqual(attachment.res_model, "res.partner")
                self.assertEqual(attachment.res_id, partner.id)
                self.assertEqual(attachment.name, filename)

    def test_the_file_is_still_what_gets_stored(self):
        for filename, content in (("photo.png", self.png), ("note.txt", b"hello")):
            with self.subTest(filename=filename):
                attachment = self.Attachments._create_from_request_file(
                    self._FakeFile(content, filename), name="renamed"
                )
                self.assertEqual(attachment.raw, content)
