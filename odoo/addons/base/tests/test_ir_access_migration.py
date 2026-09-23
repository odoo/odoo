from odoo.modules.module import get_module_path, load_script
from odoo.tests import TransactionCase, new_test_user, tagged

OLD_TABLES = """
    CREATE TABLE IF NOT EXISTS ir_model_access (
        id serial PRIMARY KEY, name varchar, model_id int, group_id int,
        active boolean, perm_read boolean, perm_write boolean,
        perm_create boolean, perm_unlink boolean
    );
    CREATE TABLE IF NOT EXISTS ir_rule (
        id serial PRIMARY KEY, name varchar, model_id int, domain_force text,
        composition varchar, active boolean, global boolean, perm_read boolean,
        perm_write boolean, perm_create boolean, perm_unlink boolean
    );
    CREATE TABLE IF NOT EXISTS rule_group_rel (rule_group_id int, group_id int);
"""


@tagged("post_install", "-at_install")
class TestIrAccessMigration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.script = load_script(
            f"{get_module_path('base')}/migrations/1.97/pre-migrate_ir_access_rows.py",
            "base_1_97_pre_migrate_ir_access_rows",
        )
        cls.model = cls.env["ir.model"]._get("res.partner.industry")
        # the tables 1.97 read are gone since 1.100: the test builds what it reads
        cls.env.cr.execute(OLD_TABLES)
        cls.user = new_test_user(
            cls.env, login="migrated_probe", groups="base.group_user"
        )

    def _insert_line(self, name):
        self.env.cr.execute(
            """
            INSERT INTO ir_model_access (name, model_id, group_id, active, perm_read,
                                         perm_write, perm_create, perm_unlink)
            VALUES (%s, %s, %s, true, true, true, true, true)
            """,
            [name, self.model.id, self.env.ref("base.group_user").id],
        )

    def _insert_rule(self, name, is_global):
        self.env.cr.execute(
            """
            INSERT INTO ir_rule (name, model_id, domain_force, active, global,
                                 composition, perm_read, perm_write, perm_create,
                                 perm_unlink)
            VALUES (%s, %s, '[(''id'', ''='', 0)]', true, %s, 'grant', false, false,
                    false, true)
            """,
            [name, self.model.id, is_global],
        )

    def _migrated(self, *names):
        self.env.flush_all()
        self.script.migrate(self.env.cr, "1.96")
        self.env.invalidate_all()
        self.env.registry.clear_cache("stable")
        return (
            self.env["ir.access"]
            .with_context(active_test=False)
            .search([("name", "in", names)])
        )

    def test_a_rule_with_no_group_that_is_not_global_binds_nobody(self):
        self._insert_line("probe line")
        self._insert_rule("probe orphaned rule", False)
        rows = self._migrated("probe line", "probe orphaned rule")
        self.assertEqual(rows.mapped("name"), ["probe line"])
        industry = self.env["res.partner.industry"].create({"name": "Probe"})
        industry.with_user(self.user).unlink()
        self.assertFalse(industry.exists())

    def test_a_global_rule_becomes_a_guard_on_everyone(self):
        self._insert_line("probe line")
        self._insert_rule("probe global rule", True)
        guard = self._migrated("probe global rule")
        self.assertEqual(
            (guard.kind, guard.guard_scope, guard.operation, guard.group_id),
            ("guard", "everyone", "d", self.env.ref("base.group_everyone")),
        )

    def test_the_old_tables_are_emptied_and_their_external_ids_moved(self):
        self._insert_line("probe line")
        self.env.cr.execute("SELECT max(id) FROM ir_model_access")
        [line_id] = self.env.cr.fetchone()
        self.env["ir.model.data"].create(
            {
                "module": "base",
                "name": "probe_line",
                "model": "ir.model.access",
                "res_id": line_id,
                "noupdate": True,
            }
        )
        row = self._migrated("probe line")
        self.env.cr.execute("SELECT count(*) FROM ir_model_access")
        self.assertEqual(self.env.cr.fetchone(), (0,))
        self.assertEqual(self.env.ref("base.probe_line"), row)
        data = self.env["ir.model.data"].search(
            [("module", "=", "base"), ("name", "=", "probe_line")]
        )
        self.assertEqual((data.model, data.noupdate), ("ir.access", True))

    def test_a_noupdate_rule_the_file_ships_as_another_kind_is_left_to_it(self):
        # base ships res_users_log_rule as a guard on everyone: a database whose
        # noupdate rule under that id is a group rule leaves it to the file
        self._insert_line("probe line")
        self.env.cr.execute(
            """
            INSERT INTO ir_rule (name, model_id, domain_force, active, global,
                                 composition, perm_read, perm_write, perm_create,
                                 perm_unlink)
            VALUES ('probe reshaped rule', %s, '[(''id'', ''='', 0)]', true, false,
                    'grant', true, true, true, true)
            RETURNING id
            """,
            [self.model.id],
        )
        [rule_id] = self.env.cr.fetchone()
        self.env.cr.execute(
            "INSERT INTO rule_group_rel (rule_group_id, group_id) VALUES (%s, %s)",
            [rule_id, self.env.ref("base.group_user").id],
        )
        self.env["ir.model.data"].search(
            [("module", "=", "base"), ("name", "=", "res_users_log_rule")]
        ).unlink()
        self.env["ir.model.data"].create(
            {
                "module": "base",
                "name": "res_users_log_rule",
                "model": "ir.rule",
                "res_id": rule_id,
                "noupdate": True,
            }
        )
        row = self._migrated("probe reshaped rule")
        self.assertEqual(
            (row.kind, row.group_id), ("permission", self.env.ref("base.group_user"))
        )
        data = self.env["ir.model.data"].search(
            [("module", "=", "base"), ("name", "=", "res_users_log_rule")]
        )
        self.assertEqual((data.res_id, data.noupdate), (row.id, False))


