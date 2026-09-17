import traceback
from contextlib import ExitStack, contextmanager
from unittest.mock import patch

from psycopg import IntegrityError
from psycopg.errors import NotNullViolation
from psycopg.types.json import Json

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import NO_ACCESS
from odoo.models import BaseModel, is_model_definition, pop_field
from odoo.tests import Form, HttpCase, TransactionCase, tagged
from odoo.tests.common import new_test_user
from odoo.tools import SQL, escape_psql, mute_logger

from odoo.addons.base.models import (
    ir_model,
    ir_model_fields,
    ir_model_fields_selection,
)
from odoo.addons.base.models.ir_model_common import MODULE_UNINSTALL_FLAG, upsert_en


class TestXMLID(TransactionCase):
    def get_data(self, xml_id):
        module, suffix = xml_id.split(".", 1)
        domain = [("module", "=", module), ("name", "=", suffix)]
        return self.env["ir.model.data"].search(domain)

    def test_create(self):
        model = self.env["res.partner.tag"]
        xml_id = "test_convert.category_foo"

        data = {"xml_id": xml_id, "values": {"name": "Foo"}}
        category = model._load_records([data])
        self.assertEqual(category, self.env.ref(xml_id, raise_if_not_found=False))
        self.assertEqual(category.name, "Foo")
        self.assertEqual(self.get_data(xml_id).noupdate, False)

        data = {"xml_id": xml_id, "values": {"name": "Bar"}}
        category1 = model._load_records([data], update=True)
        self.assertEqual(category, category1)
        self.assertEqual(category.name, "Bar")
        self.assertEqual(self.get_data(xml_id).noupdate, False)

        data = {"xml_id": xml_id, "values": {"name": "Baz"}, "noupdate": True}
        category2 = model._load_records([data], update=True)
        self.assertEqual(category, category2)
        self.assertEqual(category.name, "Baz")
        self.assertEqual(self.get_data(xml_id).noupdate, False)

    def test_create_noupdate(self):
        model = self.env["res.partner.tag"]
        xml_id = "test_convert.category_foo"

        data = {"xml_id": xml_id, "values": {"name": "Foo"}, "noupdate": True}
        category = model._load_records([data])
        self.assertEqual(category, self.env.ref(xml_id, raise_if_not_found=False))
        self.assertEqual(category.name, "Foo")
        self.assertEqual(self.get_data(xml_id).noupdate, True)

        data = {"xml_id": xml_id, "values": {"name": "Bar"}, "noupdate": False}
        category1 = model._load_records([data], update=True)
        self.assertEqual(category, category1)
        self.assertEqual(category.name, "Foo")
        self.assertEqual(self.get_data(xml_id).noupdate, True)

        data = {"xml_id": xml_id, "values": {"name": "Baz"}, "noupdate": True}
        category2 = model._load_records([data], update=True)
        self.assertEqual(category, category2)
        self.assertEqual(category.name, "Foo")
        self.assertEqual(self.get_data(xml_id).noupdate, True)

    def test_create_noupdate_multi(self):
        model = self.env["res.partner.tag"]
        data_list = [
            {
                "xml_id": "test_convert.category_foo",
                "values": {"name": "Foo"},
                "noupdate": True,
            },
            {
                "xml_id": "test_convert.category_bar",
                "values": {"name": "Bar"},
                "noupdate": True,
            },
        ]

        categories = model._load_records(data_list)
        foo = self.env.ref("test_convert.category_foo")
        bar = self.env.ref("test_convert.category_bar")
        self.assertEqual(categories, foo + bar)
        self.assertEqual(foo.name, "Foo")
        self.assertEqual(bar.name, "Bar")

        self.assertEqual(self.get_data("test_convert.category_foo").noupdate, True)
        self.assertEqual(self.get_data("test_convert.category_bar").noupdate, True)

    def test_create_order(self):
        model = self.env["res.partner.tag"]
        data_list = [
            {"xml_id": "test_convert.category_foo", "values": {"name": "Foo"}},
            {
                "xml_id": "test_convert.category_bar",
                "values": {"name": "Bar"},
                "noupdate": True,
            },
            {"xml_id": "test_convert.category_baz", "values": {"name": "Baz"}},
        ]

        foo = model._load_records([data_list[0]])
        bar = model._load_records([data_list[1]])
        baz = model._load_records([data_list[2]])
        self.assertEqual(foo.name, "Foo")
        self.assertEqual(bar.name, "Bar")
        self.assertEqual(baz.name, "Baz")

        for data in data_list:
            data["values"]["name"] += "X"
        cats = model._load_records(data_list, update=True)
        self.assertEqual(list(cats), [foo, bar, baz])
        self.assertEqual(foo.name, "FooX")
        self.assertEqual(bar.name, "Bar")
        self.assertEqual(baz.name, "BazX")

    def test_create_inherits(self):
        model = self.env["res.users"]
        xml_id = "test_convert.user_foo"
        par_xml_id = xml_id + "_res_partner"

        user = model._load_records(
            [{"xml_id": xml_id, "values": {"name": "Foo", "login": "foo"}}]
        )
        self.assertEqual(user, self.env.ref(xml_id, raise_if_not_found=False))
        self.assertEqual(
            user.partner_id, self.env.ref(par_xml_id, raise_if_not_found=False)
        )
        self.assertEqual(user.name, "Foo")
        self.assertEqual(user.login, "foo")

    def test_recreate(self):
        model = self.env["res.partner.tag"]
        xml_id = "test_convert.category_foo"
        data = {"xml_id": xml_id, "values": {"name": "Foo"}}

        category = model._load_records([data])
        self.assertEqual(category, self.env.ref(xml_id, raise_if_not_found=False))
        self.assertEqual(category.name, "Foo")

        category.unlink()
        self.assertFalse(self.env.ref(xml_id, raise_if_not_found=False))

        category = model._load_records([data], update=True)
        self.assertEqual(category, self.env.ref(xml_id, raise_if_not_found=False))
        self.assertEqual(category.name, "Foo")

    def test_create_xmlids(self):
        foo, bar = self.env["res.users"]._load_records(
            [
                {
                    "xml_id": "test_convert.foo",
                    "values": {"name": "Foo", "login": "foo"},
                    "noupdate": True,
                },
                {
                    "xml_id": "test_convert.bar",
                    "values": {"name": "Bar", "login": "bar"},
                    "noupdate": True,
                },
            ]
        )

        self.assertEqual(
            foo, self.env.ref("test_convert.foo", raise_if_not_found=False)
        )
        self.assertEqual(
            bar, self.env.ref("test_convert.bar", raise_if_not_found=False)
        )

        self.assertEqual(
            foo.partner_id,
            self.env.ref("test_convert.foo_res_partner", raise_if_not_found=False),
        )
        self.assertEqual(
            bar.partner_id,
            self.env.ref("test_convert.bar_res_partner", raise_if_not_found=False),
        )

        self.assertEqual(self.get_data("test_convert.foo").noupdate, True)
        self.assertEqual(self.get_data("test_convert.bar").noupdate, True)

    @mute_logger(
        "odoo.db",
        "odoo.addons.base.models.ir_model",
        "odoo.addons.base.models.ir_model_data",
    )
    def test_create_external_id_with_space(self):
        model = self.env["res.partner.tag"]
        data_list = [
            {
                "xml_id": "test_convert.category_with space",
                "values": {"name": "Bar"},
            }
        ]
        with self.assertRaisesRegex(IntegrityError, "ir_model_data_name_nospaces"):
            model._load_records(data_list)

    def test_update_xmlid(self):
        def assert_xmlid(xmlid, value, message):
            expected_values = (value._name, value.id)
            self.assertEqual(
                self.env["ir.model.data"]._get_xmlid_target(xmlid),
                expected_values,
                message,
            )
            with self.assertQueryCount(0):
                self.assertEqual(
                    self.env["ir.model.data"]._get_xmlid_target(xmlid),
                    expected_values,
                    message,
                )
            module, name = xmlid.split(".")
            self.env.cr.execute(
                "SELECT model, res_id FROM ir_model_data where module=%s and name=%s",
                [module, name],
            )
            self.assertEqual((value._name, value.id), self.env.cr.fetchone(), message)

        xmlid = "base.test_xmlid"
        records = self.env["ir.model.data"].search([], limit=6)
        # warm the field, default and clock caches the first create pays for
        self.env["ir.model.data"]._update_xmlids(
            [{"xml_id": "base.test_xmlid_warmup", "record": records[5]}]
        )
        # one read of the existing rows, then one insert or one update
        with self.assertQueryCount(2):
            self.env["ir.model.data"]._update_xmlids(
                [
                    {"xml_id": xmlid, "record": records[0]},
                ]
            )
        assert_xmlid(
            xmlid,
            records[0],
            f"The xmlid {xmlid} should have been created with record {records[0]}",
        )

        with self.assertQueryCount(2):
            self.env["ir.model.data"]._update_xmlids(
                [
                    {"xml_id": xmlid, "record": records[1]},
                ],
                update=True,
            )
        assert_xmlid(
            xmlid,
            records[1],
            f"The xmlid {xmlid} should have been updated with record {records[1]}",
        )

        with self.assertQueryCount(2):
            self.env["ir.model.data"]._update_xmlids(
                [
                    {"xml_id": xmlid, "record": records[2]},
                ]
            )
        assert_xmlid(
            xmlid,
            records[2],
            f"The xmlid {xmlid} should have been updated with record {records[1]}",
        )

        xmlid = "base.test_xmlid_noupdates"
        with self.assertQueryCount(2):
            self.env["ir.model.data"]._update_xmlids(
                [
                    {
                        "xml_id": xmlid,
                        "record": records[3],
                        "noupdate": True,
                    },
                ]
            )

        assert_xmlid(
            xmlid,
            records[3],
            f"The xmlid {xmlid} should have been created for record {records[2]}",
        )

        with self.assertQueryCount(1):
            self.env["ir.model.data"]._update_xmlids(
                [
                    {"xml_id": xmlid, "record": records[4]},
                ],
                update=True,
            )
        assert_xmlid(
            xmlid,
            records[3],
            f"The xmlid {xmlid} should not have been updated (update mode)",
        )

        with self.assertQueryCount(2):
            self.env["ir.model.data"]._update_xmlids(
                [
                    {"xml_id": xmlid, "record": records[5]},
                ]
            )
        assert_xmlid(
            xmlid,
            records[5],
            f"The xmlid {xmlid} should have been updated with record (not an update) {records[1]}",
        )


