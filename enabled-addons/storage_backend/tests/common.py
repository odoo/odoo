# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
from unittest import mock

from odoo.addons.component.tests.common import TransactionComponentCase


class BackendStorageTestMixin:
    def _test_setting_and_getting_data(self):
        # Check that the directory is empty
        files = self.backend.list_files()
        self.assertNotIn(self.filename, files)

        # Add a new file
        self.backend.add(
            self.filename, self.filedata, mimetype="text/plain", binary=False
        )

        # Check that the file exist
        files = self.backend.list_files()
        self.assertIn(self.filename, files)

        # Retrieve the file added
        data = self.backend.get(self.filename, binary=False)
        self.assertEqual(data, self.filedata)

        # Delete the file
        self.backend.delete(self.filename)
        files = self.backend.list_files()
        self.assertNotIn(self.filename, files)

    def _test_setting_and_getting_data_from_root(self):
        self._test_setting_and_getting_data()

    def _test_setting_and_getting_data_from_dir(self):
        self.backend.directory_path = self.case_with_subdirectory
        self._test_setting_and_getting_data()

    def _test_find_files(
        self,
        backend,
        adapter_dotted_path,
        mocked_filepaths,
        pattern,
        expected_filepaths,
    ):
        with mock.patch(adapter_dotted_path + ".list") as mocked:
            mocked.return_value = mocked_filepaths
            res = backend.find_files(pattern)
            self.assertEqual(sorted(res), sorted(expected_filepaths))

    def _test_move_files(
        self,
        backend,
        adapter_dotted_path,
        filename,
        destination_path,
        expected_filepaths,
    ):
        with mock.patch(adapter_dotted_path + ".move_files") as mocked:
            mocked.return_value = expected_filepaths
            res = backend.move_files(filename, destination_path)
            self.assertEqual(sorted(res), sorted(expected_filepaths))


class CommonCase(TransactionComponentCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.backend = cls.env.ref("storage_backend.default_storage_backend")
        cls.filedata = base64.b64encode(b"This is a simple file")
        cls.filename = "test_file.txt"
        cls.case_with_subdirectory = "subdirectory/here"
        cls.demo_user = cls.env.ref("base.user_demo")
