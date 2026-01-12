# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import base64
import io
import os
import tempfile
from io import BytesIO

from odoo_test_helper import FakeModelLoader
from PIL import Image

from odoo.tests.common import TransactionCase

from odoo.addons.fs_storage.models.fs_storage import FSStorage

from ..fields import FSFileValue


class TestFsFile(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.loader.backup_registry()
        from .models import TestModel

        cls.loader.update_registry((TestModel,))

        cls.create_content = b"content"
        cls.write_content = b"new content"
        cls.tmpfile_path = tempfile.mkstemp(suffix=".txt")[1]
        with open(cls.tmpfile_path, "wb") as f:
            f.write(cls.create_content)
        cls.filename = os.path.basename(cls.tmpfile_path)
        f = BytesIO()
        Image.new("RGB", (1, 1), color="red").save(f, "PNG")
        f.seek(0)
        cls.png_content = f

    def setUp(self):
        super().setUp()
        self.temp_dir: FSStorage = self.env["fs.storage"].create(
            {
                "name": "Temp FS Storage",
                "protocol": "memory",
                "code": "mem_dir",
                "directory_path": "/tmp/",
                "model_xmlids": "fs_file.model_test_model",
            }
        )

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.tmpfile_path):
            os.remove(cls.tmpfile_path)
        cls.loader.restore_registry()
        return super().tearDownClass()

    def _test_create(self, fs_file_value):
        model = self.env["test.model"]
        instance = model.create({"fs_file": fs_file_value})
        self.assertTrue(isinstance(instance.fs_file, FSFileValue))
        self.assertEqual(instance.fs_file.getvalue(), self.create_content)
        self.assertEqual(instance.fs_file.name, self.filename)
        self.assertEqual(instance.fs_file.url_path, None)
        self.assertEqual(instance.fs_file.url, None)

    def _test_write(self, fs_file_value, **ctx):
        instance = self.env["test.model"].create({})
        if ctx:
            instance = instance.with_context(**ctx)
        instance.fs_file = fs_file_value
        self.assertEqual(instance.fs_file.getvalue(), self.write_content)
        self.assertEqual(instance.fs_file.name, self.filename)

    def test_read(self):
        instance = self.env["test.model"].create(
            {"fs_file": FSFileValue(name=self.filename, value=self.create_content)}
        )
        info = instance.read(["fs_file"])[0]
        self.assertDictEqual(
            info["fs_file"],
            {
                "filename": self.filename,
                "mimetype": "text/plain",
                "size": 7,
                "url": instance.fs_file.internal_url,
            },
        )

    def test_create_with_fsfilebytesio(self):
        self._test_create(FSFileValue(name=self.filename, value=self.create_content))

    def test_create_with_dict(self):
        self._test_create(
            {
                "filename": self.filename,
                "content": base64.b64encode(self.create_content),
            }
        )

    def test_write_with_dict(self):
        self._test_write(
            {
                "filename": self.filename,
                "content": base64.b64encode(self.write_content),
            }
        )

    def test_create_with_file_like(self):
        with open(self.tmpfile_path, "rb") as f:
            self._test_create(f)

    def test_create_in_b64(self):
        instance = self.env["test.model"].create(
            {"fs_file": base64.b64encode(self.create_content)}
        )
        self.assertTrue(isinstance(instance.fs_file, FSFileValue))
        self.assertEqual(instance.fs_file.getvalue(), self.create_content)

    def test_create_in_b64_check_size(self):
        instance = self.env["test.model"].create(
            {"fs_file": base64.b64encode(self.create_content)}
        )
        self.assertEqual(7, instance.fs_file.size)

    def test_create_in_b64_check_extension(self):
        instance = self.env["test.model"].create(
            {"fs_file": base64.b64encode(self.create_content)}
        )
        self.assertEqual("txt", instance.fs_file.extension)

    def test_create_in_b64_name_set(self):
        instance = self.env["test.model"].create(
            {"fs_file": base64.b64encode(self.create_content)}
        )
        with self.assertRaises(ValueError) as raise_exception:
            instance.fs_file.name = "fs_file_test"
        self.assertEqual(
            "The name of the file can only be updated while the file is not yet stored",
            raise_exception.exception.args[0],
        )

    def test_write_in_b64(self):
        instance = self.env["test.model"].create({"fs_file": b"test"})
        self.assertEqual("fs_file", instance.fs_file.write_buffer.name)
        instance.write({"fs_file": base64.b64encode(self.create_content)})
        self.assertTrue(isinstance(instance.fs_file, FSFileValue))
        self.assertEqual(instance.fs_file.getvalue(), self.create_content)

    def test_write_in_b64_with_specified_filename(self):
        self._test_write(
            base64.b64encode(self.write_content), fs_filename=self.filename
        )

    def test_create_with_io(self):
        instance = self.env["test.model"].create(
            {"fs_file": io.BytesIO(self.create_content)}
        )
        self.assertTrue(isinstance(instance.fs_file, FSFileValue))
        self.assertEqual(instance.fs_file.getvalue(), self.create_content)

    def test_write_with_io(self):
        instance = self.env["test.model"].create(
            {"fs_file": io.BytesIO(self.create_content)}
        )
        instance.write({"fs_file": io.BytesIO(b"test3")})
        self.assertTrue(isinstance(instance.fs_file, FSFileValue))
        self.assertEqual(instance.fs_file.getvalue(), b"test3")

    def test_create_with_empty_value(self):
        instance = self.env["test.model"].create(
            {"fs_file": FSFileValue(name=self.filename, value=b"")}
        )
        self.assertEqual(instance.fs_file.getvalue(), b"")
        self.assertEqual(instance.fs_file.name, self.filename)

    def test_write_with_empty_value(self):
        instance = self.env["test.model"].create(
            {"fs_file": FSFileValue(name=self.filename, value=self.create_content)}
        )
        instance.write({"fs_file": FSFileValue(name=self.filename, value=b"")})
        self.assertEqual(instance.fs_file.getvalue(), b"")
        self.assertEqual(instance.fs_file.name, self.filename)

    def test_modify_fsfilebytesio(self):
        """If you modify the content of the FSFileValue,
        the changes will be directly applied
        and a new file in the storage must be created for the new content.
        """
        instance = self.env["test.model"].create(
            {"fs_file": FSFileValue(name=self.filename, value=self.create_content)}
        )
        initial_store_fname = instance.fs_file.attachment.store_fname
        with instance.fs_file.open(mode="wb") as f:
            f.write(b"new_content")
        self.assertNotEqual(
            instance.fs_file.attachment.store_fname, initial_store_fname
        )
        self.assertEqual(instance.fs_file.getvalue(), b"new_content")

    def test_fs_value_mimetype(self):
        """Test that the mimetype is correctly computed on a FSFileValue"""
        value = FSFileValue(name="test.png", value=self.create_content)
        # in this case, the mimetype is not computed from the filename
        self.assertEqual(value.mimetype, "image/png")

        value = FSFileValue(value=open(self.tmpfile_path, "rb"))
        # in this case, the mimetype is not computed from the content
        self.assertEqual(value.mimetype, "text/plain")

        # if the mimetype is not found into the name, it should be computed
        # from the content
        value = FSFileValue(name="test", value=self.png_content)
        self.assertEqual(value.mimetype, "image/png")

    def test_fs_value_no_name(self):
        with self.assertRaises(ValueError) as raise_exception:
            FSFileValue(value=self.create_content)
        self.assertEqual(
            "name must be set when value is bytes", raise_exception.exception.args[0]
        )

    def test_cache_invalidation(self):
        """Test that the cache is invalidated when the FSFileValue is modified
        When we assign a FSFileValue to a field, the value in the cache  must
        be invalidated and the new value must be computed. This is required
        because the FSFileValue from the cache should always be linked to the
        attachment record used to store the file in the storage.
        """
        value = FSFileValue(name="test.png", value=self.create_content)
        instance = self.env["test.model"].create({"fs_file": value})
        self.assertNotEqual(instance.fs_file, value)
        value = FSFileValue(name="test.png", value=self.write_content)
        instance.write({"fs_file": value})
        self.assertNotEqual(instance.fs_file, value)