@tagged("-at_install", "post_install")
class TestIrModelEdition(TransactionCase):
    def test_new_ir_model_fields_related(self):
        model = self.env["ir.model"].create({"name": "Bananas", "model": "x_bananas"})
        with self.debug_mode():
            form = Form(
                self.env["ir.model.fields"].with_context(default_model_id=model.id)
            )
            form.related = "id"
            self.assertEqual(form.ttype, "integer")

    def test_delete_manual_models_with_base_fields(self):
        model = self.env["ir.model"].create(
            {
                "model": "x_test_base_delete",
                "name": "test base delete",
                "field_id": [
                    Command.create(
                        {
                            "name": "x_my_field",
                            "ttype": "char",
                        }
                    ),
                    Command.create(
                        {
                            "name": "active",
                            "ttype": "boolean",
                            "state": "base",
                        }
                    ),
                ],
            }
        )
        model2 = self.env["ir.model"].create(
            {
                "model": "x_test_base_delete2",
                "name": "test base delete2",
                "field_id": [
                    Command.create(
                        {
                            "name": "x_my_field2",
                            "ttype": "char",
                        }
                    ),
                    Command.create(
                        {
                            "name": "active",
                            "ttype": "boolean",
                            "state": "base",
                        }
                    ),
                ],
            }
        )
        self.assertTrue(model.exists())
        self.assertTrue(model2.exists())

        self.env["ir.model"].browse(model.ids + model2.ids).unlink()
        self.assertFalse(model.exists())
        self.assertFalse(model2.exists())

    def test_base_model_unlink_raises_the_model_level_message(self):
        model = self.env["ir.model"]._get("res.country")
        field_names = set(self.env.registry["res.country"]._fields)
        with self.assertRaisesRegex(UserError, "Model .* contains module data"):
            model.unlink()
        self.assertEqual(set(self.env.registry["res.country"]._fields), field_names)

    @mute_logger("odoo.db")
    def test_ir_model_fields_name_create(self):
        model = self.env["ir.model"].create({"name": "Bananas", "model": "x_bananas"})
        with self.assertRaises(NotNullViolation):
            self.env["ir.model.fields"].name_create("field_name")

        self.env["ir.model.fields"].with_context(
            default_model_id=model.id,
            default_model=model.name,
            default_ttype="char",
        ).name_create("field_name")

    def test_create_without_a_model_name_uses_the_default(self):
        model = self.env["ir.model"].create({"name": "Default name"})
        self.assertEqual(model.model, "x_")
        self.assertIn("x_", self.env.registry)

    def test_manual_model_rename_reaches_the_registry(self):
        model = self.env["ir.model"].create(
            {"name": "Before", "model": "x_renamed", "info": "old doc"}
        )
        self.assertEqual(self.env.registry["x_renamed"]._description, "Before")
        model.write({"name": "After", "info": "new doc"})
        self.assertEqual(self.env.registry["x_renamed"]._description, "After")
        self.assertEqual(
            self.env["ir.model"]._prepare_model_vals(self.env["x_renamed"])["info"],
            "new doc",
        )

    def test_base_model_order_write_skips_registry_setup(self):
        model = self.env["ir.model"]._get("res.country")
        with patch.object(type(self.env.registry), "setup_models") as setup:
            model.write({"order": model.order})
        setup.assert_not_called()

    def test_manual_model_write_that_changes_nothing_skips_registry_setup(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        model = self.env["ir.model"].create({"name": "Same", "model": "x_same"})
        with patch.object(type(self.env.registry), "setup_models") as setup:
            model.write({"name": "Same", "order": "id"})
            model.with_context(lang="fr_FR").write({"name": "Pareil"})
        setup.assert_not_called()
        self.assertEqual(self.env.registry["x_same"]._description, "Same")

    def test_model_deletion_forgets_its_many2many_relation_and_rebuilds_named(self):
        model = self.env["ir.model"].create(
            {
                "name": "Tagged",
                "model": "x_tagged",
                "field_id": [
                    Command.create(
                        {
                            "name": "x_partner_ids",
                            "ttype": "many2many",
                            "relation": "res.partner",
                        }
                    )
                ],
            }
        )
        registry = self.env.registry
        field = registry["x_tagged"]._fields["x_partner_ids"]
        triple = (field.relation, field.column1, field.column2)
        self.assertIn(
            ("x_tagged", "x_partner_ids"), registry.many2many_relations[triple]
        )
        with patch.object(
            type(registry), "setup_models", wraps=registry.setup_models
        ) as setup:
            model.unlink()
        self.assertNotIn("x_tagged", registry)
        self.assertNotIn(triple, registry.many2many_relations)
        self.assertTrue(setup.call_args_list)
        self.assertEqual(setup.call_args_list[-1].args[1], [])

    def test_model_deletion_survives_a_manual_many2one_on_a_delegating_parent(self):
        IrModel = self.env["ir.model"]
        model = IrModel.create({"name": "Target", "model": "x_target"})
        self.env["ir.model.fields"].create(
            {
                "model_id": IrModel._get("res.partner").id,
                "name": "x_target_id",
                "ttype": "many2one",
                "relation": "x_target",
            }
        )
        self.assertIn("x_target_id", self.env.registry["res.users"]._fields)
        model.unlink()
        self.assertNotIn("x_target", self.env.registry)
        self.assertNotIn("x_target_id", self.env.registry["res.partner"]._fields)
        self.assertNotIn("x_target_id", self.env.registry["res.users"]._fields)
        self.assertFalse(
            self.env["ir.model.fields"].search([("name", "=", "x_target_id")])
        )

    def test_model_deletion_survives_a_computed_field_depending_on_a_sibling(self):
        model = self.env["ir.model"].create(
            {
                "name": "Computed",
                "model": "x_computed",
                "field_id": [Command.create({"name": "x_name", "ttype": "char"})],
            }
        )
        self.env["ir.model.fields"].create(
            {
                "model_id": model.id,
                "name": "x_upper",
                "ttype": "char",
                "depends": "x_name",
                "compute": "for r in self: r['x_upper'] = (r.x_name or '').upper()",
                "store": True,
            }
        )
        record = self.env["x_computed"].create({"x_name": "abc"})
        self.assertEqual(record.x_upper, "ABC")
        model.unlink()
        self.assertNotIn("x_computed", self.env.registry)
        graph_fields = {
            f"{f.model_name}.{f.name}"
            for f in self.env.registry.field_depends_context
            if f.model_name == "x_computed"
        }
        self.assertEqual(graph_fields, set())

    def test_manual_model_data_is_the_class_source(self):
        self.env["ir.model"].create({"name": "Rows", "model": "x_rows"})
        self.env.flush_all()
        (row,) = [
            r
            for r in self.env["ir.model"]._get_manual_model_data()
            if r["model"] == "x_rows"
        ]
        self.assertEqual(row["name"], "Rows")
        attrs = self.env["ir.model"]._prepare_class_attrs(row)
        self.assertEqual(attrs["_description"], "Rows")
        self.assertEqual(attrs["_order"], "id")
        stored = {
            fname
            for fname, field in self.env["ir.model"]._fields.items()
            if field.store and field.column_type
        }
        self.assertLessEqual(stored, set(row))

    def test_reflect_models_empty_no_raise(self):
        self.assertIsNone(self.env["ir.model"]._reflect_models([]))

    def test_reflect_models_prewarms_get_id_cache(self):
        IrModel = self.env["ir.model"]
        model = IrModel.create({"model": "x_prewarm", "name": "Prewarm test"})
        self.env.registry.clear_cache("stable")
        IrModel._reflect_models(["x_prewarm"])
        with self.assertQueryCount(0):
            self.assertEqual(IrModel._get_id("x_prewarm"), model.id)

    def test_name_create_slugifies_name(self):
        IrModel = self.env["ir.model"]
        cases = [
            ("Coûts 2024!", "x_couts_2024"),
            ("My-Model", "x_my_model"),
            ("My New Model", "x_my_new_model"),
        ]
        for label, expected in cases:
            record_id, _display = IrModel.name_create(label)
            self.assertEqual(IrModel.browse(record_id).model, expected)

    def test_upsert_en_rejects_translated_conflict_column(self):
        from odoo.addons.base.models.ir_model_common import upsert_en

        IrModel = self.env["ir.model"]
        self.assertTrue(IrModel._fields["name"].translate)
        with self.assertRaises(ValueError):
            upsert_en(IrModel, ["name", "model"], [("X", "x_up")], conflict=["name"])

    def test_upsert_en_rejects_duplicate_conflict_keys(self):
        from odoo.addons.base.models.ir_model_common import upsert_en

        IrModel = self.env["ir.model"]
        with self.assertRaises(ValueError):
            upsert_en(
                IrModel,
                ["model", "name"],
                [("dup.model", "A"), ("dup.model", "B")],
                conflict=["model"],
            )

    def test_upsert_en_rejects_empty_fnames(self):
        from odoo.addons.base.models.ir_model_common import upsert_en

        IrModel = self.env["ir.model"]
        with self.assertRaises(ValueError):
            upsert_en(IrModel, [], [("x",)], conflict=["model"])

    def test_upsert_en_empty_rows_returns_empty(self):
        from odoo.addons.base.models.ir_model_common import upsert_en

        IrModel = self.env["ir.model"]
        self.assertEqual(
            upsert_en(IrModel, ["model", "name"], [], conflict=["model"]), []
        )

    def test_upsert_en_inserts_on_integer_conflict_columns(self):
        from odoo.addons.base.models.ir_model_common import upsert_en

        IrModel = self.env["ir.model"]
        company = IrModel._get("res.company")
        partner = IrModel._get("res.partner")
        partner_field = self.env["ir.model.fields"]._get("res.company", "partner_id")
        Inherit = self.env["ir.model.inherit"]
        self.assertFalse(
            Inherit.search(
                [("model_id", "=", company.id), ("parent_id", "=", partner.id)]
            )
        )
        [inherit_id] = upsert_en(
            Inherit,
            ["model_id", "parent_id", "parent_field_id"],
            [(company.id, partner.id, partner_field.id)],
            conflict=["model_id", "parent_id"],
        )
        self.assertEqual(Inherit.browse(inherit_id).parent_field_id, partner_field)

    def test_make_compute_filters_blank_dependencies(self):
        from odoo.addons.base.models.ir_model_common import prepare_compute

        compute = prepare_compute("pass", "field_a, , field_b,")
        self.assertEqual(compute._depends, ("field_a", "field_b"))
        self.assertEqual(compute.__name__, "compute")

    def test_manual_compute_failure_names_the_field(self):
        model = self.env["ir.model"].create({"model": "x_imc_boom", "name": "IMC boom"})
        self.env["ir.model.fields"].create(
            {
                "name": "x_src",
                "field_description": "Src",
                "model_id": model.id,
                "ttype": "char",
            }
        )
        self.env.flush_all()
        self.env["ir.model.fields"].create(
            {
                "name": "x_calc",
                "field_description": "Calc",
                "model_id": model.id,
                "ttype": "integer",
                "store": False,
                "readonly": True,
                "depends": "x_src",
                "compute": "for record in self:\n    record['x_calc'] = 1 / 0\n",
            }
        )
        self.env.flush_all()
        self.env.registry.setup_models(self.env.cr, [model.model])
        record = self.env[model.model].create({"x_src": "a"})

        try:
            record.read(["x_calc"])
        except ZeroDivisionError:
            frames = traceback.format_exc()
        else:
            self.fail("the compute code was expected to raise")
        self.assertIn("<compute x_imc_boom.x_calc>", frames)

    def test_manual_compute_syntax_error_names_the_field(self):
        from odoo.addons.base.models.ir_model_common import prepare_compute

        compute = prepare_compute("for record in self\n    pass\n", None, "x_m.x_f")
        with self.assertRaises(SyntaxError) as cm:
            compute(self.env["ir.model"])
        self.assertIn("<compute x_m.x_f>", str(cm.exception))

    def test_inherit_xmlid_format(self):
        from odoo.addons.base.models.ir_model_common import inherit_xmlid

        self.assertEqual(
            inherit_xmlid("base", "a.b", "c.d"), "base.model_inherit__a_b__c_d"
        )

    def test_compute_count_matches_table_rowcount(self):
        IrModel = self.env["ir.model"]
        concrete = IrModel._get("res.country")
        abstract = IrModel._get("base")
        expected = (
            self.env["res.country"].with_context(active_test=False).search_count([])
        )
        batch = concrete + abstract
        batch.invalidate_recordset(["count"])
        self.assertEqual(concrete.count, expected)
        self.assertEqual(abstract.count, 0)

    def test_model_deletion_drops_its_custom_m2m_tables(self):
        model = self.env["ir.model"].create({"model": "x_imod_m2m", "name": "IMOD m2m"})
        field = self.env["ir.model.fields"].create(
            {
                "name": "x_partners",
                "field_description": "Partners",
                "model_id": model.id,
                "ttype": "many2many",
                "relation": "res.partner",
            }
        )
        self.env.flush_all()
        table = field.relation_table
        self.env.cr.execute("SELECT to_regclass(%s)", (table,))
        self.assertIsNotNone(self.env.cr.fetchone()[0], "precondition: table exists")

        model.unlink()
        self.env.flush_all()

        self.env.cr.execute("SELECT to_regclass(%s)", (table,))
        self.assertIsNone(self.env.cr.fetchone()[0], "m2m table must not leak")

    def test_m2m_table_kept_while_another_field_uses_it(self):
        model = self.env["ir.model"].create(
            {"model": "x_imod_share", "name": "IMOD share"}
        )
        first = self.env["ir.model.fields"].create(
            {
                "name": "x_partners",
                "field_description": "Partners",
                "model_id": model.id,
                "ttype": "many2many",
                "relation": "res.partner",
            }
        )
        self.env.flush_all()
        table = first.relation_table
        self.env["ir.model.fields"].create(
            {
                "name": "x_partners_too",
                "field_description": "Partners again",
                "model_id": model.id,
                "ttype": "many2many",
                "relation": "res.partner",
                "relation_table": table,
                "column1": first.column1,
                "column2": first.column2,
            }
        )
        self.env.flush_all()

        first.unlink()
        self.env.flush_all()

        self.env.cr.execute("SELECT to_regclass(%s)", (table,))
        self.assertIsNotNone(
            self.env.cr.fetchone()[0], "another field still uses the table"
        )

    def test_compute_count_survives_a_missing_table(self):
        IrModel = self.env["ir.model"]
        orphan = IrModel.create({"model": "x_imod_notable", "name": "No table"})
        self.env.cr.execute("DROP TABLE IF EXISTS x_imod_notable CASCADE")
        self.env.invalidate_all()

        batch = IrModel._get("res.country") + orphan
        batch.invalidate_recordset(["count"])
        counts = {record.model: record.count for record in batch}

        self.assertEqual(counts["x_imod_notable"], 0)
        self.assertEqual(
            counts["res.country"],
            self.env["res.country"].with_context(active_test=False).search_count([]),
        )
        self.env.cr.execute("SELECT 1")
        self.assertEqual(self.env.cr.fetchone(), (1,), "transaction still usable")


@tagged("test_eval_context")
class TestEvalContext(TransactionCase):
    def test_module_usage(self):
        self.env["ir.model.fields"].create(
            {
                "name": "x_foo_bar_baz",
                "model_id": self.env["ir.model"]
                .search([("model", "=", "res.partner")])
                .id,
                "field_description": "foo",
                "ttype": "integer",
                "store": False,
                "depends": "name",
                "compute": (
                    "time.time()\ndatetime.datetime.now()\ndateutil.relativedelta.relativedelta(hours=1)"
                ),
            }
        )
        _ = self.env["res.partner"].create({"name": "foo"}).x_foo_bar_baz


@tagged("-at_install", "post_install")
class TestIrModelFieldsTranslation(HttpCase):
    def test_ir_model_fields_translation(self):
        group_order_template = self.env.ref(
            "sale.group_sale_order_template",
            raise_if_not_found=False,
        )
        if group_order_template:
            self.env.ref("base.group_user").write(
                {"implied_ids": [(4, group_order_template.id)]}
            )

        field = self.env["ir.model.fields"].search(
            [("model_id.model", "=", "res.users"), ("name", "=", "login")]
        )
        self.assertEqual(field.with_context(lang="en_US").field_description, "Login")
        self.start_tour("/odoo", "ir_model_fields_translation_en_tour", login="admin")
        field.update_field_translations("field_description", {"en_US": "Login2"})
        self.start_tour("/odoo", "ir_model_fields_translation_en_tour2", login="admin")

        self.env["res.lang"]._activate_lang("fr_FR")
        field = self.env["ir.model.fields"].search(
            [("model_id.model", "=", "res.users"), ("name", "=", "login")]
        )
        field.update_field_translations("field_description", {"fr_FR": "Identifiant"})
        self.assertEqual(
            field.with_context(lang="fr_FR").field_description, "Identifiant"
        )
        admin = self.env["res.users"].search([("login", "=", "admin")], limit=1)
        admin.lang = "fr_FR"
        self.start_tour("/odoo", "ir_model_fields_translation_fr_tour", login="admin")
        field.update_field_translations("field_description", {"fr_FR": "Identifiant2"})
        self.start_tour("/odoo", "ir_model_fields_translation_fr_tour2", login="admin")


@tagged("-at_install", "post_install")
class TestIrModelFields(TransactionCase):
    def _make_manual_field(self, stem, **vals):
        model = self.env["ir.model"].create(
            {"model": f"x_imf_{stem}", "name": f"IMF test {stem}"}
        )
        field = self.env["ir.model.fields"].create(
            {
                "name": f"x_{stem}",
                "field_description": f"Field {stem}",
                "model_id": model.id,
                "ttype": "char",
                **vals,
            }
        )
        return self.env[model.model], field

    def test_a_stored_compute_added_to_a_table_with_rows_is_computed_for_them(self):
        Model, _field = self._make_manual_field("newcol", ttype="integer")
        rows = Model.create([{"x_newcol": 2}, {"x_newcol": 5}])
        rows.flush_recordset()
        self.env["ir.model.fields"].create(
            {
                "name": "x_double",
                "field_description": "Double",
                "model_id": self.env["ir.model"]._get(Model._name).id,
                "ttype": "integer",
                "store": True,
                "depends": "x_newcol",
                "compute": "for r in self:\n    r['x_double'] = r['x_newcol'] * 2",
            }
        )
        self.env.flush_all()
        self.assertEqual(
            self.env[Model._name].browse(rows.ids).mapped("x_double"), [4, 10]
        )

    def test_empty_write_skips_registry_setup(self):
        _model, field = self._make_manual_field("empty")
        with patch.object(self.env.registry, "setup_models") as mock_setup:
            self.assertTrue(field.write({}))
        mock_setup.assert_not_called()

    def test_label_translate_write_skips_registry_setup(self):
        Model, field = self._make_manual_field("label")
        with patch.object(self.env.registry, "setup_models") as mock_setup:
            field.write({"field_description": "Renamed Label"})
        mock_setup.assert_not_called()
        self.assertEqual(
            self.env["ir.model.fields"].get_field_string(Model._name)[field.name],
            "Renamed Label",
        )

    def test_field_rename_preserves_column_index_and_data(self):
        Model, field = self._make_manual_field("rename", index=True)
        table = Model._table
        record = Model.create({"x_rename": "kept"})
        record.flush_recordset()

        field.write({"name": "x_renamed"})

        self.env.cr.execute(
            "SELECT column_name FROM information_schema.columns"
            " WHERE table_name = %s AND column_name IN ('x_rename', 'x_renamed')",
            (table,),
        )
        self.assertEqual(
            [row[0] for row in self.env.cr.fetchall()],
            ["x_renamed"],
            "only the renamed column must remain",
        )
        self.env.cr.execute(
            "SELECT indexname FROM pg_indexes WHERE tablename = %s", (table,)
        )
        indexes = {row[0] for row in self.env.cr.fetchall()}
        self.assertIn(f"{table}__x_renamed_index", indexes)
        self.assertNotIn(f"{table}__x_rename_index", indexes)
        record = self.env[Model._name].browse(record.id)
        self.assertEqual(record.x_renamed, "kept")

    def test_field_rename_single_prepare_update_pass(self):
        _Model, field = self._make_manual_field("renonce")
        cls = type(self.env["ir.model.fields"])
        original = cls._prepare_update
        calls = []

        def counting(records, **kwargs):
            calls.append(records)
            return original(records, **kwargs)

        with patch.object(cls, "_prepare_update", counting):
            field.write({"name": "x_renonce2"})
        self.assertEqual(len(calls), 1)

    def test_field_rename_sets_up_the_registry_once(self):
        _Model, field = self._make_manual_field("setuponce")
        self.env.flush_all()
        original = type(self.env.registry).setup_models
        calls = []

        def spy(registry, cr, model_names=None, **kwargs):
            calls.append(model_names)
            return original(registry, cr, model_names, **kwargs)

        with patch.object(type(self.env.registry), "setup_models", spy):
            field.write({"name": "x_setuponce2"})
        self.assertEqual(len(calls), 1, calls)

    def test_rename_blocked_by_a_view_restores_the_registry(self):
        Model, field = self._make_manual_field("viewkept")
        self.env["ir.ui.view"].create(
            {
                "name": "viewkept form",
                "model": Model._name,
                "arch": f'<form><field name="{field.name}"/></form>',
            }
        )
        with self.assertRaises(UserError):
            field.write({"name": "x_viewkept2"})
        self.assertIn(field.name, self.env.registry[Model._name]._fields)

    def _make_binary_record(self, stem):
        model = self.env["ir.model"].create(
            {"model": f"x_imf_{stem}", "name": f"IMF binary {stem}"}
        )
        field = self.env["ir.model.fields"].create(
            {
                "name": f"x_{stem}",
                "field_description": f"Binary {stem}",
                "model_id": model.id,
                "ttype": "binary",
            }
        )
        Model = self.env[model.model]
        record = Model.create({field.name: b"aGVsbG8="})
        record.flush_recordset()
        attachments = (
            self.env["ir.attachment"]
            .sudo()
            .search([("res_model", "=", Model._name), ("res_field", "=", field.name)])
        )
        self.assertEqual(len(attachments), 1)
        return Model, field, record, attachments

    def test_binary_field_rename_carries_its_attachments(self):
        Model, field, record, attachments = self._make_binary_record("binren")

        field.write({"name": "x_binren2"})

        self.assertEqual(attachments.mapped("res_field"), ["x_binren2"])
        record = self.env[Model._name].browse(record.id)
        self.assertEqual(record.x_binren2, b"aGVsbG8=")

    def test_binary_field_unlink_removes_its_attachments(self):
        _Model, field, _record, attachments = self._make_binary_record("bindel")
        field.unlink()
        self.assertFalse(attachments.exists())

    def test_binary_field_unlink_at_uninstall_keeps_its_attachments(self):
        _Model, field, _record, attachments = self._make_binary_record("binkeep")
        field.with_context(**{MODULE_UNINSTALL_FLAG: True}).unlink()
        self.assertTrue(attachments.exists())

    def test_help_on_a_base_field_skips_registry_setup(self):
        field = self.env["ir.model.fields"]._get("res.partner", "comment")
        self.assertFalse(field.help)
        with patch.object(self.env.registry, "setup_models") as mock_setup:
            field.write({"help": "Tooltip"})
        mock_setup.assert_not_called()

    def test_boolean_translate_rejected(self):
        model = self.env["ir.model"].create(
            {"model": "x_imf_transl", "name": "IMF translate test"}
        )
        with self.assertRaises(ValidationError):
            self.env["ir.model.fields"].create(
                {
                    "name": "x_transl",
                    "field_description": "Translated",
                    "model_id": model.id,
                    "ttype": "char",
                    "translate": True,
                }
            )
        _Model, field = self._make_manual_field("translw")
        with self.assertRaises(ValidationError):
            field.write({"translate": True})

    def test_check_depends_raises_validation_error(self):
        model = self.env["ir.model"].create(
            {"model": "x_imf_deps", "name": "IMF depends test"}
        )
        with self.assertRaises(ValidationError):
            self.env["ir.model.fields"].create(
                {
                    "name": "x_dep",
                    "field_description": "Dep",
                    "model_id": model.id,
                    "ttype": "char",
                    "store": False,
                    "compute": "pass",
                    "depends": "no_such_field",
                }
            )

    def test_check_related_raises_validation_error(self):
        model = self.env["ir.model"].create(
            {"model": "x_imf_rel", "name": "IMF related test"}
        )
        with self.assertRaises(ValidationError):
            self.env["ir.model.fields"].create(
                {
                    "name": "x_rel",
                    "field_description": "Rel",
                    "model_id": model.id,
                    "ttype": "char",
                    "related": "no_such_field",
                }
            )

    def test_all_manual_field_data_immutable(self):
        self._make_manual_field("frozen")
        data = self.env["ir.model.fields"]._get_manual_field_data_by_model()
        self.assertIn("x_imf_frozen", data)
        with self.assertRaises((TypeError, NotImplementedError)):
            data["x_bogus"] = {}

    def test_compute_modules_shared_helper(self):
        model = self.env["ir.model"]._get("res.partner")
        self.assertIn("base", model.modules.split(", "))
        field = self.env["ir.model.fields"]._get("res.partner", "name")
        self.assertIn("base", field.modules.split(", "))

    def test_display_name_batch_fetches_model_names(self):
        fields_ = self.env["ir.model.fields"].search(
            [("model", "=", "res.partner"), ("name", "in", ["name", "email"])]
        )
        self.env.invalidate_all()
        names = fields_.mapped("display_name")
        model_name = self.env["ir.model"]._get("res.partner").name
        for field, display_name in zip(fields_, names, strict=True):
            self.assertEqual(display_name, f"{field.field_description} ({model_name})")
        self.env.invalidate_all()
        fields_.mapped("display_name")
        with self.assertQueryCount(0):
            self.env["ir.model"]._get("res.partner").name

    def test_check_relation_table_invalid_name(self):
        model = self.env["ir.model"].create(
            {"model": "x_imf_m2m", "name": "IMF m2m test"}
        )
        comodel = self.env["ir.model"].search([("model", "=", "res.partner")])
        with self.assertRaises(ValidationError) as cm:
            self.env["ir.model.fields"].create(
                {
                    "name": "x_partner_ids",
                    "field_description": "Partners",
                    "model_id": model.id,
                    "ttype": "many2many",
                    "relation": comodel.model,
                    "relation_table": "bad-name!",
                }
            )
        self.assertIn("Relation table names", str(cm.exception))

    def test_help_added_by_translate_only_write_is_visible(self):
        Model, field = self._make_manual_field("addhelp")
        model_name = Model._name
        self.assertIsNone(Model._fields[field.name].help)

        field.write({"help": "Tooltip"})

        self.assertEqual(
            self.env[model_name].fields_get([field.name])[field.name]["help"],
            "Tooltip",
        )
        self.assertEqual(
            self.env.registry[model_name]._fields[field.name].help, "Tooltip"
        )

    def test_a_label_write_is_visible_to_an_environment_without_a_language(self):
        Model, field = self._make_manual_field("nolang")
        field.write({"field_description": "Relabelled"})
        no_lang = self.env(context={**self.env.context, "lang": False})
        self.assertEqual(
            no_lang[Model._name].fields_get([field.name])[field.name]["string"],
            "Relabelled",
        )

    def test_presence_preserving_label_write_still_skips_setup(self):
        Model, field = self._make_manual_field("keepfast", help="Tip")
        with patch.object(self.env.registry, "setup_models") as mock_setup:
            field.write({"field_description": "Renamed", "help": "Tip 2"})
        mock_setup.assert_not_called()
        self.assertEqual(
            self.env["ir.model.fields"].get_field_help(Model._name)[field.name],
            "Tip 2",
        )

    def test_field_groups_without_xmlid_are_enforceable(self):
        model = self.env["ir.model"].create(
            {"model": "x_imf_sec", "name": "IMF security test"}
        )
        group = self.env["res.groups"].create({"name": "IMF ad-hoc group"})
        self.assertFalse(group.get_external_id()[group.id])

        field = self.env["ir.model.fields"].create(
            {
                "name": "x_secret",
                "field_description": "Secret",
                "model_id": model.id,
                "ttype": "char",
                "groups": [Command.set([group.id])],
            }
        )
        self.env["ir.model.access"].create(
            {
                "name": "imf sec acl",
                "model_id": model.id,
                "group_id": self.env.ref("base.group_user").id,
                "perm_read": True,
                "perm_write": True,
                "perm_create": True,
                "perm_unlink": True,
            }
        )
        self.env.flush_all()
        self.env.registry.setup_models(self.env.cr, [model.model])

        self.assertTrue(group.get_external_id()[group.id])
        self.assertEqual(
            self.env.registry[model.model]._fields[field.name].groups,
            group.get_external_id()[group.id],
        )

        record = self.env[model.model].create({"x_secret": "classified"})
        self.env.flush_all()
        outsider = new_test_user(self.env, login="imf_outsider")
        with self.assertRaises(AccessError):
            self.env[model.model].with_user(outsider).browse(record.id).read(
                ["x_secret"]
            )
        outsider.write({"group_ids": [Command.link(group.id)]})
        self.assertEqual(
            self.env[model.model].with_user(outsider).browse(record.id).x_secret,
            "classified",
        )

    @mute_logger("odoo.addons.base.models.ir_model_fields")
    def test_field_groups_missing_xmlid_fails_closed(self):
        model = self.env["ir.model"].create(
            {"model": "x_imf_sec2", "name": "IMF security test 2"}
        )
        group = self.env["res.groups"].create({"name": "IMF legacy group"})
        field = self.env["ir.model.fields"].create(
            {
                "name": "x_secret",
                "field_description": "Secret",
                "model_id": model.id,
                "ttype": "char",
                "groups": [Command.set([group.id])],
            }
        )
        self.env.flush_all()
        self.env["ir.model.data"].search(
            [("model", "=", "res.groups"), ("res_id", "=", group.id)]
        ).unlink()
        self.env.registry.clear_cache("stable")
        self.env.registry.setup_models(self.env.cr, [model.model])

        self.assertEqual(
            self.env.registry[model.model]._fields[field.name].groups,
            NO_ACCESS,
            "an unreflectable restriction must fail closed",
        )

    def test_write_does_not_mutate_caller_vals(self):
        model = self.env["ir.model"].create(
            {"model": "x_imf_vals", "name": "IMF vals test"}
        )
        field = self.env["ir.model.fields"].create(
            {
                "name": "x_v",
                "field_description": "V",
                "model_id": model.id,
                "ttype": "char",
            }
        )
        vals = {"field_description": "V2", "model_id": model.id, "state": "manual"}
        expected = dict(vals)
        field.write(vals)
        self.assertEqual(vals, expected)

        model_vals = {"name": "IMF vals test 2", "field_id": [(4, field.id, False)]}
        expected_model_vals = dict(model_vals)
        model.write(model_vals)
        self.assertEqual(model_vals, expected_model_vals)

    def test_unrelated_broken_view_does_not_block_field_deletion(self):
        _Model, field = self._make_manual_field("ab_cd")
        bait = self.env["ir.ui.view"].create(
            {
                "name": "IMF wildcard bait",
                "model": "res.partner",
                "type": "form",
                "arch": '<form><field name="name"/></form>',
            }
        )
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE ir_ui_view SET arch_db = %s WHERE id = %s",
            (Json({"en_US": '<form><field name="xZabZcd_nope"/></form>'}), bait.id),
        )
        self.env.invalidate_all()

        self.assertTrue(
            self.env["ir.ui.view"].search_count(
                [("id", "=", bait.id), ("arch_db", "like", field.name)]
            ),
            "precondition: the raw pattern matches the bait",
        )
        self.assertFalse(
            self.env["ir.ui.view"].search_count(
                [("id", "=", bait.id), ("arch_db", "like", escape_psql(field.name))]
            ),
            "precondition: the escaped pattern does not",
        )
        with self.assertRaises(ValidationError):
            bait._check_xml()

        field.unlink()

    def test_related_view_still_blocks_field_deletion(self):
        Model, field = self._make_manual_field("guard")
        self.env["ir.ui.view"].create(
            {
                "name": "IMF real reference",
                "model": Model._name,
                "type": "form",
                "arch": f'<form><field name="{field.name}"/></form>',
            }
        )
        self.env.flush_all()
        with self.assertRaises(UserError):
            field.unlink()

    def test_view_scan_ignores_substring_and_wildcard_matches(self):
        model = self.env["ir.model"].create({"model": "x_imf_scan", "name": "IMF scan"})
        for name in ("x_ab", "x_ab_long", "x_ab_cd"):
            self.env["ir.model.fields"].create(
                {
                    "name": name,
                    "field_description": name,
                    "model_id": model.id,
                    "ttype": "char",
                }
            )
        self.env.flush_all()
        self.env.registry.setup_models(self.env.cr, [model.model])
        long_view = self.env["ir.ui.view"].create(
            {
                "name": "IMF scan long",
                "model": model.model,
                "type": "form",
                "arch": '<form><field name="x_ab_long"/></form>',
            }
        )
        wildcard_bait = self.env["ir.ui.view"].create(
            {
                "name": "IMF scan bait",
                "model": "res.partner",
                "type": "form",
                "arch": '<form><field name="name" string="xZabZcd"/></form>',
            }
        )
        self.env.flush_all()

        IrModelFields = self.env["ir.model.fields"]
        self.assertNotIn(
            long_view.id, IrModelFields._get_views_mentioning(["x_ab"]).ids
        )
        self.assertIn(
            long_view.id, IrModelFields._get_views_mentioning(["x_ab_long"]).ids
        )
        self.assertNotIn(
            wildcard_bait.id, IrModelFields._get_views_mentioning(["x_ab_cd"]).ids
        )

    def test_view_scan_finds_translation_only_occurrences(self):
        model = self.env["ir.model"].create(
            {"model": "x_imf_scanfr", "name": "IMF scan fr"}
        )
        self.env["ir.model.fields"].create(
            {
                "name": "x_only_fr",
                "field_description": "Fr",
                "model_id": model.id,
                "ttype": "char",
            }
        )
        view = self.env["ir.ui.view"].create(
            {
                "name": "IMF scan fr view",
                "model": "res.partner",
                "type": "form",
                "arch": '<form><field name="name"/></form>',
            }
        )
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE ir_ui_view SET arch_db = %s WHERE id = %s",
            (
                Json(
                    {
                        "en_US": '<form><field name="name"/></form>',
                        "fr_FR": '<form><field name="x_only_fr"/></form>',
                    }
                ),
                view.id,
            ),
        )
        self.env.invalidate_all()

        self.assertIn(
            view.id,
            self.env["ir.model.fields"]._get_views_mentioning(["x_only_fr"]).ids,
        )

    def test_drop_column_recovers_m2m_table_name(self):
        model = self.env["ir.model"].create(
            {"model": "x_imf_m2mdrop", "name": "IMF m2m drop"}
        )
        field = self.env["ir.model.fields"].create(
            {
                "name": "x_rel",
                "field_description": "Rel",
                "model_id": model.id,
                "ttype": "many2many",
                "relation": "res.partner",
            }
        )
        self.env.flush_all()
        table = field.relation_table
        self.assertTrue(table)
        self.env.cr.execute(
            "UPDATE ir_model_fields SET relation_table = NULL WHERE id = %s",
            (field.id,),
        )
        self.env.invalidate_all()
        pop_field(self.env.registry["x_imf_m2mdrop"], "x_rel")

        field._drop_columns()

        self.env.cr.execute("SELECT to_regclass(%s)", (table,))
        self.assertIsNone(self.env.cr.fetchone()[0], "m2m table must not leak")

    def test_selection_of_a_new_record_does_not_hit_the_database(self):
        model = self.env["ir.model"].create(
            {"model": "x_imf_newsel", "name": "IMF new selection"}
        )
        record = self.env["ir.model.fields"].new(
            {
                "name": "x_sel",
                "field_description": "Sel",
                "model_id": model.id,
                "ttype": "selection",
                "selection_ids": [
                    Command.create({"value": "a", "name": "A", "sequence": 1}),
                    Command.create({"value": "b", "name": "B", "sequence": 2}),
                ],
            }
        )
        self.assertEqual(record.selection, str([("a", "A"), ("b", "B")]))

    def test_selection_is_computed_without_one_query_per_field(self):
        fields_ = self.env["ir.model.fields"].search(
            [("ttype", "in", ("selection", "reference"))], limit=20
        )
        self.assertGreater(len(fields_), 4)
        self.env.flush_all()
        self.env.invalidate_all()
        count = [0]
        original = self.env.cr.execute

        def spy(query, params=None, **kwargs):
            count[0] += 1
            return original(query, params, **kwargs)

        self.env.cr.execute = spy
        try:
            fields_.mapped("selection")
        finally:
            self.env.cr.execute = original
        self.assertLess(
            count[0],
            len(fields_),
            "the selection compute must batch, not query once per field",
        )

    def test_relational_field_without_comodel_is_rejected(self):
        model = self.env["ir.model"].create(
            {"model": "x_imf_norel", "name": "IMF no relation"}
        )
        for ttype in ("many2one", "one2many", "many2many"):
            with self.subTest(ttype=ttype), self.assertRaises(ValidationError):
                self.env["ir.model.fields"].create(
                    {
                        "name": f"x_{ttype}",
                        "field_description": ttype,
                        "model_id": model.id,
                        "ttype": ttype,
                    }
                )

    def test_stored_one2many_without_inverse_is_rejected(self):
        model = self.env["ir.model"].create(
            {"model": "x_imf_noinv", "name": "IMF no inverse"}
        )
        with self.assertRaises(ValidationError):
            self.env["ir.model.fields"].create(
                {
                    "name": "x_children",
                    "field_description": "Children",
                    "model_id": model.id,
                    "ttype": "one2many",
                    "relation": "res.partner",
                }
            )

    def test_stored_related_one2many_is_rejected_and_unstored_is_not(self):
        model = self.env["ir.model"].create(
            {"model": "x_imf_relo2m", "name": "IMF related o2m"}
        )
        self.env["ir.model.fields"].create(
            {
                "name": "x_partner_id",
                "field_description": "Partner",
                "model_id": model.id,
                "ttype": "many2one",
                "relation": "res.partner",
            }
        )
        vals = {
            "name": "x_child_ids",
            "field_description": "Children",
            "model_id": model.id,
            "ttype": "one2many",
            "relation": "res.partner",
            "related": "x_partner_id.child_ids",
        }
        with self.assertRaises(ValidationError):
            self.env["ir.model.fields"].create(dict(vals))
        field = self.env["ir.model.fields"].create(dict(vals, store=False))
        self.assertIn(field.name, self.env[model.model]._fields)

    def test_check_depends_on_a_model_outside_the_registry(self):
        _Model, field = self._make_manual_field("depsmodel")
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE ir_model_fields SET model = %s, depends = %s WHERE id = %s",
            ("no.such.model", "name", field.id),
        )
        self.env.invalidate_all()
        with self.assertRaises(ValidationError):
            field._check_depends()

    def test_write_rejects_an_unknown_field_name(self):
        _Model, field = self._make_manual_field("badkey")
        with self.assertRaises(ValueError):
            field.write({"no_such_field": 1})

    def test_write_rejects_a_model_change_spelled_as_model(self):
        _Model, field = self._make_manual_field("modelkey")
        with self.assertRaises(UserError):
            field.write({"model": "res.partner"})

    def test_drop_columns_groups_one_alter_per_table(self):
        model = self.env["ir.model"].create(
            {"model": "x_imf_dropmany", "name": "IMF drop many"}
        )
        fields_ = self.env["ir.model.fields"].create(
            [
                {
                    "name": f"x_col{i}",
                    "field_description": f"Col {i}",
                    "model_id": model.id,
                    "ttype": "char",
                }
                for i in range(5)
            ]
        )
        self.env.flush_all()
        table = self.env[model.model]._table
        statements = []
        original = self.env.cr.execute

        def spy(query, params=None, **kwargs):
            statements.append(str(query))
            return original(query, params, **kwargs)

        self.env.cr.execute = spy
        try:
            fields_._drop_columns()
        finally:
            self.env.cr.execute = original

        alters = [q for q in statements if "DROP COLUMN" in q]
        self.assertEqual(len(alters), 1, "one ALTER TABLE for one table")
        self.assertEqual(alters[0].count("DROP COLUMN"), 5)
        self.env.cr.execute(
            "SELECT column_name FROM information_schema.columns"
            " WHERE table_name = %s AND column_name LIKE 'x\\_col%%'",
            (table,),
        )
        self.assertFalse(self.env.cr.fetchall())

    def test_prepare_update_does_not_rebuild_the_whole_registry(self):
        _Model, field = self._make_manual_field("scoped")
        self.env.flush_all()
        scopes = []
        original = type(self.env.registry).setup_models

        def spy(registry, cr, model_names=None, **kwargs):
            scopes.append(model_names)
            return original(registry, cr, model_names, **kwargs)

        with patch.object(type(self.env.registry), "setup_models", spy):
            field.unlink()

        self.assertTrue(scopes)
        self.assertNotIn(
            None, scopes, "a field deletion must not re-set-up every model"
        )

    def test_group_with_two_xmlids_is_not_reported_as_unreflectable(self):
        model = self.env["ir.model"].create(
            {"model": "x_imf_twoxid", "name": "IMF two xmlids"}
        )
        group = self.env["res.groups"].create({"name": "IMF twice-named group"})
        field = self.env["ir.model.fields"].create(
            {
                "name": "x_secret",
                "field_description": "Secret",
                "model_id": model.id,
                "ttype": "char",
                "groups": [Command.set([group.id])],
            }
        )
        self.env.flush_all()
        self.env["ir.model.data"].create(
            {
                "module": "base",
                "name": "imf_alias_for_twice_named_group",
                "model": "res.groups",
                "res_id": group.id,
            }
        )
        self.env.flush_all()
        self.env.registry.clear_cache("stable")
        data = self.env["ir.model.fields"]._get_manual_field_data(model.model)
        field_data = data[field.name]
        self.assertEqual(field_data["group_count"], 1)
        self.assertEqual(field_data["group_known"], 1)
        self.assertEqual(field_data["group_xmlids"].count(","), 0)

    def test_rename_carries_the_derived_xml_id_and_leaves_others_alone(self):
        model = self.env["ir.model"].create({"model": "x_imf_xid", "name": "IMF xmlid"})
        field = self.env["ir.model.fields"].create(
            {
                "name": "x_old",
                "field_description": "Old",
                "model_id": model.id,
                "ttype": "char",
            }
        )
        Data = self.env["ir.model.data"]
        Data.create(
            {
                "module": "base",
                "name": "field_x_imf_xid__x_old",
                "model": "ir.model.fields",
                "res_id": field.id,
            }
        )
        Data.create(
            {
                "module": "base",
                "name": "imf_handwritten_alias",
                "model": "ir.model.fields",
                "res_id": field.id,
            }
        )
        self.env.flush_all()

        field.write({"name": "x_new"})
        self.env.flush_all()

        names = Data.search(
            [("model", "=", "ir.model.fields"), ("res_id", "=", field.id)]
        ).mapped("name")
        self.assertEqual(
            sorted(names),
            ["field_x_imf_xid__x_new", "imf_handwritten_alias"],
            "the derived xml id follows the rename; a hand-written one does not",
        )

    def test_dependencies_without_a_compute_are_rejected(self):
        model = self.env["ir.model"].create(
            {"model": "x_imf_deadep", "name": "IMF dead depends"}
        )
        self.env["ir.model.fields"].create(
            {
                "name": "x_src",
                "field_description": "Source",
                "model_id": model.id,
                "ttype": "char",
            }
        )
        with self.assertRaises(ValidationError):
            self.env["ir.model.fields"].create(
                {
                    "name": "x_dead",
                    "field_description": "Dead",
                    "model_id": model.id,
                    "ttype": "char",
                    "depends": "x_src",
                }
            )
        field = self.env["ir.model.fields"].create(
            {
                "name": "x_live",
                "field_description": "Live",
                "model_id": model.id,
                "ttype": "char",
                "store": False,
                "depends": "x_src",
                "compute": "for record in self: record['x_live'] = record.x_src",
            }
        )
        self.assertIn(field.name, self.env[model.model]._fields)

    def test_field_readiness_is_asked_separately_from_the_attributes(self):
        IrModelFields = self.env["ir.model.fields"]
        model = self.env["ir.model"].create(
            {"model": "x_imf_ready", "name": "IMF ready"}
        )
        field = IrModelFields.create(
            {
                "name": "x_tags",
                "field_description": "Tags",
                "model_id": model.id,
                "ttype": "many2many",
                "relation": "res.partner",
            }
        )
        self.env.flush_all()
        self.env.registry.clear_cache("stable")
        data = IrModelFields._get_manual_field_data(model.model)[field.name]

        self.assertTrue(IrModelFields._is_field_ready(data))
        attrs = IrModelFields._prepare_field_attrs(data)
        self.assertIsInstance(attrs, dict, "attributes no longer carry the sentinel")
        self.assertEqual(attrs["comodel_name"], "res.partner")

        absent = dict(data, relation="x_not_a_model")
        with patch.object(self.env.registry, "loaded", False):
            self.assertFalse(IrModelFields._is_field_ready(absent))
            self.assertTrue(IrModelFields._is_field_ready(data))

    def test_manual_field_data_rows_are_frozen_and_plain(self):
        model = self.env["ir.model"].create({"model": "x_imf_rows", "name": "IMF rows"})
        self.env["ir.model.fields"].create(
            {
                "name": "x_c",
                "field_description": "Label",
                "model_id": model.id,
                "ttype": "char",
                "help": "Helptext",
            }
        )
        self.env.flush_all()
        self.env.registry.clear_cache("stable")
        row = self.env["ir.model.fields"]._get_manual_field_data(model.model)["x_c"]
        self.assertEqual(row["field_description"], "Label")
        self.assertEqual(row["help"], "Helptext")
        self.assertFalse([key for key in row if key.endswith("_en")])
        with self.assertRaises(NotImplementedError):
            row["field_description"] = "mutated"

    def test_rename_without_registry_model_raises_user_error(self):
        _Model, field = self._make_manual_field("noreg")
        model_cls = self.env.registry.models.pop("x_imf_noreg")
        try:
            with self.assertRaises(UserError):
                field.write({"name": "x_noreg2"})
        finally:
            self.env.registry.models["x_imf_noreg"] = model_cls


