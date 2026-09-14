from odoo.db.schema import column_exists, table_exists
from odoo.tests.common import TransactionCase, tagged
from odoo.tools.module_data import rename_in_stored_expressions, rename_model


@tagged("post_install", "-at_install")
class TestRenameModel(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cr = cls.env.cr
        cr.execute("""
            CREATE TABLE probe_thing (id serial PRIMARY KEY, name varchar);
            ALTER TABLE probe_thing ADD CONSTRAINT probe_thing_name_uniq UNIQUE (name);
            CREATE TABLE probe_thing_member (
                id serial PRIMARY KEY,
                probe_thing_id int REFERENCES probe_thing (id),
                ref varchar
            );
            CREATE TABLE probe_thing_res_users_rel (
                probe_thing_id int REFERENCES probe_thing (id),
                res_users_id int
            );
            CREATE TABLE probe_log (res_model varchar);
            INSERT INTO probe_log VALUES ('probe.thing'), ('probe.thing.member');
            INSERT INTO ir_filters (name, model_id, sort, domain, context, active)
                 VALUES ('probe', 'probe.thing', '[]', '[]', '{}', true);
            INSERT INTO probe_thing_member (ref)
                 VALUES ('probe.thing,5'), ('probe.thing.member,5');
        """)
        cls.thing_model_id = cls._insert_model("probe.thing")
        cls.member_model_id = cls._insert_model("probe.thing.member")
        cls._insert_field(cls.thing_model_id, "probe.thing", "name", "char")
        cls._insert_field(
            cls.thing_model_id,
            "probe.thing",
            "user_ids",
            "many2many",
            relation="res.users",
            relation_table="probe_thing_res_users_rel",
            column1="probe_thing_id",
            column2="res_users_id",
        )
        cls._insert_field(
            cls.member_model_id,
            "probe.thing.member",
            "probe_thing_id",
            "many2one",
            relation="probe.thing",
        )
        cls._insert_field(cls.member_model_id, "probe.thing.member", "ref", "reference")
        cr.execute("SELECT id FROM ir_module_module WHERE name = 'base'")
        base_id = cr.fetchone()[0]
        for name, model_id in (
            ("probe_thing_name_uniq", cls.thing_model_id),
            ("probe_thing_member_ref_uniq", cls.member_model_id),
        ):
            cr.execute(
                "INSERT INTO ir_model_constraint (name, type, model, module) "
                "VALUES (%s, 'u', %s, %s)",
                (name, model_id, base_id),
            )
        for name, model, res_id in (
            ("model_probe_thing", "ir.model", cls.thing_model_id),
            ("model_probe_thing_member", "ir.model", cls.member_model_id),
        ):
            cr.execute(
                "INSERT INTO ir_model_data (module, name, model, res_id) "
                "VALUES ('test_rename', %s, %s, %s)",
                (name, model, res_id),
            )
        cr.execute("""
            INSERT INTO ir_model_data (module, name, model, res_id)
            SELECT 'test_rename', 'field_' || replace(model, '.', '_') || '__' || name,
                   'ir.model.fields', id
              FROM ir_model_fields WHERE model LIKE 'probe.thing%'
        """)
        cls.view = cls.env["ir.ui.view"].create(
            {
                "name": "probe",
                "model": "res.partner",
                "type": "search",
                "arch": """<search>
                    <filter name="a" string="a" context="{'m': 'probe.thing'}"/>
                    <filter name="b" string="b" context="{'m': 'probe.thing.member'}"/>
                </search>""",
            }
        )
        cls.env.flush_all()
        cls.relations = rename_model(cr, "probe.thing", "team.probe")

    @classmethod
    def _insert_model(cls, model):
        cls.env.cr.execute(
            'INSERT INTO ir_model (model, name, "order", state) '
            "VALUES (%s, %s, 'id', 'base') RETURNING id",
            (model, '{"en_US": "probe"}'),
        )
        return cls.env.cr.fetchone()[0]

    @classmethod
    def _insert_field(cls, model_id, model, name, ttype, **values):
        columns = [
            "model_id",
            "model",
            "name",
            "ttype",
            "state",
            "field_description",
            "store",
        ]
        params = [model_id, model, name, ttype, "base", '{"en_US": "probe"}', True]
        for column, value in values.items():
            columns.append(column)
            params.append(value)
        cls.env.cr.execute(
            "INSERT INTO ir_model_fields (%s) VALUES (%s)"
            % (", ".join(columns), ", ".join(["%s"] * len(params))),
            params,
        )

    def _scalar(self, query, params=()):
        self.env.cr.execute(query, params)
        return [row[0] for row in self.env.cr.fetchall()]

    def test_the_table_sequence_and_constraints_follow_the_model(self):
        self.assertTrue(table_exists(self.env.cr, "team_probe"))
        self.assertFalse(table_exists(self.env.cr, "probe_thing"))
        self.assertEqual(
            self._scalar(
                "SELECT sequencename FROM pg_sequences WHERE sequencename = %s",
                ("team_probe_id_seq",),
            ),
            ["team_probe_id_seq"],
        )
        self.assertIn(
            "team_probe_name_uniq",
            self._scalar(
                "SELECT conname FROM pg_constraint WHERE conrelid = 'team_probe'::regclass"
            ),
        )

    def test_a_model_whose_table_merely_starts_with_the_old_one_is_untouched(self):
        self.assertTrue(table_exists(self.env.cr, "probe_thing_member"))
        self.assertEqual(
            self._scalar(
                "SELECT model FROM ir_model WHERE id = %s", (self.member_model_id,)
            ),
            ["probe.thing.member"],
        )
        self.assertEqual(
            sorted(
                self._scalar(
                    "SELECT name FROM ir_model_constraint WHERE model = ANY(%s)",
                    ([self.thing_model_id, self.member_model_id],),
                )
            ),
            ["probe_thing_member_ref_uniq", "team_probe_name_uniq"],
        )
        self.assertEqual(
            sorted(
                self._scalar(
                    "SELECT name FROM ir_model_data WHERE module = 'test_rename'"
                )
            ),
            [
                "field_probe_thing_member__probe_thing_id",
                "field_probe_thing_member__ref",
                "field_team_probe__name",
                "field_team_probe__user_ids",
                "model_probe_thing_member",
                "model_team_probe",
            ],
        )

    def test_a_derived_join_table_is_renamed_in_the_orms_sort_order(self):
        self.assertEqual(
            self.relations, {"probe_thing_res_users_rel": "res_users_team_probe_rel"}
        )
        self.assertTrue(
            column_exists(self.env.cr, "res_users_team_probe_rel", "team_probe_id")
        )
        self.env.cr.execute(
            "SELECT relation_table, column1, column2 FROM ir_model_fields "
            "WHERE model = 'team.probe' AND name = 'user_ids'"
        )
        self.assertEqual(
            self.env.cr.fetchone(),
            ("res_users_team_probe_rel", "team_probe_id", "res_users_id"),
        )

    def test_relations_model_name_columns_and_references_are_repointed(self):
        self.assertEqual(
            self._scalar(
                "SELECT relation FROM ir_model_fields "
                "WHERE model = 'probe.thing.member' AND name = 'probe_thing_id'"
            ),
            ["team.probe"],
        )
        self.assertEqual(
            sorted(self._scalar("SELECT res_model FROM probe_log")),
            ["probe.thing.member", "team.probe"],
        )
        self.assertEqual(
            sorted(self._scalar("SELECT ref FROM probe_thing_member")),
            ["probe.thing.member,5", "team.probe,5"],
        )

    def test_a_saved_filter_follows_the_model(self):
        self.assertEqual(
            self._scalar("SELECT model_id FROM ir_filters WHERE name = 'probe'"),
            ["team.probe"],
        )

    def test_a_quoted_model_name_is_rewritten_in_a_view_but_not_its_extension(self):
        self.view.invalidate_recordset(["arch_db"])
        arch = self.view.arch_db
        self.assertIn("'team.probe'", arch)
        self.assertIn("'probe.thing.member'", arch)
        self.assertNotIn("'probe.thing'", arch)

    def test_renaming_again_changes_nothing(self):
        self.assertEqual(rename_model(self.env.cr, "probe.thing", "team.probe"), {})
        self.assertTrue(table_exists(self.env.cr, "team_probe"))


@tagged("post_install", "-at_install")
class TestRenameInStoredExpressions(TransactionCase):
    def _rule(self, model, domain):
        self.env.cr.execute(
            "INSERT INTO ir_rule (name, model_id, domain_force, composition, active) "
            "VALUES ('probe', (SELECT id FROM ir_model WHERE model = %s), %s, "
            "'or', true) RETURNING id",
            (model, domain),
        )
        return self.env.cr.fetchone()[0]

    def _domain(self, rule_id):
        self.env.cr.execute(
            "SELECT domain_force FROM ir_rule WHERE id = %s", (rule_id,)
        )
        return self.env.cr.fetchone()[0]

    def test_a_bare_name_needs_a_model_unless_it_is_unique(self):
        with self.assertRaises(ValueError):
            rename_in_stored_expressions(self.env.cr, "probe_team_ids", "probe_x_ids")

    def test_a_unique_name_is_rewritten_through_any_path_in_a_rule(self):
        rule_id = self._rule(
            "res.partner", "[('user_id.probe_team_ids', 'in', user.probe_team_ids.ids)]"
        )
        other_id = self._rule("res.partner", "[('probe_team_ids_count', '>', 0)]")

        rename_in_stored_expressions(
            self.env.cr, "probe_team_ids", "probe_sale_team_ids", unique=True
        )

        self.assertEqual(
            self._domain(rule_id),
            "[('user_id.probe_sale_team_ids', 'in', user.probe_sale_team_ids.ids)]",
        )
        self.assertEqual(self._domain(other_id), "[('probe_team_ids_count', '>', 0)]")

    def test_a_scoped_rename_leaves_other_models_rules_alone(self):
        partner_rule = self._rule("res.partner", "[('probe_flag', '=', True)]")
        user_rule = self._rule("res.users", "[('probe_flag', '=', True)]")

        rename_in_stored_expressions(
            self.env.cr, "probe_flag", "probe_new_flag", model="res.users"
        )

        self.assertEqual(self._domain(partner_rule), "[('probe_flag', '=', True)]")
        self.assertEqual(self._domain(user_rule), "[('probe_new_flag', '=', True)]")
