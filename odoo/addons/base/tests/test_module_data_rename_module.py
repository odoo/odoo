from odoo.tests.common import TransactionCase, tagged
from odoo.tools.module_data import rename_module


@tagged("post_install", "-at_install")
class TestRenameModule(TransactionCase):
    def _insert_module(self, name, state="installed"):
        self.env.cr.execute(
            "INSERT INTO ir_module_module (name, state, data_file_checksums) "
            "VALUES (%s, %s, '{}'::jsonb) RETURNING id",
            [name, state],
        )
        module_id = self.env.cr.fetchone()[0]
        self.env.cr.execute(
            "INSERT INTO ir_model_data (module, name, model, res_id, noupdate) "
            "VALUES ('base', %s, 'ir.module.module', %s, true)",
            [f"module_{name}", module_id],
        )
        return module_id

    def _insert_xmlid(self, module, name):
        self.env.cr.execute(
            "INSERT INTO ir_model_data (module, name, model, res_id) "
            "VALUES (%s, %s, 'res.partner', 1)",
            [module, name],
        )

    def _read(self, query, params=None):
        self.env.cr.execute(query, params)
        return self.env.cr.fetchall()

    def setUp(self):
        super().setUp()
        self.old_id = self._insert_module("probe_old")
        dependant_id = self._insert_module("probe_dependant")
        self.env.cr.execute(
            "INSERT INTO ir_module_module_dependency (module_id, name) "
            "VALUES (%s, 'probe_old')",
            [dependant_id],
        )
        self._insert_xmlid("probe_old", "probe_record")
        self.env["ir.config_parameter"].set_param("probe_old.setting", "kept")
        self.view = self.env["ir.ui.view"].create(
            {
                "name": "probe",
                "type": "qweb",
                "key": "probe_old.probe_template",
                "arch": "<t t-name='probe'><t t-call='probe_old.probe_template'/></t>",
            }
        )
        self.asset = self.env["ir.asset"].create(
            {
                "name": "probe",
                "bundle": "web.assets_backend",
                "path": "probe_old/static/src/probe.js",
            }
        )

    def test_the_row_its_xmlids_and_every_stored_reference_take_the_new_name(self):
        self.assertTrue(rename_module(self.env.cr, "probe_old", "probe_new"))
        self.assertEqual(
            self._read(
                "SELECT name FROM ir_module_module WHERE id = %s", [self.old_id]
            ),
            [("probe_new",)],
        )
        self.assertEqual(
            self._read("SELECT module FROM ir_model_data WHERE name = 'probe_record'"),
            [("probe_new",)],
        )
        self.assertEqual(
            self._read(
                "SELECT name FROM ir_model_data "
                "WHERE module = 'base' AND res_id = %s AND model = 'ir.module.module'",
                [self.old_id],
            ),
            [("module_probe_new",)],
        )
        self.assertEqual(
            self._read(
                "SELECT count(*) FROM ir_module_module_dependency "
                "WHERE name = 'probe_new'"
            ),
            [(1,)],
        )
        self.assertEqual(
            self._read(
                "SELECT value FROM ir_config_parameter WHERE key = 'probe_new.setting'"
            ),
            [("kept",)],
        )
        self.assertEqual(
            self._read("SELECT key FROM ir_ui_view WHERE id = %s", [self.view.id]),
            [("probe_new.probe_template",)],
        )
        self.assertEqual(
            self._read("SELECT path FROM ir_asset WHERE id = %s", [self.asset.id]),
            [("probe_new/static/src/probe.js",)],
        )

    def test_a_database_without_the_module_is_left_alone(self):
        self.assertFalse(rename_module(self.env.cr, "probe_absent", "probe_new"))
        self.assertEqual(
            self._read(
                "SELECT name FROM ir_module_module WHERE id = %s", [self.old_id]
            ),
            [("probe_old",)],
        )

    def test_an_uninstalled_placeholder_under_the_new_name_gives_way(self):
        placeholder_id = self._insert_module("probe_new", state="uninstalled")
        rename_module(self.env.cr, "probe_old", "probe_new")
        self.assertEqual(
            self._read("SELECT id FROM ir_module_module WHERE name = 'probe_new'"),
            [(self.old_id,)],
        )
        self.assertFalse(
            self._read(
                "SELECT 1 FROM ir_model_data WHERE model = 'ir.module.module' "
                "AND res_id = %s",
                [placeholder_id],
            )
        )

    def test_an_installed_module_under_the_new_name_stops_the_upgrade(self):
        self._insert_module("probe_new")
        with self.assertRaisesRegex(ValueError, "probe_new is installed"):
            rename_module(self.env.cr, "probe_old", "probe_new")

    def test_an_xmlid_both_modules_own_stops_the_upgrade(self):
        self._insert_module("probe_new", state="uninstalled")
        self._insert_xmlid("probe_new", "probe_record")
        with self.assertRaisesRegex(ValueError, "both own \\['probe_record'\\]"):
            rename_module(self.env.cr, "probe_old", "probe_new")