class TestIrModelInherit(TransactionCase):
    def test_inherit(self):
        imi = self.env["ir.model.inherit"].search(
            [
                ("model_id.model", "=", "ir.actions.server"),
                ("parent_id.model", "=", "ir.actions.actions"),
            ]
        )
        self.assertEqual(len(imi), 1)
        self.assertEqual(imi.parent_id.model, "ir.actions.actions")
        self.assertFalse(imi.parent_field_id)

    def test_inherits(self):
        imi = self.env["ir.model.inherit"].search(
            [
                ("model_id.model", "=", "res.users"),
                ("parent_field_id", "!=", False),
            ]
        )
        self.assertEqual(len(imi), 1)
        self.assertEqual(imi.parent_id.model, "res.partner")
        self.assertEqual(imi.parent_field_id.name, "partner_id")

    def test_prepare_inherit_mapping_prewarms_ids_and_asks_field_ids_only_for_inherits(
        self,
    ):
        IrModelInherit = self.env["ir.model.inherit"]
        cls = type(self.env["ir.model.fields"])
        original = cls._get_ids_by_name
        asked = []

        def spy(records, model_name):
            asked.append(model_name)
            return original(records, model_name)

        self.env.flush_all()
        self.env.registry.clear_cache("stable")
        count0 = self.env.cr.sql_statement_count
        with patch.object(cls, "_get_ids_by_name", spy):
            mapping = IrModelInherit._prepare_inherit_mapping(
                ["res.partner", "res.users", "res.country"]
            )
        self.assertEqual(asked, ["res.users"])
        self.assertEqual(self.env.cr.sql_statement_count - count0, 2)
        self.assertTrue(mapping)

    def test_inherit_and_inherits_same_parent_is_rejected_clearly(self):
        IrModelInherit = self.env["ir.model.inherit"]
        definition = next(
            cls
            for cls in type(self.env["res.users"]).mro()
            if is_model_definition(cls) and "res.partner" in cls._inherits
        )

        with (
            patch.object(definition, "_inherit", ["res.partner"]),
            self.assertRaises(ValueError) as cm,
        ):
            IrModelInherit._reflect_inherits(["res.users"])
        self.assertIn("res.users", str(cm.exception))
        self.assertIn("res.partner", str(cm.exception))


