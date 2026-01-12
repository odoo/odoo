# Copyright 2023 ACSONE SA/NV (http://acsone.eu).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import os
from unittest import mock

from odoo.tools import mute_logger

from .common import MyException, TestFSAttachmentCommon


class TestFSAttachment(TestFSAttachmentCommon):
    def test_create_attachment_explicit_location(self):
        content = b"This is a test attachment"
        attachment = (
            self.env["ir.attachment"]
            .with_context(
                storage_location=self.temp_backend.code,
                force_storage_key="test.txt",
            )
            .create({"name": "test.txt", "raw": content})
        )
        self.assertEqual(os.listdir(self.temp_dir), [f"test-{attachment.id}-0.txt"])
        self.assertEqual(attachment.raw, content)
        self.assertFalse(attachment.db_datas)
        self.assertEqual(attachment.mimetype, "text/plain")
        with attachment.open("rb") as f:
            self.assertEqual(f.read(), content)

        with attachment.open("wb") as f:
            f.write(b"new")
        self.assertEqual(attachment.raw, b"new")

    def test_create_attachment_with_meaningful_name(self):
        """In this test we use a backend with 'optimizes_directory_path',
        which rewrites the filename to be a meaningful name.
        We ensure that the rewritten path is consistently used,
        meaning we can read the file after.
        """
        content = b"This is a test attachment"
        attachment = (
            self.env["ir.attachment"]
            .with_context(
                storage_location=self.backend_optimized.code,
                force_storage_key="test.txt",
            )
            .create({"name": "test.txt", "raw": content})
        )
        # the expected store_fname is made of the storage code,
        # a random middle part, and the filename
        # example: tmp_opt://te/st/test-198-0.txt
        # The storage root is NOT part of the store_fname
        self.assertFalse("tmp/" in attachment.store_fname)

        # remove protocol and file name to keep the middle part
        sub_path = os.path.dirname(attachment.store_fname.split("://")[1])
        # the subpath is consistently 'te/st' because the file storage key is forced
        # if it's arbitrary we might get a random name (3fbc5er....txt), in which case
        # the middle part would also be 'random', in our example 3f/bc
        self.assertEqual(sub_path, "te/st")

        # we can read the file, so storage finds it correctly
        with attachment.open("rb") as f:
            self.assertEqual(f.read(), content)

        new_content = b"new content"
        with attachment.open("wb") as f:
            f.write(new_content)

        # the store fname should have changed, as its version number has increased
        # e.g. tmp_opt://te/st/test-1766-0.txt to tmp_opt://te/st/test-1766-1.txt
        # but the protocol and sub path should be the same
        new_sub_path = os.path.dirname(attachment.store_fname.split("://")[1])
        self.assertEqual(sub_path, new_sub_path)

        with attachment.open("rb") as f:
            self.assertEqual(f.read(), new_content)

    def test_open_attachment_in_db(self):
        self.env["ir.config_parameter"].sudo().set_param("ir_attachment.location", "db")
        content = b"This is a test attachment in db"
        attachment = self.ir_attachment_model.create(
            {"name": "test.txt", "raw": content}
        )
        self.assertFalse(attachment.store_fname)
        self.assertTrue(attachment.db_datas)
        self.assertEqual(attachment.mimetype, "text/plain")
        with attachment.open("rb") as f:
            self.assertEqual(f.read(), content)
        with attachment.open("wb") as f:
            f.write(b"new")
        self.assertEqual(attachment.raw, b"new")

    def test_attachment_open_in_filestore(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "ir_attachment.location", "file"
        )
        content = b"This is a test attachment in filestore"
        attachment = self.ir_attachment_model.create(
            {"name": "test.txt", "raw": content}
        )
        self.assertTrue(attachment.store_fname)
        self.assertFalse(attachment.db_datas)
        self.assertEqual(attachment.raw, content)
        with attachment.open("rb") as f:
            self.assertEqual(f.read(), content)
        with attachment.open("wb") as f:
            f.write(b"new")
        self.assertEqual(attachment.raw, b"new")

    def test_default_attachment_store_in_fs(self):
        self.temp_backend.use_as_default_for_attachments = True
        content = b"This is a test attachment in filestore tmp_dir"
        attachment = self.ir_attachment_model.create(
            {"name": "test.txt", "raw": content}
        )
        self.assertTrue(attachment.store_fname)
        self.assertFalse(attachment.db_datas)
        self.assertEqual(attachment.raw, content)
        self.assertEqual(attachment.mimetype, "text/plain")
        self.env.flush_all()

        initial_filename = f"test-{attachment.id}-0.txt"

        self.assertEqual(os.listdir(self.temp_dir), [initial_filename])

        with attachment.open("rb") as f:
            self.assertEqual(f.read(), content)

        with open(os.path.join(self.temp_dir, initial_filename), "rb") as f:
            self.assertEqual(f.read(), content)

        # update the attachment
        attachment.raw = b"new"
        with attachment.open("rb") as f:
            self.assertEqual(f.read(), b"new")
        # a new file version is created
        new_filename = f"test-{attachment.id}-1.txt"
        with open(os.path.join(self.temp_dir, new_filename), "rb") as f:
            self.assertEqual(f.read(), b"new")
        self.assertEqual(attachment.raw, b"new")
        self.assertEqual(attachment.store_fname, f"tmp_dir://{new_filename}")
        self.assertEqual(attachment.mimetype, "text/plain")

        # the original file is to to be deleted by the GC
        self.assertEqual(
            set(os.listdir(self.temp_dir)), {initial_filename, new_filename}
        )

        # run the GC
        self.env.flush_all()
        self.gc_file_model._gc_files_unsafe()
        self.assertEqual(os.listdir(self.temp_dir), [new_filename])

        attachment.unlink()
        # concrete file deletion is done by the GC
        self.env.flush_all()
        self.assertEqual(os.listdir(self.temp_dir), [new_filename])
        # run the GC
        self.gc_file_model._gc_files_unsafe()
        self.assertEqual(os.listdir(self.temp_dir), [])

    def test_fs_update_transactionnal(self):
        """In this test we check that if a rollback is done on an update
        The original content is preserved
        """
        self.temp_backend.use_as_default_for_attachments = True
        content = b"Transactional update"
        attachment = self.ir_attachment_model.create(
            {"name": "test.txt", "raw": content}
        )
        self.env.flush_all()
        self.assertEqual(attachment.raw, content)

        initial_filename = f"test-{attachment.id}-0.txt"

        self.assertEqual(attachment.store_fname, f"tmp_dir://{initial_filename}")
        self.assertEqual(attachment.fs_filename, initial_filename)
        self.assertEqual(
            os.listdir(self.temp_dir), [os.path.basename(initial_filename)]
        )

        orignal_store_fname = attachment.store_fname
        try:
            with self.env.cr.savepoint():
                attachment.raw = b"updated"
                new_filename = f"test-{attachment.id}-1.txt"
                new_store_fname = f"tmp_dir://{new_filename}"
                self.assertEqual(attachment.store_fname, new_store_fname)
                self.assertEqual(attachment.fs_filename, new_filename)
                # at this stage the original file and the new file are present
                # in the list of files to GC
                gc_files = self.gc_file_model.search([]).mapped("store_fname")
                self.assertIn(orignal_store_fname, gc_files)
                self.assertIn(orignal_store_fname, gc_files)
                raise MyException("dummy exception")
        except MyException:
            ...
        self.assertEqual(attachment.store_fname, f"tmp_dir://{initial_filename}")
        self.assertEqual(attachment.fs_filename, initial_filename)
        self.assertEqual(attachment.raw, content)
        self.assertEqual(attachment.mimetype, "text/plain")
        self.assertEqual(
            set(os.listdir(self.temp_dir)),
            {os.path.basename(initial_filename), os.path.basename(new_filename)},
        )
        # in test mode, gc collector is not run into a separate transaction
        # therefore it has been reset. We manually add our two store_fname
        # to the list of files to GC
        self.gc_file_model._mark_for_gc(orignal_store_fname)
        self.gc_file_model._mark_for_gc(new_store_fname)
        # run gc
        self.gc_file_model._gc_files_unsafe()
        self.assertEqual(
            os.listdir(self.temp_dir), [os.path.basename(initial_filename)]
        )

    def test_fs_create_transactional(self):
        """In this test we check that if a rollback is done on a create
        The file is removed
        """
        self.temp_backend.use_as_default_for_attachments = True
        content = b"Transactional create"
        try:
            with self.env.cr.savepoint():
                attachment = self.ir_attachment_model.create(
                    {"name": "test.txt", "raw": content}
                )
                self.env.flush_all()
                self.assertEqual(attachment.raw, content)
                initial_filename = f"test-{attachment.id}-0.txt"
                self.assertEqual(
                    attachment.store_fname, f"tmp_dir://{initial_filename}"
                )
                self.assertEqual(attachment.fs_filename, initial_filename)
                self.assertEqual(
                    os.listdir(self.temp_dir), [os.path.basename(initial_filename)]
                )
                new_store_fname = attachment.store_fname
                # at this stage the new file is into the list of files to GC
                gc_files = self.gc_file_model.search([]).mapped("store_fname")
                self.assertIn(new_store_fname, gc_files)
                raise MyException("dummy exception")
        except MyException:
            ...
        self.env.flush_all()
        # in test mode, gc collector is not run into a separate transaction
        # therefore it has been reset. We manually add our new file to the
        # list of files to GC
        self.gc_file_model._mark_for_gc(new_store_fname)
        # run gc
        self.gc_file_model._gc_files_unsafe()
        self.assertEqual(os.listdir(self.temp_dir), [])

    def test_fs_no_delete_if_not_in_current_directory_path(self):
        """In this test we check that it's not possible to removes files
        outside the current directory path even if they were created by the
        current filesystem storage.
        """
        # normal delete
        self.temp_backend.use_as_default_for_attachments = True
        content = b"Transactional create"
        attachment = self.ir_attachment_model.create(
            {"name": "test.txt", "raw": content}
        )
        self.env.flush_all()
        initial_filename = f"test-{attachment.id}-0.txt"
        self.assertEqual(
            os.listdir(self.temp_dir), [os.path.basename(initial_filename)]
        )
        attachment.unlink()
        self.gc_file_model._gc_files_unsafe()
        self.assertEqual(os.listdir(self.temp_dir), [])
        # delete outside the current directory path
        attachment = self.ir_attachment_model.create(
            {"name": "test.txt", "raw": content}
        )
        self.env.flush_all()
        initial_filename = f"test-{attachment.id}-0.txt"
        self.assertEqual(
            os.listdir(self.temp_dir), [os.path.basename(initial_filename)]
        )
        self.temp_backend.directory_path = "/dummy"
        attachment.unlink()
        self.gc_file_model._gc_files_unsafe()
        # unlink is not physically done since the file is outside the current
        self.assertEqual(
            os.listdir(self.temp_dir), [os.path.basename(initial_filename)]
        )

    def test_no_gc_if_disabled_on_storage(self):
        store_fname = "tmp_dir://dummy-0-0.txt"
        self.gc_file_model._mark_for_gc(store_fname)
        self.temp_backend.autovacuum_gc = False
        self.gc_file_model._gc_files_unsafe()
        self.assertIn(store_fname, self.gc_file_model.search([]).mapped("store_fname"))
        self.temp_backend.autovacuum_gc = False
        self.gc_file_model._gc_files_unsafe()
        self.assertIn(store_fname, self.gc_file_model.search([]).mapped("store_fname"))
        self.temp_backend.autovacuum_gc = True
        self.gc_file_model._gc_files_unsafe()
        self.assertNotIn(
            store_fname, self.gc_file_model.search([]).mapped("store_fname")
        )

    def test_attachment_fs_url(self):
        self.temp_backend.base_url = "https://acsone.eu/media"
        self.temp_backend.use_as_default_for_attachments = True
        content = b"Transactional update"
        attachment = self.ir_attachment_model.create(
            {"name": "test.txt", "raw": content}
        )
        self.env.flush_all()
        attachment_path = f"/test-{attachment.id}-0.txt"
        self.assertEqual(attachment.fs_url, f"https://acsone.eu/media{attachment_path}")
        self.assertEqual(attachment.fs_url_path, attachment_path)

        self.temp_backend.is_directory_path_in_url = True
        self.temp_backend.recompute_urls()
        attachment_path = f"{self.temp_dir}/test-{attachment.id}-0.txt"
        self.assertEqual(attachment.fs_url, f"https://acsone.eu/media{attachment_path}")
        self.assertEqual(attachment.fs_url_path, attachment_path)

    def test_force_attachment_in_db_rules(self):
        self.temp_backend.use_as_default_for_attachments = True
        # force storage in db for text/plain
        self.temp_backend.force_db_for_default_attachment_rules = '{"text/plain": 0}'
        attachment = self.ir_attachment_model.create(
            {"name": "test.txt", "raw": b"content"}
        )
        self.env.flush_all()
        self.assertFalse(attachment.store_fname)
        self.assertEqual(attachment.db_datas, b"content")
        self.assertEqual(attachment.mimetype, "text/plain")

    def test_force_storage_to_db(self):
        self.temp_backend.use_as_default_for_attachments = True
        attachment = self.ir_attachment_model.create(
            {"name": "test.txt", "raw": b"content"}
        )
        self.env.flush_all()
        self.assertTrue(attachment.store_fname)
        self.assertFalse(attachment.db_datas)
        store_fname = attachment.store_fname
        # we change the rules to force the storage in db for text/plain
        self.temp_backend.force_db_for_default_attachment_rules = '{"text/plain": 0}'
        attachment.force_storage_to_db_for_special_fields()
        self.assertFalse(attachment.store_fname)
        self.assertEqual(attachment.db_datas, b"content")
        # we check that the file is marked for GC
        gc_files = self.gc_file_model.search([]).mapped("store_fname")
        self.assertIn(store_fname, gc_files)

    @mute_logger("odoo.addons.fs_attachment.models.ir_attachment")
    def test_force_storage_to_fs(self):
        attachment = self.ir_attachment_model.create(
            {"name": "test.txt", "raw": b"content"}
        )
        self.env.flush_all()
        fs_path = self.ir_attachment_model._filestore() + "/" + attachment.store_fname
        self.assertTrue(os.path.exists(fs_path))
        self.assertEqual(os.listdir(self.temp_dir), [])
        # we decide to force the storage in the filestore
        self.temp_backend.use_as_default_for_attachments = True
        with (
            mock.patch.object(self.env.cr, "commit"),
            mock.patch(
                "odoo.addons.fs_attachment.models.ir_attachment.clean_fs"
            ) as clean_fs,
        ):
            self.ir_attachment_model.force_storage()
            clean_fs.assert_called_once()
        # files into the filestore must be moved to our filesystem storage
        filename = f"test-{attachment.id}-0.txt"
        self.assertEqual(attachment.store_fname, f"tmp_dir://{filename}")
        self.assertIn(filename, os.listdir(self.temp_dir))

    def test_storage_use_filename_obfuscation(self):
        self.temp_backend.base_url = "https://acsone.eu/media"
        self.temp_backend.use_as_default_for_attachments = True
        self.temp_backend.use_filename_obfuscation = True
        attachment = self.ir_attachment_model.create(
            {"name": "test.txt", "raw": b"content"}
        )
        self.env.flush_all()
        self.assertTrue(attachment.store_fname)
        self.assertEqual(attachment.name, "test.txt")
        self.assertEqual(attachment.checksum, attachment.store_fname.split("/")[-1])
        self.assertEqual(attachment.checksum, attachment.fs_url.split("/")[-1])
        self.assertEqual(attachment.mimetype, "text/plain")

    def test_create_attachments_basic_user(self):
        demo_user = self.env.ref("base.user_demo")
        demo_partner = self.env.ref("base.partner_demo")
        self.temp_backend.use_as_default_for_attachments = True
        # Ensure basic access
        group_user = self.env.ref("base.group_user")
        group_partner_manager = self.env.ref("base.group_partner_manager")
        demo_user.write(
            {"groups_id": [(6, 0, [group_user.id, group_partner_manager.id])]}
        )
        # Create basic attachment
        self.ir_attachment_model.with_user(demo_user).create(
            {"name": "test.txt", "raw": b"content"}
        )
        # Create attachment related to model
        self.ir_attachment_model.with_user(demo_user).create(
            {
                "name": "test.txt",
                "raw": b"content",
                "res_model": "res.partner",
                "res_id": demo_partner.id,
            }
        )
        # Create attachment related to field
        partner_image_field = self.env["ir.model.fields"].search(
            [("model", "=", "res.partner"), ("name", "=", "image1920")]
        )
        self.ir_attachment_model.with_user(demo_user).create(
            {
                "name": "test.txt",
                "raw": b"content",
                "res_model": "res.partner",
                "res_id": demo_partner.id,
                "res_field": partner_image_field.name,
            }
        )

    def test_update_png_to_svg(self):
        b64_data_png = (
            b"iVBORw0KGgoAAAANSUhEUgAAADMAAAAhCAIAAAD73QTtAAAAA3NCSVQICAjb4U/gAA"
            b"AAP0lEQVRYhe3OMQGAMBAAsVL/nh8FDDfxQ6Igz8ycle7fgU9mnVln1pl1Zp1ZZ9aZd"
            b"WadWWfWmXVmnVln1u2dvfL/Az+TRcv4AAAAAElFTkSuQmCC"
        )

        attachment = self.ir_attachment_model.create(
            {
                "name": "test.png",
                "datas": b64_data_png,
            }
        )
        self.assertEqual(attachment.mimetype, "image/png")

        b64_data_svg = (
            b"PD94bWwgdmVyc2lvbj0iMS4wIiBzdGFuZGFsb25lPSJubyI/Pgo8IURPQ1RZUEU"
            b"gc3ZnIFBVQkxJQyAiLS8vVzNDLy9EVEQgU1ZHIDIwMDEwOTA0Ly9FTiIKICJodH"
            b"RwOi8vd3d3LnczLm9yZy9UUi8yMDAxL1JFQy1TVkctMjAwMTA5MDQvRFREL3N2Zz"
            b"EwLmR0ZCI+CjxzdmcgdmVyc2lvbj0iMS4wIiB4bWxucz0iaHR0cDovL3d3dy53My5"
            b"vcmcvMjAwMC9zdmciCiB3aWR0aD0iNTEuMDAwMDAwcHQiIGhlaWdodD0iMzMuMDAw"
            b"MDAwcHQiIHZpZXdCb3g9IjAgMCA1MS4wMDAwMDAgMzMuMDAwMDAwIgogcHJlc2Vydm"
            b"VBc3BlY3RSYXRpbz0ieE1pZFlNaWQgbWVldCI+Cgo8ZyB0cmFuc2Zvcm09InRyYW5z"
            b"bGF0ZSgwLjAwMDAwMCwzMy4wMDAwMDApIHNjYWxlKDAuMTAwMDAwLC0wLjEwMDAwMCk"
            b"iCmZpbGw9IiMwMDAwMDAiIHN0cm9rZT0ibm9uZSI+CjwvZz4KPC9zdmc+Cg=="
        )
        attachment.write(
            {
                "datas": b64_data_svg,
            }
        )

        self.assertEqual(attachment.mimetype, "image/svg+xml")

    def test_write_name(self):
        self.temp_backend.use_as_default_for_attachments = True
        attachment = self.ir_attachment_model.create(
            {"name": "file.bin", "datas": b"aGVsbG8gd29ybGQK"}
        )
        self.assertTrue(attachment.fs_filename.startswith("file-"))
        self.assertTrue(attachment.fs_filename.endswith(".bin"))
        attachment.write({"name": "file2.txt"})
        self.assertTrue(attachment.fs_filename.startswith("file2-"))
        self.assertTrue(attachment.fs_filename.endswith(".txt"))

    def test_store_in_db_instead_of_object_storage_domain(self):
        IrAttachment = self.env["ir.attachment"]
        self.patch(
            type(IrAttachment),
            "_get_storage_force_db_config",
            lambda self: {"text/plain": 0, "image/png": 100},
        )
        self.assertEqual(
            self.env["ir.attachment"]._store_in_db_instead_of_object_storage_domain(),
            [
                "|",
                ("mimetype", "=like", "text/plain%"),
                "&",
                ("mimetype", "=like", "image/png%"),
                ("file_size", "<=", 100),
            ],
        )
