# Copyright 2023 ACSONE SA/NV (http://acsone.eu).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import os
import shutil
import tempfile

from odoo.tests.common import TransactionCase


class TestFSAttachmentCommon(TransactionCase):
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
            }
        )
        cls.backend_optimized = cls.env["fs.storage"].create(
            {
                "name": "Temp Optimized FS Storage",
                "protocol": "file",
                "code": "tmp_opt",
                "directory_path": temp_dir,
                "optimizes_directory_path": True,
            }
        )
        cls.temp_dir = temp_dir
        cls.gc_file_model = cls.env["fs.file.gc"]
        cls.ir_attachment_model = cls.env["ir.attachment"]

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
            }
        )
        self.backend_optimized.write(
            {
                "protocol": "file",
                "code": "tmp_opt",
                "directory_path": self.temp_dir,
                "optimizes_directory_path": True,
            }
        )

    def tearDown(self) -> None:
        super().tearDown()
        # empty the temp dir
        for f in os.listdir(self.temp_dir):
            full_path = os.path.join(self.temp_dir, f)
            if os.path.isfile(full_path):
                os.remove(full_path)
            else:  # using optimizes_directory_path, we'll have a directory
                shutil.rmtree(full_path)


class MyException(Exception):
    """Exception to be raised into tests ensure that we trap only this
    exception and not other exceptions raised by the test"""