class TestIrModelReflectionIdempotence(TransactionCase):
    MODELS = ["res.partner", "res.users", "res.country", "ir.model.fields"]

    def _reflect(self):
        env = self.env
        env["ir.model"]._reflect_models(self.MODELS)
        env["ir.model.fields"]._reflect_fields(self.MODELS)
        env["ir.model.fields.selection"]._reflect_selections(self.MODELS)

    def test_second_reflection_writes_nothing(self):
        with patch.object(type(self.env.registry), "post_init", lambda *args: None):
            self._reflect()
        tz_id = self.env["ir.model.fields"]._get("res.partner", "tz").id
        upserts = []

        def spy(records, cols, rows, conflict):
            upserts.append((records._name, cols, rows))
            return upsert_en(records, cols, rows, conflict)

        with (
            patch.object(type(self.env.registry), "post_init", lambda *args: None),
            patch.object(ir_model, "upsert_en", spy),
            patch.object(ir_model_fields, "upsert_en", spy),
            patch.object(ir_model_fields_selection, "upsert_en", spy),
        ):
            self._reflect()

        unexpected = [
            (name, cols, [row for row in rows if row[0] != tz_id])
            for name, cols, rows in upserts
            if name != "ir.model.fields.selection"
            or any(row[0] != tz_id for row in rows)
        ]
        self.assertEqual(unexpected, [])


