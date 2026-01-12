# Copyright 2023 ACSONE SA/NV (http://acsone.eu).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import base64
import os

from .common import TestFSAttachmentCommon


class TestFsStorage(TestFSAttachmentCommon):
    @classmethod
    def setUpClass(cls):
        res = super().setUpClass()
        cls.default_backend = cls.env.ref("fs_storage.fs_storage_demo")
        return res

    def test_force_model_create_attachment(self):
        """
        Force 'res.partner' model to temp_backend
        Use odoofs as default for attachments
        * Check that only attachments linked to res.partner model are stored
        in the first FS.
        * Check that updating this first attachment does not change the storage
        """
        self.default_backend.use_as_default_for_attachments = True
        self.temp_backend.model_xmlids = "base.model_res_partner"

        # 1a. First attachment linked to res.partner model
        content = b"This is a test attachment linked to res.partner model"
        attachment = self.ir_attachment_model.create(
            {"name": "test.txt", "raw": content, "res_model": "res.partner"}
        )
        self.assertTrue(attachment.store_fname)
        self.assertFalse(attachment.db_datas)
        self.assertEqual(attachment.raw, content)
        self.assertEqual(attachment.mimetype, "text/plain")
        self.env.flush_all()

        initial_filename = f"test-{attachment.id}-0.txt"

        self.assertEqual(attachment.fs_storage_code, self.temp_backend.code)
        self.assertEqual(os.listdir(self.temp_dir), [initial_filename])
        with attachment.open("rb") as f:
            self.assertEqual(f.read(), content)
        with open(os.path.join(self.temp_dir, initial_filename), "rb") as f:
            self.assertEqual(f.read(), content)

        # 1b. Update the attachment
        new_content = b"Update the test attachment"
        attachment.raw = new_content
        with attachment.open("rb") as f:
            self.assertEqual(f.read(), new_content)
        # a new file version is created
        new_filename = f"test-{attachment.id}-1.txt"
        with open(os.path.join(self.temp_dir, new_filename), "rb") as f:
            self.assertEqual(f.read(), new_content)
        self.assertEqual(attachment.raw, new_content)
        self.assertEqual(attachment.store_fname, f"tmp_dir://{new_filename}")

        # 2. Second attachment linked to res.country model
        content = b"This is a test attachment linked to res.country model"
        attachment = self.ir_attachment_model.create(
            {"name": "test.txt", "raw": content, "res_model": "res.country"}
        )
        self.assertTrue(attachment.store_fname)
        self.assertFalse(attachment.db_datas)
        self.assertEqual(attachment.raw, content)
        self.assertEqual(attachment.mimetype, "text/plain")
        self.env.flush_all()

        self.assertEqual(attachment.fs_storage_code, self.default_backend.code)

    def test_force_field_create_attachment(self):
        """
        Force 'base.field_res.partner__name' field to temp_backend
        Use odoofs as default for attachments
        * Check that only attachments linked to res.partner name field are stored
        in the first FS.
        * Check that updating this first attachment does not change the storage
        """
        self.default_backend.use_as_default_for_attachments = True
        self.temp_backend.field_xmlids = "base.field_res_partner__name"

        # 1a. First attachment linked to res.partner name field
        content = b"This is a test attachment linked to res.partner name field"
        attachment = self.ir_attachment_model.create(
            {
                "name": "test.txt",
                "raw": content,
                "res_model": "res.partner",
                "res_field": "name",
            }
        )
        self.assertTrue(attachment.store_fname)
        self.assertFalse(attachment.db_datas)
        self.assertEqual(attachment.raw, content)
        self.assertEqual(attachment.mimetype, "text/plain")
        self.env.flush_all()

        initial_filename = f"test-{attachment.id}-0.txt"

        self.assertEqual(attachment.fs_storage_code, self.temp_backend.code)
        self.assertEqual(os.listdir(self.temp_dir), [initial_filename])
        with attachment.open("rb") as f:
            self.assertEqual(f.read(), content)
        with open(os.path.join(self.temp_dir, initial_filename), "rb") as f:
            self.assertEqual(f.read(), content)

        # 1b. Update the attachment
        new_content = b"Update the test attachment"
        attachment.raw = new_content
        with attachment.open("rb") as f:
            self.assertEqual(f.read(), new_content)
        # a new file version is created
        new_filename = f"test-{attachment.id}-1.txt"
        with open(os.path.join(self.temp_dir, new_filename), "rb") as f:
            self.assertEqual(f.read(), new_content)
        self.assertEqual(attachment.raw, new_content)
        self.assertEqual(attachment.store_fname, f"tmp_dir://{new_filename}")

        # 2. Second attachment linked to res.partner but other field (website)
        content = b"This is a test attachment linked to res.partner website field"
        attachment = self.ir_attachment_model.create(
            {
                "name": "test.txt",
                "raw": content,
                "res_model": "res.partner",
                "res_field": "website",
            }
        )
        self.assertTrue(attachment.store_fname)
        self.assertFalse(attachment.db_datas)
        self.assertEqual(attachment.raw, content)
        self.assertEqual(attachment.mimetype, "text/plain")
        self.env.flush_all()

        self.assertEqual(attachment.fs_storage_code, self.default_backend.code)

        # 3. Third attachment linked to res.partner but no specific field
        content = b"This is a test attachment linked to res.partner model"
        attachment = self.ir_attachment_model.create(
            {"name": "test.txt", "raw": content, "res_model": "res.partner"}
        )
        self.assertTrue(attachment.store_fname)
        self.assertFalse(attachment.db_datas)
        self.assertEqual(attachment.raw, content)
        self.assertEqual(attachment.mimetype, "text/plain")
        self.env.flush_all()

        self.assertEqual(attachment.fs_storage_code, self.default_backend.code)

    def test_force_field_and_model_create_attachment(self):
        """
        Force res.partner model to default_backend.
        But force specific res.partner name field to temp_backend.
        * Check that attachments linked to res.partner name field are
        stored in temp_backend, and other attachments linked to other
        fields of res.partner are stored in default_backend
        * Check that updating this first attachment does not change the storage
        """
        self.default_backend.model_xmlids = "base.model_res_partner"
        self.temp_backend.field_xmlids = "base.field_res_partner__name"

        # 1a. First attachment linked to res.partner name field
        content = b"This is a test attachment linked to res.partner name field"
        attachment = self.ir_attachment_model.create(
            {
                "name": "test.txt",
                "raw": content,
                "res_model": "res.partner",
                "res_field": "name",
            }
        )
        self.assertTrue(attachment.store_fname)
        self.assertFalse(attachment.db_datas)
        self.assertEqual(attachment.raw, content)
        self.assertEqual(attachment.mimetype, "text/plain")
        self.env.flush_all()

        initial_filename = f"test-{attachment.id}-0.txt"

        self.assertEqual(attachment.fs_storage_code, self.temp_backend.code)
        self.assertEqual(os.listdir(self.temp_dir), [initial_filename])
        with attachment.open("rb") as f:
            self.assertEqual(f.read(), content)
        with open(os.path.join(self.temp_dir, initial_filename), "rb") as f:
            self.assertEqual(f.read(), content)

        # 1b. Update the attachment
        new_content = b"Update the test attachment"
        attachment.raw = new_content
        with attachment.open("rb") as f:
            self.assertEqual(f.read(), new_content)
        # a new file version is created
        new_filename = f"test-{attachment.id}-1.txt"
        with open(os.path.join(self.temp_dir, new_filename), "rb") as f:
            self.assertEqual(f.read(), new_content)
        self.assertEqual(attachment.raw, new_content)
        self.assertEqual(attachment.store_fname, f"tmp_dir://{new_filename}")

        # 2. Second attachment linked to res.partner but other field (website)
        content = b"This is a test attachment linked to res.partner website field"
        attachment = self.ir_attachment_model.create(
            {
                "name": "test.txt",
                "raw": content,
                "res_model": "res.partner",
                "res_field": "website",
            }
        )
        self.assertTrue(attachment.store_fname)
        self.assertFalse(attachment.db_datas)
        self.assertEqual(attachment.raw, content)
        self.assertEqual(attachment.mimetype, "text/plain")
        self.env.flush_all()

        self.assertEqual(attachment.fs_storage_code, self.default_backend.code)

        # 3. Third attachment linked to res.partner but no specific field
        content = b"This is a test attachment linked to res.partner model"
        attachment = self.ir_attachment_model.create(
            {"name": "test.txt", "raw": content, "res_model": "res.partner"}
        )
        self.assertTrue(attachment.store_fname)
        self.assertFalse(attachment.db_datas)
        self.assertEqual(attachment.raw, content)
        self.assertEqual(attachment.mimetype, "text/plain")
        self.env.flush_all()

        self.assertEqual(attachment.fs_storage_code, self.default_backend.code)

        # Fourth attachment linked to res.country: no storage because
        # no default FS storage
        content = b"This is a test attachment linked to res.country model"
        attachment = self.ir_attachment_model.create(
            {"name": "test.txt", "raw": content, "res_model": "res.country"}
        )
        self.assertTrue(attachment.store_fname)
        self.assertFalse(attachment.db_datas)
        self.assertEqual(attachment.raw, content)
        self.assertEqual(attachment.mimetype, "text/plain")
        self.env.flush_all()

        self.assertFalse(attachment.fs_storage_code)

    def test_recompute_urls(self):
        """
        Mark temp_backend as default and set its base_url. Create one attachment
        in temp_backend that is linked to a field and one that is not. * Check
        that after updating the base_url for the backend, executing
        recompute_urls updates fs_url for both attachments, whether they are
        linked to a field or not
        """
        self.temp_backend.base_url = "https://acsone.eu/media"
        self.temp_backend.use_as_default_for_attachments = True
        self.ir_attachment_model.create(
            {
                "name": "field.txt",
                "raw": "Attachment linked to a field",
                "res_model": "res.partner",
                "res_field": "name",
            }
        )
        self.ir_attachment_model.create(
            {
                "name": "no_field.txt",
                "raw": "Attachment not linked to a field",
            }
        )
        self.env.flush_all()

        self.env.cr.execute(
            f"""
            SELECT COUNT(*)
            FROM ir_attachment
            WHERE fs_storage_id = {self.temp_backend.id}
                AND fs_url LIKE '{self.temp_backend.base_url}%'
        """
        )
        self.assertEqual(self.env.cr.dictfetchall()[0].get("count"), 2)

        self.temp_backend.base_url = "https://forgeflow.com/media"
        self.temp_backend.recompute_urls()
        self.env.flush_all()

        self.env.cr.execute(
            f"""
            SELECT COUNT(*)
            FROM ir_attachment
            WHERE fs_storage_id = {self.temp_backend.id}
                AND fs_url LIKE '{self.temp_backend.base_url}%'
        """
        )
        self.assertEqual(self.env.cr.dictfetchall()[0].get("count"), 2)

    def test_url_for_image_dir_optimized_and_not_obfuscated(self):
        # Create a base64 encoded mock image (1x1 pixel transparent PNG)
        image_data = base64.b64encode(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08"
            b"\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDAT\x08\xd7c\xf8\x0f\x00"
            b"\x01\x01\x01\x00\xd1\x8d\xcd\xbf\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        # Create a mock image filestore
        fs_storage = self.env["fs.storage"].create(
            {
                "name": "FS Product Image Backend",
                "code": "file",
                "base_url": "https://localhost/images",
                "optimizes_directory_path": True,
                "use_filename_obfuscation": False,
            }
        )

        # Create a mock image attachment
        attachment = self.env["ir.attachment"].create(
            {"name": "test_image.png", "datas": image_data, "mimetype": "image/png"}
        )

        # Get the url from the model
        fs_url_1 = fs_storage._get_url_for_attachment(attachment)

        # Generate the url that should be accessed
        base_url = fs_storage.base_url_for_files
        fs_filename = attachment.fs_filename
        checksum = attachment.checksum
        parts = [base_url, checksum[:2], checksum[2:4], fs_filename]
        fs_url_2 = fs_storage._normalize_url("/".join(parts))

        # Make some checks and asset if the two urls are equal
        self.assertTrue(parts)
        self.assertTrue(checksum)
        self.assertEqual(fs_url_1, fs_url_2)

    def test_directory_path_substitution(self):
        self.temp_backend.directory_path += "/{db_name}"
        self.assertEqual("", self.temp_backend.base_url_for_files)
        self.assertNotIn("{db_name}", self.temp_backend.base_url_for_files)
