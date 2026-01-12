# Copyright 2023 ACSONE SA/NV (http://acsone.eu).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from ..models.ir_attachment import AttachmentFileLikeAdapter
from .common import MyException, TestFSAttachmentCommon


class TestFSAttachmentFileLikeAdapterMixin:
    @classmethod
    def _create_attachment(cls):
        raise NotImplementedError

    @classmethod
    def prepareClass(cls):
        cls.initial_content = b"This is a test attachment"
        cls.new_content = b"This is a new test attachment"

    def prepare(self):
        self.attachment = self._create_attachment()

    def open(self, attachment=None, mode="rb", new_version=False, **kwargs):
        return AttachmentFileLikeAdapter(
            attachment or self.attachment,
            mode=mode,
            new_version=new_version,
            **kwargs,
        )

    def test_read(self):
        with self.open(mode="rb") as f:
            self.assertEqual(f.read(), self.initial_content)

    def test_write(self):
        with self.open(mode="wb") as f:
            f.write(self.new_content)
        self.assertEqual(self.new_content, self.attachment.raw)

    def test_write_append(self):
        self.assertEqual(self.initial_content, self.attachment.raw)
        with self.open(mode="ab") as f:
            f.write(self.new_content)
        self.assertEqual(self.initial_content + self.new_content, self.attachment.raw)

    def test_write_new_version(self):
        initial_fname = self.attachment.store_fname
        with self.open(mode="wb", new_version=True) as f:
            f.write(self.new_content)
        self.assertEqual(self.new_content, self.attachment.raw)
        if initial_fname:
            self.assertNotEqual(self.attachment.store_fname, initial_fname)

    def test_write_append_new_version(self):
        initial_fname = self.attachment.store_fname
        with self.open(mode="ab", new_version=True) as f:
            f.write(self.new_content)
        self.assertEqual(self.initial_content + self.new_content, self.attachment.raw)
        if initial_fname:
            self.assertNotEqual(self.attachment.store_fname, initial_fname)

    def test_write_transactional_new_version_only(self):
        try:
            initial_fname = self.attachment.store_fname
            with self.env.cr.savepoint():
                with self.open(mode="wb", new_version=True) as f:
                    f.write(self.new_content)
                self.assertEqual(self.new_content, self.attachment.raw)
                if initial_fname:
                    self.assertNotEqual(self.attachment.store_fname, initial_fname)
                raise MyException("Test")
        except MyException:
            ...

        self.assertEqual(self.initial_content, self.attachment.raw)
        if initial_fname:
            self.assertEqual(self.attachment.store_fname, initial_fname)


class TestAttachmentInFileSystemFileLikeAdapter(
    TestFSAttachmentCommon, TestFSAttachmentFileLikeAdapterMixin
):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.prepareClass()

    def setUp(self):
        super().setUp()
        self.prepare()

    @classmethod
    def _create_attachment(cls):
        return (
            cls.env["ir.attachment"]
            .with_context(
                storage_location=cls.temp_backend.code,
                storage_file_path="test.txt",
            )
            .create({"name": "test.txt", "raw": cls.initial_content})
        )


class TestAttachmentInDBFileLikeAdapter(
    TestFSAttachmentCommon, TestFSAttachmentFileLikeAdapterMixin
):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.prepareClass()

    def setUp(self):
        super().setUp()
        self.env["ir.config_parameter"].sudo().set_param("ir_attachment.location", "db")
        self.prepare()

    def tearDown(self) -> None:
        self.attachment.unlink()
        super().tearDown()

    @classmethod
    def _create_attachment(cls):
        return cls.env["ir.attachment"].create(
            {"name": "test.txt", "raw": cls.initial_content}
        )


class TestAttachmentInFileFileLikeAdapter(
    TestFSAttachmentCommon, TestFSAttachmentFileLikeAdapterMixin
):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.prepareClass()

    def setUp(self):
        super().setUp()
        self.env["ir.config_parameter"].sudo().set_param(
            "ir_attachment.location", "file"
        )
        self.prepare()

    def tearDown(self) -> None:
        self.attachment.unlink()
        self.attachment._gc_file_store_unsafe()
        super().tearDown()

    @classmethod
    def _create_attachment(cls):
        return cls.env["ir.attachment"].create(
            {"name": "test.txt", "raw": cls.initial_content}
        )


class TestAttachmentInFileSystemDependingModelFileLikeAdapter(
    TestFSAttachmentCommon, TestFSAttachmentFileLikeAdapterMixin
):
    """
    Configure the temp backend to store only attachments linked to
    res.partner model.

    Check that opening/updating the file does not change the storage type.
    """

    @classmethod
    def setUpClass(cls):
        res = super().setUpClass()
        cls.temp_backend.model_xmlids = "base.model_res_partner"
        cls.prepareClass()
        return res

    def setUp(self):
        super().setUp()
        super().prepare()

    @classmethod
    def _create_attachment(cls):
        return (
            cls.env["ir.attachment"]
            .with_context(
                storage_file_path="test.txt",
            )
            .create(
                {
                    "name": "test.txt",
                    "raw": cls.initial_content,
                    "res_model": "res.partner",
                }
            )
        )

    def test_storage_location(self):
        self.assertEqual(self.attachment.fs_storage_id, self.temp_backend)


class TestAttachmentInFileSystemDependingFieldFileLikeAdapter(
    TestFSAttachmentCommon, TestFSAttachmentFileLikeAdapterMixin
):
    """
    Configure the temp backend to store only attachments linked to
    res.country ID field.

    Check that opening/updating the file does not change the storage type.
    """

    @classmethod
    def setUpClass(cls):
        res = super().setUpClass()
        cls.temp_backend.field_xmlids = "base.field_res_country__id"
        cls.prepareClass()
        return res

    def setUp(self):
        super().setUp()
        super().prepare()

    @classmethod
    def _create_attachment(cls):
        return (
            cls.env["ir.attachment"]
            .with_context(
                storage_file_path="test.txt",
            )
            .create(
                {
                    "name": "test.txt",
                    "raw": cls.initial_content,
                    "res_model": "res.country",
                    "res_field": "id",
                }
            )
        )

    def test_storage_location(self):
        self.assertEqual(self.attachment.fs_storage_id, self.temp_backend)