class TestIrModelRelationReflection(TransactionCase):
    def test_model_table_reflection_is_removed_without_dropping_payload(self):
        relations = self.env["ir.model.relation"]
        partner = self.env["res.partner"].create({"name": "Preserved payload"})
        table = partner._table
        for items in ([], [("res.partner", table, "base")]):
            with self.subTest(items=items):
                legacy = relations.create(
                    {
                        "name": table,
                        "model": self.env["ir.model"]._get_id("res.partner"),
                        "module": self.env.ref("base.module_base").id,
                    }
                )
                relations._reflect_relations(items, model_tables={table})
                self.assertFalse(legacy.exists())
                self.assertFalse(relations.search([("name", "=", table)]))
                partner.invalidate_recordset(["name"])
                self.assertEqual(partner.name, "Preserved payload")

    def test_reflect_relations_is_idempotent_and_batched(self):
        IrModelRelation = self.env["ir.model.relation"]
        model_name = "res.partner"
        table = "x_imr_probe_rel"
        self.env.cr.execute("DELETE FROM ir_model_relation WHERE name = %s", (table,))

        IrModelRelation._reflect_relations(
            [(model_name, table, "base"), (model_name, table, "base")]
        )
        self.env.cr.execute(
            "SELECT im.model, m.name FROM ir_model_relation r"
            " JOIN ir_model im ON r.model = im.id"
            " JOIN ir_module_module m ON r.module = m.id"
            " WHERE r.name = %s",
            (table,),
        )
        self.assertEqual(self.env.cr.fetchall(), [(model_name, "base")])

        IrModelRelation._reflect_relations([(model_name, table, "base")])
        self.env.cr.execute(
            "SELECT count(*) FROM ir_model_relation WHERE name = %s", (table,)
        )
        self.assertEqual(self.env.cr.fetchone()[0], 1, "no duplicate row")

    def test_reflect_relations_skips_unknown_module(self):
        with mute_logger("odoo.addons.base.models.ir_model_reflection"):
            self.env["ir.model.relation"]._reflect_relations(
                [("res.partner", "x_imr_nomodule_rel", "no_such_module_xyz")]
            )
        self.env.cr.execute(
            "SELECT count(*) FROM ir_model_relation WHERE name = %s",
            ("x_imr_nomodule_rel",),
        )
        self.assertEqual(self.env.cr.fetchone()[0], 0)


