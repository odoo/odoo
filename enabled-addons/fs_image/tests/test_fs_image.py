# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import base64
import io
import os
import tempfile

from odoo_test_helper import FakeModelLoader
from PIL import Image

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, users, warmup

from odoo.addons.fs_storage.models.fs_storage import FSStorage

from ..fields import FSImageValue


class TestFsImage(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.env["ir.config_parameter"].set_param(
            "base.image_autoresize_max_px", "10000x10000"
        )
        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.loader.backup_registry()
        from .models import TestImageModel, TestRelatedImageModel

        cls.loader.update_registry((TestImageModel, TestRelatedImageModel))

        cls.image_w = cls._create_image(4000, 2000)
        cls.image_h = cls._create_image(2000, 4000)

        cls.create_content = cls.image_w
        cls.write_content = cls.image_h
        cls.tmpfile_path = tempfile.mkstemp(suffix=".png")[1]
        with open(cls.tmpfile_path, "wb") as f:
            f.write(cls.create_content)
        cls.filename = os.path.basename(cls.tmpfile_path)

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

    @classmethod
    def _create_image(cls, width, height, color="#4169E1", img_format="PNG"):
        f = io.BytesIO()
        Image.new("RGB", (width, height), color).save(f, img_format)
        f.seek(0)
        return f.read()

    def _test_create(self, fs_image_value):
        model = self.env["test.image.model"]
        instance = model.create({"fs_image": fs_image_value})
        self.assertTrue(isinstance(instance.fs_image, FSImageValue))
        self.assertEqual(instance.fs_image.getvalue(), self.create_content)
        self.assertEqual(instance.fs_image.name, self.filename)
        return instance

    def _test_write(self, fs_image_value, **ctx):
        instance = self.env["test.image.model"].create({})
        if ctx:
            instance = instance.with_context(**ctx)
        instance.fs_image = fs_image_value
        self.assertEqual(instance.fs_image.getvalue(), self.write_content)
        self.assertEqual(instance.fs_image.name, self.filename)
        return instance

    def assert_image_size(self, value: bytes, width, height):
        self.assertEqual(Image.open(io.BytesIO(value)).size, (width, height))

    def test_read(self):
        instance = self.env["test.image.model"].create(
            {"fs_image": FSImageValue(name=self.filename, value=self.create_content)}
        )
        info = instance.read(["fs_image"])[0]
        self.assertDictEqual(
            info["fs_image"],
            {
                "alt_text": None,
                "filename": self.filename,
                "mimetype": "image/png",
                "size": len(self.create_content),
                "url": instance.fs_image.internal_url,
            },
        )

    def test_create_with_FsImagebytesio(self):
        self._test_create(FSImageValue(name=self.filename, value=self.create_content))

    def test_create_with_dict(self):
        instance = self._test_create(
            {
                "filename": self.filename,
                "content": base64.b64encode(self.create_content),
                "alt_text": "test",
            }
        )
        self.assertEqual(instance.fs_image.alt_text, "test")

    def test_write_with_dict(self):
        instance = self._test_write(
            {
                "filename": self.filename,
                "content": base64.b64encode(self.write_content),
                "alt_text": "test_bis",
            }
        )
        self.assertEqual(instance.fs_image.alt_text, "test_bis")

    def test_create_with_file_like(self):
        with open(self.tmpfile_path, "rb") as f:
            self._test_create(f)

    def test_create_in_b64(self):
        instance = self.env["test.image.model"].create(
            {"fs_image": base64.b64encode(self.create_content)}
        )
        self.assertTrue(isinstance(instance.fs_image, FSImageValue))
        self.assertEqual(instance.fs_image.getvalue(), self.create_content)

    def test_write_in_b64(self):
        instance = self.env["test.image.model"].create({"fs_image": b"test"})
        instance.write({"fs_image": base64.b64encode(self.create_content)})
        self.assertTrue(isinstance(instance.fs_image, FSImageValue))
        self.assertEqual(instance.fs_image.getvalue(), self.create_content)

    def test_write_in_b64_with_specified_filename(self):
        self._test_write(
            base64.b64encode(self.write_content), fs_filename=self.filename
        )

    def test_create_with_io(self):
        instance = self.env["test.image.model"].create(
            {"fs_image": io.BytesIO(self.create_content)}
        )
        self.assertTrue(isinstance(instance.fs_image, FSImageValue))
        self.assertEqual(instance.fs_image.getvalue(), self.create_content)

    def test_write_with_io(self):
        instance = self.env["test.image.model"].create(
            {"fs_image": io.BytesIO(self.create_content)}
        )
        instance.write({"fs_image": io.BytesIO(b"test3")})
        self.assertTrue(isinstance(instance.fs_image, FSImageValue))
        self.assertEqual(instance.fs_image.getvalue(), b"test3")

    def test_modify_FsImagebytesio(self):
        """If you modify the content of the FSImageValue,
        the changes will be directly applied
        and a new file in the storage must be created for the new content.
        """
        instance = self.env["test.image.model"].create(
            {"fs_image": FSImageValue(name=self.filename, value=self.create_content)}
        )
        initial_store_fname = instance.fs_image.attachment.store_fname
        with instance.fs_image.open(mode="wb") as f:
            f.write(b"new_content")
        self.assertNotEqual(
            instance.fs_image.attachment.store_fname, initial_store_fname
        )
        self.assertEqual(instance.fs_image.getvalue(), b"new_content")

    def test_image_resize(self):
        instance = self.env["test.image.model"].create(
            {"fs_image_1024": FSImageValue(name=self.filename, value=self.image_w)}
        )
        # the image is resized to 1024x512 even if the field is 1024x1024 since
        # we keep the ratio
        self.assert_image_size(instance.fs_image_1024.getvalue(), 1024, 512)

    def test_image_resize_related(self):
        instance = self.env["test.related.image.model"].create(
            {"fs_image": FSImageValue(name=self.filename, value=self.image_w)}
        )
        self.assert_image_size(instance.fs_image.getvalue(), 4000, 2000)
        self.assert_image_size(instance.fs_image_1024.getvalue(), 1024, 512)
        self.assert_image_size(instance.fs_image_512.getvalue(), 512, 256)

    def test_related_with_b64(self):
        instance = self.env["test.related.image.model"].create(
            {"fs_image": base64.b64encode(self.create_content)}
        )
        self.assert_image_size(instance.fs_image.getvalue(), 4000, 2000)
        self.assert_image_size(instance.fs_image_1024.getvalue(), 1024, 512)
        self.assert_image_size(instance.fs_image_512.getvalue(), 512, 256)

    def test_write_alt_text(self):
        instance = self.env["test.image.model"].create(
            {"fs_image": FSImageValue(name=self.filename, value=self.image_w)}
        )
        instance.fs_image.alt_text = "test"
        self.assertEqual(instance.fs_image.alt_text, "test")

    def test_write_alt_text_with_dict(self):
        instance = self.env["test.image.model"].create(
            {"fs_image": FSImageValue(name=self.filename, value=self.image_w)}
        )
        instance.write({"fs_image": {"alt_text": "test"}})
        self.assertEqual(instance.fs_image.alt_text, "test")

    def test_write_alt_text_on_empty_with_dict(self):
        instance = self.env["test.image.model"].create({})
        with self.assertRaisesRegex(UserError, "Cannot set alt_text on empty image"):
            instance.write({"fs_image": {"alt_text": "test"}})

    @users("__system__")
    @warmup
    def test_generated_sql_commands(self):
        # The following tests will never fail, but they will output a warning
        # if the number of SQL queries changes into the logs. They
        # are to help us keep track of the number of SQL queries generated
        # by the module.
        with self.assertQueryCount(__system__=3):
            instance = self.env["test.image.model"].create(
                {"fs_image": FSImageValue(name=self.filename, value=self.image_w)}
            )

        instance.invalidate_recordset()
        with self.assertQueryCount(__system__=1):
            self.assertEqual(instance.fs_image.getvalue(), self.image_w)
            self.env.flush_all()
