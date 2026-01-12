# Copyright 2023 ACSONE SA/NV (http://acsone.eu).
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
import warnings
from unittest import mock

from odoo.exceptions import ValidationError
from odoo.tests import Form
from odoo.tools import mute_logger

from .common import TestFSStorageCase


class TestFSStorage(TestFSStorageCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.copy_backend = cls.env["fs.storage"].create(
            {
                "name": "Temp FS Storage",
                "protocol": "file",
                "code": "copy_tmp_dir",
                "directory_path": "/",
            }
        )

    @mute_logger("py.warnings")
    def _test_deprecated_setting_and_getting_data(self):
        # Check that the directory is empty
        warnings.filterwarnings("ignore")
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

    @mute_logger("py.warnings")
    def _test_deprecated_find_files(self):
        warnings.filterwarnings("ignore")
        self.backend.add(
            self.filename, self.filedata, mimetype="text/plain", binary=False
        )
        try:
            res = self.backend.find_files(r".*\.txt")
            self.assertListEqual([self.filename], res)
            res = self.backend.find_files(r".*\.text")
            self.assertListEqual([], res)
        finally:
            self.backend.delete(self.filename)

    def test_deprecated_setting_and_getting_data_from_root(self):
        self._test_deprecated_setting_and_getting_data()

    def test_deprecated_setting_and_getting_data_from_dir(self):
        self.backend.directory_path = self.case_with_subdirectory
        self._test_deprecated_setting_and_getting_data()

    def test_deprecated_find_files_from_root(self):
        self._test_deprecated_find_files()

    def test_deprecated_find_files_from_dir(self):
        self.backend.directory_path = self.case_with_subdirectory
        self._test_deprecated_find_files()

    def test_ensure_one_fs_by_record(self):
        # in this test we ensure that we've one fs by record
        backend_ids = []
        for i in range(4):
            backend_ids.append(
                self.backend.create(
                    {"name": f"name{i}", "directory_path": f"{i}", "code": f"code{i}"}
                ).id
            )
        records = self.backend.browse(backend_ids)
        fs = None
        for rec in records:
            self.assertNotEqual(fs, rec.fs)

    def test_relative_access(self):
        self.backend.directory_path = self.case_with_subdirectory
        self._create_file(self.backend, self.filename, self.filedata)
        other_subdirectory = "other_subdirectory"
        backend2 = self.backend.copy({"directory_path": other_subdirectory})
        self._create_file(backend2, self.filename, self.filedata)
        with self.assertRaises(PermissionError), self.env.cr.savepoint():
            # check that we can't access outside the subdirectory
            backend2.fs.ls("../")
        with self.assertRaises(PermissionError), self.env.cr.savepoint():
            # check that we can't access the file into another subdirectory
            backend2.fs.ls(f"../{self.case_with_subdirectory}")
        self.backend.fs.rm_file(self.filename)
        backend2.fs.rm_file(self.filename)

    def test_recursive_add_odoo_storage_path_to_options(self):
        options = {
            "directory_path": "/tmp/my_backend",
            "target_protocol": "odoofs",
        }
        self.backend._recursive_add_odoo_storage_path(options)
        self.assertEqual(
            self.backend._odoo_storage_path,
            options.get("target_options").get("odoo_storage_path"),
        )
        options = {
            "directory_path": "/tmp/my_backend",
            "target_protocol": "dir",
            "target_options": {
                "path": "/my_backend",
                "target_protocol": "odoofs",
            },
        }
        self.backend._recursive_add_odoo_storage_path(options)
        self.assertEqual(
            self.backend._odoo_storage_path,
            options.get("target_options")
            .get("target_options")
            .get("odoo_storage_path"),
        )

    def test_interface_values(self):
        protocol = "file"  # should be available by default in the list of protocols
        with Form(self.env["fs.storage"]) as new_storage:
            new_storage.name = "Test storage"
            new_storage.code = "code"
            new_storage.protocol = protocol
            self.assertEqual(new_storage.protocol, protocol)
            # the options should follow the protocol
            self.assertEqual(new_storage.options_protocol, protocol)
            description = new_storage.protocol_descr
            self.assertTrue("Interface to files on local storage" in description)
        # this is still true after saving
        self.assertEqual(new_storage.options_protocol, protocol)

    def test_options_env(self):
        self.backend.json_options = {"key": {"sub_key": "$KEY_VAR"}}
        eval_json_options = {"key": {"sub_key": "TEST"}}
        options = self.backend._get_fs_options()
        self.assertDictEqual(options, self.backend.json_options)
        self.backend.eval_options_from_env = True
        with mock.patch.dict("os.environ", {"KEY_VAR": "TEST"}):
            options = self.backend._get_fs_options()
            self.assertDictEqual(options, eval_json_options)
        with self.assertLogs(level="WARNING") as log:
            options = self.backend._get_fs_options()
        self.assertIn(
            (
                f"Environment variable KEY_VAR is not set for "
                f"fs_storage {self.backend.display_name}."
            ),
            log.output[0],
        )

    def test_compute_model_ids(self):
        """
        Give a list of model xmlids and check that the o2m field model_ids
        is correctly fulfilled.
        """
        self.backend.model_xmlids = "base.model_res_partner,base.model_ir_attachment"

        model_ids = self.backend.model_ids
        self.assertEqual(len(model_ids), 2)
        model_names = model_ids.mapped("model")
        self.assertEqual(set(model_names), {"res.partner", "ir.attachment"})

    def test_inverse_model_ids(self):
        """
        Modify backend model_ids and check the char field model_xmlids
        is correctly updated
        """
        model_1 = self.env["ir.model"].search([("model", "=", "res.partner")])
        model_2 = self.env["ir.model"].search([("model", "=", "ir.attachment")])
        self.backend.model_ids = [(6, 0, [model_1.id, model_2.id])]
        self.assertEqual(
            self.backend.model_xmlids,
            "base.model_res_partner,base.model_ir_attachment",
        )

    def test_compute_field_ids(self):
        """
        Give a list of field xmlids and check that the o2m field field_ids
        is correctly fulfilled.
        """
        self.backend.field_xmlids = (
            "base.field_res_partner__id,base.field_res_partner__create_date"
        )

        field_ids = self.backend.field_ids
        self.assertEqual(len(field_ids), 2)
        field_names = field_ids.mapped("name")
        self.assertEqual(set(field_names), {"id", "create_date"})
        field_models = field_ids.mapped("model")
        self.assertEqual(set(field_models), {"res.partner"})

    def test_inverse_field_ids(self):
        """
        Modify backend field_ids and check the char field field_xmlids
        is correctly updated
        """
        field_1 = self.env["ir.model.fields"].search(
            [("model", "=", "res.partner"), ("name", "=", "id")]
        )
        field_2 = self.env["ir.model.fields"].search(
            [("model", "=", "res.partner"), ("name", "=", "create_date")]
        )
        self.backend.field_ids = [(6, 0, [field_1.id, field_2.id])]
        self.assertEqual(
            self.backend.field_xmlids,
            "base.field_res_partner__id,base.field_res_partner__create_date",
        )

    def test_constraint_unique_storage_model(self):
        """
        A given model can be linked to a unique storage
        """
        self.backend.model_xmlids = "base.model_res_partner,base.model_ir_attachment"
        self.env.ref("fs_storage.fs_storage_demo")
        with self.assertRaises(ValidationError):
            self.copy_backend.model_xmlids = "base.model_res_partner"

    def test_constraint_unique_storage_field(self):
        """
        A given field can be linked to a unique storage
        """
        self.backend.field_xmlids = (
            "base.field_res_partner__id,base.field_res_partner__name"
        )
        with self.assertRaises(ValidationError):
            self.copy_backend.field_xmlids = "base.field_res_partner__name"

    def test_directory_path_substitution(self):
        template = "dir/{db_name}"
        self.backend.directory_path = template
        # Assert different (db name should be replaced)
        self.assertNotEqual(template, self.backend.get_directory_path())