@tagged("-at_install", "post_install")
class TestIrModelFieldsSelection(TransactionCase):
    @contextmanager
    def _write_raises(self, model_name, field_name, error):
        original_write = BaseModel.write

        def guarded_write(records, vals):
            if records._name == model_name and field_name in vals:
                raise error
            return original_write(records, vals)

        with patch.object(BaseModel, "write", guarded_write):
            yield

    def _make_selection_field(
        self, stem, *, company_dependent=False, values=None, ttype="selection"
    ):
        values = values or [("draft", "Draft"), ("done", "Done")]
        model = self.env["ir.model"].create(
            {"model": f"x_sel_{stem}", "name": f"Selection test {stem}"}
        )
        field = self.env["ir.model.fields"].create(
            {
                "name": f"x_{stem}",
                "field_description": f"Sel {stem}",
                "model_id": model.id,
                "ttype": ttype,
                "company_dependent": company_dependent,
                "selection_ids": [
                    Command.create({"value": value, "name": label, "sequence": index})
                    for index, (value, label) in enumerate(values)
                ],
            }
        )
        return self.env[model.model], field

    def _set_jsonb(self, model, field, record, mapping):
        self.env.backend.columns.write(
            record,
            field.name,
            [(record.id, Json({str(cid): value for cid, value in mapping.items()}))],
        )
        record.invalidate_recordset([field.name])

    def _read_jsonb(self, model, field, record):
        self.env.cr.execute(
            SQL(
                "SELECT %s FROM %s WHERE id = %s",
                SQL.identifier(field.name),
                SQL.identifier(model._table),
                record.id,
            )
        )
        return self.env.cr.fetchone()[0]

    def test_selection_value_rename_normal(self):
        Model, field = self._make_selection_field("plain")
        record = Model.create({"x_plain": "draft"})
        record.flush_recordset()

        field.selection_ids.filtered(lambda s: s.value == "draft").write(
            {"value": "pending"}
        )

        record.invalidate_recordset(["x_plain"])
        self.assertEqual(record.x_plain, "pending")

    def test_selection_value_rename_company_dependent(self):
        company_a = self.env.company
        company_b = self.env["res.company"].create({"name": "SEL Co B"})
        Model, field = self._make_selection_field("cdep", company_dependent=True)
        record = Model.create({})
        record.flush_recordset()
        self._set_jsonb(
            Model, field, record, {company_a.id: "draft", company_b.id: "draft"}
        )

        field.selection_ids.filtered(lambda s: s.value == "draft").write(
            {"value": "pending"}
        )

        self.assertEqual(
            self._read_jsonb(Model, field, record),
            {str(company_a.id): "pending", str(company_b.id): "pending"},
        )

    def test_selection_value_rename_company_dependent_other_value_untouched(self):
        company_a = self.env.company
        company_b = self.env["res.company"].create({"name": "SEL Co C"})
        Model, field = self._make_selection_field("keep", company_dependent=True)
        record = Model.create({})
        record.flush_recordset()
        self._set_jsonb(
            Model, field, record, {company_a.id: "draft", company_b.id: "done"}
        )

        field.selection_ids.filtered(lambda s: s.value == "draft").write(
            {"value": "pending"}
        )

        self.assertEqual(
            self._read_jsonb(Model, field, record),
            {str(company_a.id): "pending", str(company_b.id): "done"},
        )

    def test_selection_value_rename_same_value_batch_rejected(self):
        _model, field = self._make_selection_field("batch")
        self.assertEqual(len(field.selection_ids), 2)
        with self.assertRaises(UserError):
            field.selection_ids.write({"value": "merged"})

    def test_selection_label_rename_skips_registry_setup(self):
        Model, field = self._make_selection_field("label")
        draft = field.selection_ids.filtered(lambda s: s.value == "draft")
        with patch.object(self.env.registry, "setup_models") as mock_setup:
            draft.write({"name": "Brouillon"})
        mock_setup.assert_not_called()
        self.assertIn(
            ("draft", "Brouillon"),
            self.env["ir.model.fields"].get_field_selection(Model._name, field.name),
        )

    def test_selection_value_rename_triggers_registry_setup(self):
        _model, field = self._make_selection_field("setup")
        draft = field.selection_ids.filtered(lambda s: s.value == "draft")
        with patch.object(self.env.registry, "setup_models") as mock_setup:
            draft.write({"value": "pending"})
        mock_setup.assert_called()

    def test_selection_ondelete_bypass_on_recoverable_error(self):
        Model, field = self._make_selection_field("ondok")
        record = Model.create({"x_ondok": "draft"})
        record.flush_recordset()
        draft = field.selection_ids.filtered(lambda s: s.value == "draft")

        refusal = ValidationError("ondelete write refused by a constraint")
        with self._write_raises(Model._name, "x_ondok", refusal):
            draft.unlink()

        record.invalidate_recordset(["x_ondok"])
        self.assertFalse(record.x_ondok)

    def test_selection_ondelete_propagates_programming_error(self):
        Model, field = self._make_selection_field("ondbug")
        record = Model.create({"x_ondbug": "draft"})
        record.flush_recordset()
        draft = field.selection_ids.filtered(lambda s: s.value == "draft")

        bug = TypeError("programming error in an override")
        with self._write_raises(Model._name, "x_ondbug", bug):
            with self.assertRaises(TypeError):
                draft.unlink()

    def _field_obj(self, model, stem):
        return self.env[model._name]._fields[f"x_{stem}"]

    def test_ondelete_set_null(self):
        Model, field = self._make_selection_field("pnull")
        record = Model.create({"x_pnull": "draft"})
        record.flush_recordset()
        field.selection_ids.filtered(lambda s: s.value == "draft").unlink()
        record.invalidate_recordset(["x_pnull"])
        self.assertFalse(record.x_pnull)

    def _make_reference_field(self, stem, *, company_dependent=False):
        return self._make_selection_field(
            stem,
            company_dependent=company_dependent,
            values=[("res.partner", "Partner"), ("res.users", "User")],
            ttype="reference",
        )

    def _read_column(self, model, field, record):
        return self._read_jsonb(model, field, record)

    def test_option_unlink_discards_its_default(self):
        Model, field = self._make_selection_field("defdel")
        self.env["ir.default"].set(Model._name, field.name, "done")

        field.selection_ids.filtered(lambda s: s.value == "done").unlink()

        self.assertIsNone(self.env["ir.default"]._get(Model._name, field.name))
        self.assertFalse(Model.create({}).x_defdel)

    def test_option_value_rename_renames_its_default(self):
        Model, field = self._make_selection_field("defren")
        self.env["ir.default"].set(Model._name, field.name, "done")

        field.selection_ids.filtered(lambda s: s.value == "done").write(
            {"value": "finished"}
        )

        self.assertEqual(
            self.env["ir.default"]._get(Model._name, field.name), "finished"
        )
        self.assertEqual(self.env[Model._name].create({}).x_defren, "finished")

    def test_reference_option_value_rename_rewrites_stored_values(self):
        Model, field = self._make_reference_field("refren")
        partner = self.env["res.partner"].create({"name": "Ref"})
        record = Model.create({field.name: f"res.partner,{partner.id}"})
        record.flush_recordset()

        field.selection_ids.filtered(lambda s: s.value == "res.partner").write(
            {"value": "res.company"}
        )

        self.assertEqual(
            self._read_column(Model, field, record), f"res.company,{partner.id}"
        )
        record.invalidate_recordset([field.name])
        self.assertEqual(record[field.name]._name, "res.company")

    def test_reference_option_value_rename_company_dependent(self):
        company = self.env.company
        Model, field = self._make_reference_field("refrencd", company_dependent=True)
        record = Model.create({})
        record.flush_recordset()
        self._set_jsonb(
            Model, field, record, {company.id: "res.partner,7", 0: "res.users,7"}
        )

        field.selection_ids.filtered(lambda s: s.value == "res.partner").write(
            {"value": "res.company"}
        )

        self.assertEqual(
            self._read_jsonb(Model, field, record),
            {str(company.id): "res.company,7", "0": "res.users,7"},
        )

    def test_reference_option_unlink_nulls_stored_values(self):
        Model, field = self._make_reference_field("refdel")
        partner = self.env["res.partner"].create({"name": "Ref"})
        record = Model.create({field.name: f"res.partner,{partner.id}"})
        other = Model.create({field.name: f"res.users,{self.env.uid}"})
        (record + other).flush_recordset()

        field.selection_ids.filtered(lambda s: s.value == "res.partner").unlink()

        self.assertIsNone(self._read_column(Model, field, record))
        self.assertEqual(
            self._read_column(Model, field, other), f"res.users,{self.env.uid}"
        )

    def test_reference_option_unlink_company_dependent(self):
        company = self.env.company
        Model, field = self._make_reference_field("refdelcd", company_dependent=True)
        record = Model.create({})
        record.flush_recordset()
        self._set_jsonb(Model, field, record, {company.id: "res.partner,7"})

        field.selection_ids.filtered(lambda s: s.value == "res.partner").unlink()

        record.invalidate_recordset([field.name])
        self.assertFalse(record.with_company(company)[field.name])

    def test_base_field_option_cannot_be_renamed_even_by_admin(self):
        option = self.env["ir.model.fields.selection"].search(
            [
                ("field_id.model", "=", "res.partner"),
                ("field_id.name", "=", "type"),
                ("value", "=", "other"),
            ]
        )
        self.assertTrue(option)
        self.assertTrue(self.env.user._is_admin())
        with self.assertRaises(UserError):
            option.write({"value": "otherx"})
        with self.assertRaises(UserError):
            option.write({"sequence": 42})
        option.write({"name": "Other (relabelled)"})
        self.assertEqual(option.name, "Other (relabelled)")

    def test_ondelete_set_constant(self):
        Model, field = self._make_selection_field("pset")
        record = Model.create({"x_pset": "draft"})
        record.flush_recordset()
        with patch.object(
            self._field_obj(Model, "pset"), "ondelete", {"draft": "set done"}
        ):
            field.selection_ids.filtered(lambda s: s.value == "draft").unlink()
        record.invalidate_recordset(["x_pset"])
        self.assertEqual(record.x_pset, "done")

    def test_ondelete_set_default(self):
        Model, field = self._make_selection_field("pdef")
        record = Model.create({"x_pdef": "draft"})
        record.flush_recordset()
        field_obj = self._field_obj(Model, "pdef")
        with (
            patch.object(field_obj, "ondelete", {"draft": "set default"}),
            patch.object(field_obj, "default", lambda model: "done"),
        ):
            field.selection_ids.filtered(lambda s: s.value == "draft").unlink()
        record.invalidate_recordset(["x_pdef"])
        self.assertEqual(record.x_pdef, "done")

    def test_ondelete_cascade(self):
        Model, field = self._make_selection_field("pcasc")
        record = Model.create({"x_pcasc": "draft"})
        record.flush_recordset()
        with patch.object(
            self._field_obj(Model, "pcasc"), "ondelete", {"draft": "cascade"}
        ):
            field.selection_ids.filtered(lambda s: s.value == "draft").unlink()
        self.assertFalse(record.exists())

    def test_ondelete_callable(self):
        Model, field = self._make_selection_field("pcall")
        record = Model.create({"x_pcall": "draft"})
        record.flush_recordset()
        seen = []

        def policy(records):
            seen.extend(records.ids)
            records.write({"x_pcall": "done"})

        with patch.object(
            self._field_obj(Model, "pcall"), "ondelete", {"draft": policy}
        ):
            field.selection_ids.filtered(lambda s: s.value == "draft").unlink()
        record.invalidate_recordset(["x_pcall"])
        self.assertEqual(seen, record.ids)
        self.assertEqual(record.x_pcall, "done")

    def test_ondelete_resolves_values_in_one_batch(self):
        Model, field = self._make_selection_field(
            "pbatch", values=[("a", "A"), ("b", "B"), ("c", "C")]
        )
        records = Model.create([{"x_pbatch": v} for v in ("a", "b", "c")])
        records.flush_recordset()

        sel_cls = type(self.env["ir.model.fields.selection"])
        original = sel_cls._get_records_by_value
        calls = []

        def counting(self2, *args, **kwargs):
            calls.append(1)
            return original(self2, *args, **kwargs)

        with patch.object(sel_cls, "_get_records_by_value", counting):
            field.selection_ids.unlink()

        self.assertEqual(len(calls), 1)
        records.invalidate_recordset(["x_pbatch"])
        self.assertEqual(records.mapped("x_pbatch"), [False, False, False])

    def test_update_selection_returns_none(self):
        Model, field = self._make_selection_field("updret")
        result = self.env["ir.model.fields.selection"]._update_selection(
            Model._name,
            field.name,
            [("draft", "Brouillon"), ("new", "New")],
        )
        self.assertIsNone(result)
        self.assertEqual(
            self.env["ir.model.fields.selection"]._get_selection_data(field.id),
            [("draft", "Brouillon"), ("new", "New")],
        )

    def test_ondelete_set_null_company_dependent(self):
        company = self.env.company
        Model, field = self._make_selection_field("pcd", company_dependent=True)
        record = Model.create({})
        record.flush_recordset()
        self._set_jsonb(Model, field, record, {company.id: "draft"})

        field.selection_ids.filtered(lambda s: s.value == "draft").unlink()

        record.invalidate_recordset(["x_pcd"])
        self.assertFalse(record.with_company(company).x_pcd)

    def test_ondelete_company_dependent_outside_env_companies(self):
        other = self.env["res.company"].create({"name": "SEL-P4 other"})
        Model, field = self._make_selection_field("outscope", company_dependent=True)
        record = Model.create({})
        record.flush_recordset()
        self._set_jsonb(Model, field, record, {other.id: "draft"})

        scoped = self.env(
            context=dict(self.env.context, allowed_company_ids=[self.env.company.id])
        )
        self.assertNotIn(other.id, scoped.companies.ids)

        field.with_env(scoped).selection_ids.filtered(
            lambda s: s.value == "draft"
        ).unlink()

        self.assertFalse(self._read_jsonb(Model, field, record))

    @mute_logger("odoo.addons.base.models.ir_model_fields_selection")
    def test_ondelete_orm_bypass_preserves_other_companies(self):
        other = self.env["res.company"].create({"name": "SEL-C3 other"})
        Model, field = self._make_selection_field("bypass", company_dependent=True)
        record = Model.create({})
        record.flush_recordset()
        self._set_jsonb(
            Model, field, record, {self.env.company.id: "draft", other.id: "done"}
        )

        failure = UserError("forced ORM failure")
        with self._write_raises(Model._name, field.name, failure):
            field.selection_ids.filtered(lambda s: s.value == "draft").unlink()
        self.env.flush_all()

        stored = self._read_jsonb(Model, field, record)
        self.assertEqual(
            stored.get(str(other.id)),
            "done",
            "the other company's unrelated value must survive the bypass",
        )
        self.assertFalse(stored.get(str(self.env.company.id)))

    def test_ondelete_tolerates_non_object_jsonb(self):
        Model, field = self._make_selection_field("scalar", company_dependent=True)
        polluted = Model.create({})
        healthy = Model.create({})
        Model.flush_model()
        self.env.cr.execute(
            SQL(
                "UPDATE %s SET %s = 'null'::jsonb WHERE id = %s",
                SQL.identifier(Model._table),
                SQL.identifier(field.name),
                polluted.id,
            )
        )
        self._set_jsonb(Model, field, healthy, {self.env.company.id: "draft"})

        field.selection_ids.filtered(lambda s: s.value == "draft").unlink()

        self.assertFalse(self._read_jsonb(Model, field, healthy))


