# Copyright 2023 ACSONE SA/NV (http://acsone.eu).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import os
import shutil
import tempfile

from odoo.tests.common import HttpCase


class TestFsAttachmentInternalUrl(HttpCase):
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
        cls.gc_file_model = cls.env["fs.file.gc"]
        cls.content = b"This is a test attachment"
        cls.attachment = (
            cls.env["ir.attachment"]
            .with_context(
                storage_location=cls.temp_backend.code,
                storage_file_path="test.txt",
            )
            .create({"name": "test.txt", "raw": cls.content})
        )

        @cls.addClassCleanup
        def cleanup_tempdir():
            shutil.rmtree(temp_dir)

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

    def test_fs_attachment_internal_url(self):
        self.authenticate("admin", "admin")
        self.assertDownload(
            self.attachment.internal_url,
            headers={},
            assert_status_code=200,
            assert_headers={
                "Content-Type": "text/plain; charset=utf-8",
                "Content-Disposition": "inline; filename=test.txt",
            },
            assert_content=self.content,
        )

    def test_fs_attachment_internal_url_x_sendfile(self):
        self.authenticate("admin", "admin")
        self.temp_backend.write({"use_x_sendfile_to_serve_internal_url": True})
        x_accel_redirect = f"/tmp_dir/test-{self.attachment.id}-0.txt"
        self.assertDownload(
            self.attachment.internal_url,
            headers={},
            assert_status_code=200,
            assert_headers={
                "Content-Type": "text/plain; charset=utf-8",
                "Content-Disposition": "inline; filename=test.txt",
                "X-Accel-Redirect": x_accel_redirect,
                "Content-Length": "0",
                "X-Sendfile": x_accel_redirect,
            },
            assert_content=None,
        )
