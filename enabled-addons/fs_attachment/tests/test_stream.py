# Copyright 2023 ACSONE SA/NV (http://acsone.eu).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import base64
import io
import os
import shutil
import tempfile

from PIL import Image

from odoo.tests.common import HttpCase


class TestStream(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        temp_dir = tempfile.mkdtemp()
        cls.temp_backend = cls.env["fs.storage"].create(
            {
                "name": "Temp FS Storage",
                "protocol": "file",
                "code": "tmp_dir",
                "directory_path": temp_dir,
                "base_url": "http://my.public.files/",
            }
        )
        cls.temp_dir = temp_dir
        cls.content = b"This is a test attachment"
        cls.attachment_binary = (
            cls.env["ir.attachment"]
            .with_context(
                storage_location=cls.temp_backend.code,
                storage_file_path="test.txt",
            )
            .create({"name": "test.txt", "raw": cls.content})
        )

        cls.image = cls._create_image(128, 128)
        cls.attachment_image = (
            cls.env["ir.attachment"]
            .with_context(
                storage_location=cls.temp_backend.code,
                storage_file_path="test.png",
            )
            .create({"name": "test.png", "raw": cls.image})
        )

        @cls.addClassCleanup
        def cleanup_tempdir():
            shutil.rmtree(temp_dir)

        assert cls.attachment_binary.fs_filename
        assert cls.attachment_image.fs_filename

    def setUp(self):
        super().setUp()
        # enforce temp_backend field since it seems that they are reset on
        # savepoint rollback when managed by server_environment -> TO Be investigated
        self.temp_backend.write(
            {
                "protocol": "file",
                "code": "tmp_dir",
                "directory_path": self.temp_dir,
                "base_url": "http://my.public.files/",
            }
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        for f in os.listdir(cls.temp_dir):
            os.remove(os.path.join(cls.temp_dir, f))

    @classmethod
    def _create_image(cls, width, height, color="#4169E1", img_format="PNG"):
        f = io.BytesIO()
        Image.new("RGB", (width, height), color).save(f, img_format)
        f.seek(0)
        return f.read()

    def assertDownload(
        self, url, headers, assert_status_code, assert_headers, assert_content=None
    ):
        res = self.url_open(url, headers=headers)
        res.raise_for_status()
        self.assertEqual(res.status_code, assert_status_code)
        for header_name, header_value in assert_headers.items():
            self.assertEqual(
                res.headers.get(header_name),
                header_value,
                f"Wrong value for header {header_name}",
            )
        if assert_content:
            self.assertEqual(res.content, assert_content, "Wong content")
        return res

    def test_content_url(self):
        self.authenticate("admin", "admin")
        url = f"/web/content/{self.attachment_binary.id}"
        self.assertDownload(
            url,
            headers={},
            assert_status_code=200,
            assert_headers={
                "Content-Type": "text/plain; charset=utf-8",
                "Content-Disposition": "inline; filename=test.txt",
            },
            assert_content=self.content,
        )
        url = (
            f"/web/content/{self.attachment_binary.id}/"
            "?filename=test2.txt&mimetype=text/csv"
        )
        self.assertDownload(
            url,
            headers={},
            assert_status_code=200,
            assert_headers={
                "Content-Type": "text/csv; charset=utf-8",
                "Content-Disposition": "inline; filename=test2.txt",
            },
            assert_content=self.content,
        )

    def test_image_url(self):
        self.authenticate("admin", "admin")
        url = f"/web/image/{self.attachment_image.id}"
        self.assertDownload(
            url,
            headers={},
            assert_status_code=200,
            assert_headers={
                "Content-Type": "image/png",
                "Content-Disposition": "inline; filename=test.png",
            },
            assert_content=self.image,
        )

    def test_image_url_with_size(self):
        self.authenticate("admin", "admin")
        url = f"/web/image/{self.attachment_image.id}?width=64&height=64"
        res = self.assertDownload(
            url,
            headers={},
            assert_status_code=200,
            assert_headers={
                "Content-Type": "image/png",
                "Content-Disposition": "inline; filename=test.png",
            },
        )
        self.assertEqual(Image.open(io.BytesIO(res.content)).size, (64, 64))

    def test_response_csp_header(self):
        self.authenticate("admin", "admin")
        url = f"/web/content/{self.attachment_binary.id}"
        self.assertDownload(
            url,
            headers={},
            assert_status_code=200,
            assert_headers={
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'",
            },
        )

    def test_serving_field_image(self):
        self.authenticate("admin", "admin")
        demo_partner = self.env.ref("base.partner_demo")
        demo_partner.with_context(
            storage_location=self.temp_backend.code,
        ).write({"image_128": base64.encodebytes(self._create_image(128, 128))})
        url = f"/web/image/{demo_partner._name}/{demo_partner.id}/image_128"
        res = self.assertDownload(
            url,
            headers={},
            assert_status_code=200,
            assert_headers={
                "Content-Type": "image/png",
            },
        )
        self.assertEqual(Image.open(io.BytesIO(res.content)).size, (128, 128))

        url = f"/web/image/{demo_partner._name}/{demo_partner.id}/avatar_128"
        avatar_res = self.assertDownload(
            url,
            headers={},
            assert_status_code=200,
            assert_headers={
                "Content-Type": "image/png",
            },
        )
        self.assertEqual(Image.open(io.BytesIO(avatar_res.content)).size, (128, 128))

    def test_image_url_name_with_newline(self):
        """Test downloading a file with a newline in the name.

        This test simulates the scenario that causes the Werkzeug error:
        `ValueError: Detected newline in header value`.

        It verifies that:
        1. An `ir.attachment` record is created with a newline character
           (`\n`) explicitly included in its `name` field ("tes\nt.png").
        2. Accessing this attachment via the `/web/image/{attachment_id}` URL
           succeeds with an HTTP 200 status code.
        3. Crucially, the `Content-Disposition` header returned in the response
           contains a *sanitized* filename ("tes_t.png"). The newline character
           has been replaced (typically with an underscore by `secure_filename`).

        This confirms that the filename sanitization implemented (likely in the
        streaming logic, e.g., `FsStream.get_response` using `secure_filename`)
        correctly processes the unsafe filename before passing it to Werkzeug,
        thus preventing the original `ValueError` and ensuring safe header values.
        """
        attachment_image = (
            self.env["ir.attachment"]
            .with_context(
                storage_location=self.temp_backend.code,
                storage_file_path="test.png",
            )
            .create(
                {"name": "tes\nt.png", "raw": self.image}
            )  # newline in the filename
        )
        # Ensure the name IS stored with the newline before sanitization
        # happens on download
        self.assertIn("\n", attachment_image.name)

        self.authenticate("admin", "admin")
        url = f"/web/image/{attachment_image.id}"
        self.assertDownload(
            url,
            headers={},
            assert_status_code=200,
            assert_headers={
                "Content-Type": "image/png",
                # Assert that the filename in the header IS sanitized
                "Content-Disposition": "inline; filename=tes_t.png",
            },
            assert_content=self.image,
        )