class TestIrModelDataCacheInvalidation(TransactionCase):
    def _groups_cleared(self, mock):
        return any(call.args == ("groups",) for call in mock.call_args_list)

    def test_create_groups_xmlid_clears_groups_cache(self):
        group = self.env["res.groups"].create({"name": "IMD cache group create"})
        with patch.object(
            self.env.registry, "clear_cache", wraps=self.env.registry.clear_cache
        ) as mock_clear:
            self.env["ir.model.data"].create(
                {
                    "module": "base",
                    "name": "imd_cache_group_create",
                    "model": "res.groups",
                    "res_id": group.id,
                }
            )
        self.assertTrue(self._groups_cleared(mock_clear))

    def test_unlink_groups_xmlid_clears_groups_cache(self):
        group = self.env["res.groups"].create({"name": "IMD cache group unlink"})
        data = self.env["ir.model.data"].create(
            {
                "module": "base",
                "name": "imd_cache_group_unlink",
                "model": "res.groups",
                "res_id": group.id,
            }
        )
        with patch.object(
            self.env.registry, "clear_cache", wraps=self.env.registry.clear_cache
        ) as mock_clear:
            data.unlink()
        self.assertTrue(self._groups_cleared(mock_clear))

    def test_update_xmlids_clears_groups_and_does_not_seed_the_lookup_cache(self):
        group = self.env["res.groups"].create({"name": "IMD cache group update"})
        xmlid = "base.imd_cache_group_update"
        with patch.object(
            self.env.registry, "clear_cache", wraps=self.env.registry.clear_cache
        ) as mock_clear:
            self.env["ir.model.data"]._update_xmlids(
                [{"xml_id": xmlid, "record": group}]
            )
        self.assertTrue(self._groups_cleared(mock_clear))
        with self.assertQueryCount(1):
            self.assertEqual(
                self.env["ir.model.data"]._get_xmlid_target(xmlid),
                ("res.groups", group.id),
            )
        with self.assertQueryCount(0):
            self.assertEqual(
                self.env["ir.model.data"]._get_xmlid_target(xmlid),
                ("res.groups", group.id),
            )