@tagged("post_install", "-at_install")
class TestOldAccessTablesDropped(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.script = load_script(
            f"{get_module_path('base')}/migrations/1.100/end-migrate_old_access_tables.py",
            "base_1_100_end_migrate_old_access_tables",
        )
        cls.model = cls.env["ir.model"]._get("res.partner.industry")
        cls.env.cr.execute(OLD_TABLES)

    def _relations(self):
        self.env.cr.execute(
            "SELECT relname FROM pg_class WHERE relname = ANY(%s) ORDER BY relname",
            [["ir_model_access", "ir_rule", "rule_group_rel"]],
        )
        return [name for [name] in self.env.cr.fetchall()]

    def test_the_tables_and_the_models_metadata_go(self):
        self.env.cr.execute(
            """
            INSERT INTO ir_model (model, name, state, "order")
            VALUES ('ir.rule', '{"en_US": "Record Rule"}', 'base', 'id')
            RETURNING id
            """
        )
        [model_id] = self.env.cr.fetchone()
        self.env.cr.execute(
            "INSERT INTO ir_model_data (module, name, model, res_id, noupdate) "
            "VALUES ('base', 'model_ir_rule', 'ir.model', %s, false)",
            [model_id],
        )
        self.assertEqual(
            self._relations(), ["ir_model_access", "ir_rule", "rule_group_rel"]
        )
        self.script.migrate(self.env.cr, "1.98")
        self.assertEqual(self._relations(), [])
        self.env.cr.execute("SELECT count(*) FROM ir_model WHERE model = 'ir.rule'")
        self.assertEqual(self.env.cr.fetchone(), (0,))
        self.env.cr.execute(
            "SELECT count(*) FROM ir_model_data WHERE name = 'model_ir_rule'"
        )
        self.assertEqual(self.env.cr.fetchone(), (0,))

    def test_a_line_written_after_the_conversion_is_converted_not_lost(self):
        self.env.cr.execute(
            """
            INSERT INTO ir_model_access (name, model_id, group_id, active, perm_read,
                                         perm_write, perm_create, perm_unlink)
            VALUES ('probe late line', %s, %s, true, true, false, false, false)
            """,
            [self.model.id, self.env.ref("base.group_user").id],
        )
        self.env.flush_all()
        self.script.migrate(self.env.cr, "1.98")
        self.env.invalidate_all()
        row = self.env["ir.access"].search([("name", "=", "probe late line")])
        self.assertEqual(
            (row.kind, row.operation, row.group_id),
            ("permission", "r", self.env.ref("base.group_user")),
        )
        self.assertEqual(self._relations(), [])

    def test_a_fresh_install_has_nothing_to_do(self):
        self.script.migrate(self.env.cr, None)
        self.assertEqual(
            self._relations(), ["ir_model_access", "ir_rule", "rule_group_rel"]
        )