class TestIrModelData(TransactionCase):
    def test_toggle_noupdate_access_and_flip(self):
        param = self.env["ir.config_parameter"].create(
            {"key": "imd.toggle.test", "value": "x"}
        )
        xid1 = self.env["ir.model.data"].create(
            {
                "module": "base",
                "name": "imd_toggle_a",
                "model": "ir.config_parameter",
                "res_id": param.id,
                "noupdate": False,
            }
        )
        xid2 = self.env["ir.model.data"].create(
            {
                "module": "base",
                "name": "imd_toggle_b",
                "model": "ir.config_parameter",
                "res_id": param.id,
                "noupdate": True,
            }
        )

        user = new_test_user(self.env, login="imd_toggle_user")
        with self.assertRaises(AccessError):
            self.env["ir.model.data"].with_user(user).toggle_noupdate(
                "ir.config_parameter", param.id
            )

        self.env["ir.model.data"].toggle_noupdate("ir.config_parameter", param.id)
        self.assertTrue(xid1.noupdate)
        self.assertFalse(xid2.noupdate)

    def _make_param_xid(self, name, noupdate=False):
        param = self.env["ir.config_parameter"].create(
            {"key": f"imd.{name}", "value": "x"}
        )
        xid = self.env["ir.model.data"].create(
            {
                "module": "base",
                "name": name,
                "model": "ir.config_parameter",
                "res_id": param.id,
                "noupdate": noupdate,
            }
        )
        return param, xid

    def test_noupdate_only_write_skips_default_cache_clear(self):
        _param, xid = self._make_param_xid("imd_p1_noupdate_only")

        with patch.object(
            self.env.registry, "clear_cache", wraps=self.env.registry.clear_cache
        ) as mock_clear:
            xid.write({"noupdate": True})
        self.assertNotIn(
            (),
            [call.args for call in mock_clear.call_args_list],
            "a noupdate-only write must not clear the default registry cache",
        )

        with patch.object(
            self.env.registry, "clear_cache", wraps=self.env.registry.clear_cache
        ) as mock_clear:
            xid.write({"noupdate": False, "name": "imd_p1_noupdate_only_renamed"})
        self.assertIn(
            ("xmlid",),
            [call.args for call in mock_clear.call_args_list],
            "a write touching more than noupdate must clear the xmlid cache",
        )
        self.assertNotIn(
            (),
            [call.args for call in mock_clear.call_args_list],
            "an xmlid change is not a reason to evict every default-bucket cache",
        )

    def test_toggle_noupdate_batches_writes(self):
        param, _xid_a = self._make_param_xid("imd_p2_toggle_a", noupdate=False)
        for name, noupdate in (
            ("imd_p2_toggle_b", False),
            ("imd_p2_toggle_c", True),
        ):
            self.env["ir.model.data"].create(
                {
                    "module": "base",
                    "name": name,
                    "model": "ir.config_parameter",
                    "res_id": param.id,
                    "noupdate": noupdate,
                }
            )

        DataClass = type(self.env["ir.model.data"])
        orig_write = DataClass.write
        write_vals = []

        def spy(records, vals):
            write_vals.append(vals)
            return orig_write(records, vals)

        with patch.object(DataClass, "write", spy):
            self.env["ir.model.data"].toggle_noupdate("ir.config_parameter", param.id)

        self.assertLessEqual(
            len(write_vals),
            2,
            "toggle_noupdate must batch by current value (at most two writes)",
        )
        xids = self.env["ir.model.data"].search(
            [("model", "=", "ir.config_parameter"), ("res_id", "=", param.id)]
        )
        self.assertEqual(
            {xid.name: xid.noupdate for xid in xids},
            {
                "imd_p2_toggle_a": True,
                "imd_p2_toggle_b": True,
                "imd_p2_toggle_c": False,
            },
            "each xid must flip relative to its own previous value",
        )

    def test_empty_write_and_unlink_skip_cache_clear(self):
        empty = self.env["ir.model.data"].browse()
        with patch.object(
            self.env.registry, "clear_cache", wraps=self.env.registry.clear_cache
        ) as mock_clear:
            self.assertTrue(empty.write({"noupdate": True, "name": "zzz"}))
            self.assertTrue(empty.unlink())
        mock_clear.assert_not_called()

    def test_update_xmlids_literal_percent(self):
        record = self.env["res.partner.tag"].create({"name": "Percent"})
        xmlid = "test_convert.category_100%_percent"
        self.env["ir.model.data"]._update_xmlids([{"xml_id": xmlid, "record": record}])
        self.assertEqual(
            self.env["ir.model.data"]._get_xmlid_target(xmlid),
            (record._name, record.id),
        )

    def _isolated_process_end(self, modules):
        with patch.object(self.env.registry, "loaded_xmlids", set()):
            self.env["ir.model.data"]._process_end(modules)

    def test_process_end_keeps_record_while_another_xmlid_lives(self):
        module = "x_imd_procend"
        category = self.env["res.partner.tag"].create({"name": "procend"})
        self.env.flush_all()
        for index in range(3):
            self.env["ir.model.data"].create(
                {
                    "module": module,
                    "name": f"cat_{index}",
                    "model": "res.partner.tag",
                    "res_id": category.id,
                }
            )
        self.env.flush_all()

        self._isolated_process_end([module])

        self.assertFalse(category.exists(), "record deleted exactly once")
        self.assertFalse(
            self.env["ir.model.data"].search([("module", "=", module)]),
            "every redundant xml id removed",
        )

    def test_process_end_keeps_record_owned_by_another_module(self):
        module = "x_imd_procend2"
        category = self.env["res.partner.tag"].create({"name": "procend2"})
        self.env.flush_all()
        self.env["ir.model.data"].create(
            {
                "module": module,
                "name": "cat_a",
                "model": "res.partner.tag",
                "res_id": category.id,
            }
        )
        keeper = self.env["ir.model.data"].create(
            {
                "module": "base",
                "name": "x_imd_procend2_keeper",
                "model": "res.partner.tag",
                "res_id": category.id,
            }
        )
        self.env.flush_all()

        self._isolated_process_end([module])

        self.assertTrue(category.exists(), "another module still owns the record")
        self.assertTrue(keeper.exists())
        self.assertFalse(self.env["ir.model.data"].search([("module", "=", module)]))

    def test_lookup_xmlids_resolves(self):
        group = self.env.ref("base.group_user")
        rows = self.env["ir.model.data"]._get_xmlids(
            ["base.group_user", "base.zzz_no_such_xmlid"], self.env["res.groups"]
        )
        self.assertEqual(len(rows), 1)
        _id, module, name, model, res_id, _noupdate, r_id = rows[0]
        self.assertEqual(
            (module, name, model, res_id, r_id),
            ("base", "group_user", "res.groups", group.id, group.id),
        )


class TestIrModelConstraintReflection(TransactionCase):
    MODEL = "ir.model.data"

    def _constraint_rows(self, names):
        return {
            name: (id_, type_, definition, write_date)
            for name, id_, type_, definition, write_date in self.env.execute_query(
                SQL(
                    "SELECT name, id, type, definition, write_date"
                    " FROM ir_model_constraint WHERE name = ANY(%s)",
                    names,
                )
            )
        }

    def test_constraint_drop_resolves_table_from_postgres(self):
        rows = self.env.execute_query(
            SQL(
                """SELECT c.id, c.name, im.model
                   FROM ir_model_constraint c
                   JOIN ir_model im ON c.model = im.id
                   WHERE im.model = 'ir.actions.client' AND c.type = 'u'
                   LIMIT 1"""
            )
        )
        if not rows:
            self.skipTest("no reflected constraint on ir.actions.client")
        constraint_id, name, model_name = rows[0]
        self.assertNotEqual(
            self.env[model_name]._table,
            model_name.replace(".", "_"),
            "precondition: this model's table is not derivable from its name",
        )

        model_cls = self.env.registry.models.pop(model_name)
        try:
            self.env["ir.model.constraint"].browse(constraint_id).unlink()
        finally:
            self.env.registry.models[model_name] = model_cls

        remaining = self.env.execute_query(
            SQL(
                """SELECT 1 FROM pg_constraint cs
                   JOIN pg_class cl ON cs.conrelid = cl.oid
                   WHERE cs.conname = %s
                   AND cl.relnamespace = current_schema::regnamespace""",
                name,
            )
        )
        self.assertFalse(remaining, "constraint must actually be dropped")

    def test_process_end_keeps_a_constraint_the_registry_still_declares(self):
        rows = self.env.execute_query(
            SQL(
                """SELECT c.id, c.name, im.model, d.module || '.' || d.name
                   FROM ir_model_constraint c
                   JOIN ir_model im ON c.model = im.id
                   JOIN ir_model_data d
                     ON d.model = 'ir.model.constraint' AND d.res_id = c.id
                   WHERE d.module = 'base'
                     AND COALESCE(d.noupdate, false) = false"""
            )
        )
        target = next(
            (
                row
                for row in rows
                if (model := self.env.get(row[2])) is not None
                and row[1] in model._table_objects
            ),
            None,
        )
        if target is None:
            self.skipTest("no constraint reflected under base is still declared")
        cons_id, _name, _model_name, xmlid = target

        others = {
            row[0]
            for row in self.env.execute_query(
                SQL(
                    "SELECT module || '.' || name FROM ir_model_data"
                    " WHERE module = 'base'"
                )
            )
        } - {xmlid}
        loaded = self.env.registry.loaded_xmlids
        saved = set(loaded)
        loaded.clear()
        loaded.update(others)
        try:
            self.env["ir.model.data"]._process_end(["base"])
        finally:
            loaded.clear()
            loaded.update(saved)

        self.assertTrue(
            self.env["ir.model.constraint"].browse(cons_id).exists(),
            "a constraint the registry still declares must survive the GC",
        )

    def test_reflect_constraints_idempotent_and_repairs(self):
        Constraint = self.env["ir.model.constraint"]
        names = list(self.env[self.MODEL]._table_objects)
        self.assertTrue(names, "test model must declare table objects")

        Constraint._reflect_constraints([self.MODEL])
        before = self._constraint_rows(names)
        self.assertEqual(set(before), set(names), "every table object reflected")
        Constraint._reflect_constraints([self.MODEL])
        self.assertEqual(
            self._constraint_rows(names),
            before,
            "an unchanged constraint must not be rewritten (write_date stable)",
        )

        drifted = names[0]
        self.env.cr.execute(
            "UPDATE ir_model_constraint SET definition = 'bogus' WHERE name = %s",
            (drifted,),
        )
        Constraint._reflect_constraints([self.MODEL])
        after = self._constraint_rows(names)
        self.assertNotEqual(after[drifted][2], "bogus", "drifted row repaired")
        self.assertEqual(after[drifted][0], before[drifted][0])


class TestIrModelInfoStopsAtTheOrmBoundary(TransactionCase):
    def _info(self, model_name):
        model = self.env[model_name]
        return self.env["ir.model"]._prepare_model_vals(model)["info"]

    def test_no_model_inherits_pythons_object_docstring(self):
        borrowed = [
            name
            for name in self.env.registry.models
            if (self._info(name) or "") == object.__doc__
        ]
        self.assertFalse(
            borrowed,
            msg=(
                f"{len(borrowed)} model(s) show object.__doc__ as their "
                f"Information text. The MRO walk that finds it runs to the end "
                f"of the chain, and object always has a docstring, so any model "
                f"without one of its own borrows Python's."
            ),
        )

    def test_a_model_with_no_documentation_reports_none(self):
        self.assertIsNone(
            self._info("ir.model"),
            msg="a model with no docstring of its own has no Information text",
        )

    def test_a_documented_mixin_lends_no_text_to_the_model_inheriting_it(self):
        Partner = self.env.registry["res.partner"]
        mixins = [
            cls
            for cls in Partner.mro()
            if getattr(cls, "_name", None) not in (None, "res.partner")
        ]
        self.assertTrue(mixins, "res.partner inherits at least one mixin")
        with ExitStack() as stack:
            for cls in mixins:
                stack.enter_context(
                    patch.object(cls, "__doc__", f"What {cls._name} is for.")
                )
            self.assertNotIn("is for.", self._info("res.partner") or "")

    def test_a_documented_model_still_reports_its_own_text(self):
        cls = self.env.registry["ir.model"]
        with patch.object(cls, "__doc__", "What this model is for."):
            self.assertEqual(self._info("ir.model"), "What this model is for.")


class TestInverseSuppliedInTheSameBatch(TransactionCase):
    def _pair(self, tag):
        main, line = f"x_{tag}", f"x_{tag}_line"
        return (
            {
                "name": f"{tag} main",
                "model": main,
                "field_id": [
                    Command.create(
                        {
                            "name": f"{main}_line_ids",
                            "ttype": "one2many",
                            "relation": line,
                            "relation_field": f"{main}_id",
                            "field_description": "Lines",
                        }
                    )
                ],
            },
            {
                "name": f"{tag} line",
                "model": line,
                "field_id": [
                    Command.create(
                        {
                            "name": f"{main}_id",
                            "ttype": "many2one",
                            "relation": main,
                            "field_description": "Parent",
                        }
                    )
                ],
            },
        )

    def test_a_one2many_may_name_a_many2one_created_beside_it(self):
        main, line = self._pair("batchinv")
        models = self.env["ir.model"].create([main, line])
        self.assertEqual(len(models), 2)

    def test_the_order_within_the_batch_does_not_matter(self):
        main, line = self._pair("batchrev")
        models = self.env["ir.model"].create([line, main])
        self.assertEqual(len(models), 2)

    def test_a_genuinely_absent_inverse_still_raises(self):
        main, line = self._pair("batchmissing")
        line["field_id"] = []
        with self.assertRaises(UserError):
            self.env["ir.model"].create([main, line])

    def test_an_inverse_named_on_a_model_outside_the_batch_still_raises(self):
        main, _line = self._pair("batchforeign")
        main["field_id"][0][2]["relation"] = "res.partner"
        main["field_id"][0][2]["relation_field"] = "x_no_such_inverse_field"
        with self.assertRaises(UserError):
            self.env["ir.model"].create([main])
