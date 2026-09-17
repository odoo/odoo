import contextlib
import json
import unittest
from unittest.mock import patch

import psycopg

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.libs.lru import LRU
from odoo.tests import TransactionCase, can_import, loaded_demo_data, tagged
from odoo.tools.misc import file_open

from odoo.addons.base.models.ir_fields import SKIP


@tagged("post_install", "-at_install")
class TestFieldConverters(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.converter = cls.env["ir.fields.converter"]
        cls.flds = {
            "dt": cls.env["res.partner"]._fields["write_date"],
            "date": cls.env["res.partner"]._fields["write_date"],
            "bool": cls.env["res.partner"]._fields["is_company"],
            "m2o": cls.env["res.partner"]._fields["parent_id"],
            "float": cls.env["res.partner"]._fields["partner_latitude"],
        }

    def test_str_to_datetime_offset_bearing_iso_not_double_converted(self):
        converter = self.converter.with_context(tz="America/Mexico_City")
        value, warnings = converter._str_to_datetime(
            self.flds["dt"],
            "2026-03-19T16:09:18-06:00",
        )
        self.assertFalse(warnings)
        self.assertEqual(value, "2026-03-19 22:09:18")

    def test_str_to_datetime_naive_applies_input_tz(self):
        converter = self.converter.with_context(tz="America/Mexico_City")
        value, warnings = converter._str_to_datetime(
            self.flds["dt"],
            "2026-03-19 16:09:18",
        )
        self.assertFalse(warnings)
        self.assertEqual(value, "2026-03-19 22:09:18")

    def test_str_to_datetime_utc_z_suffix_not_double_converted(self):
        converter = self.converter.with_context(tz="America/Mexico_City")
        value, warnings = converter._str_to_datetime(
            self.flds["dt"],
            "2026-03-19T16:09:18Z",
        )
        self.assertFalse(warnings)
        self.assertEqual(value, "2026-03-19 16:09:18")

    def test_str_to_date_rejects_trailing_garbage(self):
        with self.assertRaises(ValueError):
            self.converter._str_to_date(
                self.flds["date"],
                "2012-12-31xxx",
            )

    def test_str_to_date_valid(self):
        value, warnings = self.converter._str_to_date(
            self.flds["date"],
            "2012-12-31",
        )
        self.assertFalse(warnings)
        self.assertEqual(value, "2012-12-31")

    def test_str_to_date_accepts_trailing_time(self):
        for value in (
            "2012-12-31 00:00:00",
            "2012-12-31T23:59:59",
            "2012-12-31 23:59:59",
        ):
            result, warnings = self.converter._str_to_date(self.flds["date"], value)
            self.assertFalse(warnings)
            self.assertEqual(result, "2012-12-31", "%r must import as its date" % value)
        for value in ("2012-12-31xxx", "2012-12-31 nope"):
            with self.assertRaises(ValueError):
                self.converter._str_to_date(self.flds["date"], value)

    def test_boolean_value_sets_built_once(self):
        self.converter._get_transaction_cache().clear()
        calls = []
        orig = type(self.converter)._get_boolean_translations

        def spy(this, src):
            calls.append(src)
            return orig(this, src)

        with patch.object(type(self.converter), "_get_boolean_translations", spy):
            for _ in range(50):
                with contextlib.suppress(ValueError):
                    self.converter._str_to_boolean(self.flds["bool"], "maybe")
        self.assertLessEqual(
            len(calls),
            4,
            "boolean token sets must be built a constant number of times, "
            "not once per converted cell",
        )

    def test_str_to_properties_does_not_mutate_input(self):
        original = [
            {"name": "x", "type": "integer", "string": "X", "value": "42"},
        ]
        snapshot = [dict(pd) for pd in original]
        result, _warnings = self.converter._str_to_properties(
            self.flds["bool"], original
        )
        self.assertEqual(original, snapshot, "input must not be mutated")
        self.assertIsNot(result, original, "output must be a fresh list")
        self.assertEqual(result[0]["value"], 42, "value must be coerced in output")

    def test_db_id_for_unknown_subfield_is_valueerror(self):
        with self.assertRaises(ValueError):
            self.converter._get_db_id(self.flds["m2o"], "not_a_subfield", "x")

    def test_db_id_for_dbid_resolution(self):
        partner = self.env["res.partner"].search([], limit=1)
        self.assertTrue(partner, "need at least one partner to resolve")
        got, warnings = self.converter._get_db_id(
            self.flds["m2o"], ".id", str(partner.id)
        )
        self.assertEqual(got, partner.id)
        self.assertFalse(warnings)
        empty, _w = self.converter._get_db_id(self.flds["m2o"], ".id", "0")
        self.assertIs(empty, False)
        with self.assertRaises(ValueError):
            self.converter._get_db_id(self.flds["m2o"], ".id", str(partner.id + 10**9))

    def test_str_to_float_rejects_non_finite(self):
        for value in ("nan", "NaN", "inf", "-inf", "Infinity", "1e400"):
            with self.assertRaises(ValueError, msg="%r must be rejected" % value):
                self.converter._str_to_float(self.flds["float"], value)
        for value, expected in (("1.5", 1.5), (" 2.5 ", 2.5), ("1e3", 1000.0)):
            result, warnings = self.converter._str_to_float(self.flds["float"], value)
            self.assertFalse(warnings)
            self.assertEqual(result, expected)

    def test_str_to_boolean_unknown_raises(self):
        with self.assertRaises(ValueError) as cm:
            self.converter._str_to_boolean(self.flds["bool"], "maybe")
        self.assertIn("maybe", str(cm.exception.args[0]))

    def test_str_to_boolean_skip_policy_returns_the_skip_sentinel(self):
        skipping = self.converter.with_context(
            import_file=True, import_skip_records=["is_company"]
        )
        value, warnings = skipping._str_to_boolean(self.flds["bool"], "maybe")
        self.assertIs(value, SKIP)
        self.assertFalse(warnings)

    def test_boolean_error_carries_field_path(self):
        result = (
            self.env["res.partner"]
            .with_context(import_file=True)
            .load(["name", "is_company"], [["IFLD03 P", "maybe"]])
        )
        errors = [m for m in result["messages"] if m.get("type") == "error"]
        self.assertTrue(errors)
        self.assertEqual(errors[0].get("field_path"), ["is_company"])
        self.assertEqual(errors[0].get("moreinfo"), "Use '1' for yes and '0' for no")

    def test_str_to_boolean_known_values(self):
        true_val, _w = self.converter._str_to_boolean(self.flds["bool"], "1")
        false_val, _w = self.converter._str_to_boolean(self.flds["bool"], "0")
        self.assertIs(true_val, True)
        self.assertIs(false_val, False)

    def test_unsupported_field_type_logs_not_crash(self):
        target = None
        for model_name in self.env.registry.models:
            for fname, f in self.env[model_name]._fields.items():
                if not hasattr(self.converter, f"_str_to_{f.type}"):
                    target = (self.env[model_name], fname, f.type)
                    break
            if target:
                break
        if not target:
            self.skipTest("every field type has a converter on this build")
        model, fname, ftype = target
        fn = self.converter._get_converter_record(model)
        logged = []
        result = fn({fname: "x"}, lambda field, exc: logged.append((field, exc)))
        self.assertNotIn(fname, result, "unconvertible field must not be written")
        self.assertEqual([f for f, _exc in logged], [fname])
        self.assertIsInstance(logged[0][1], ValueError)
        self.assertIn(ftype, str(logged[0][1].args[0]))

    def test_nested_selection_skip_uses_full_path(self):
        fld = self.env["res.partner"]._fields["type"]
        nested = self.converter.with_context(
            import_file=True,
            parent_fields_hierarchy=["child_ids"],
            import_skip_records=["child_ids/type"],
        )
        value, warnings = nested._str_to_selection(fld, "not_a_real_type")
        self.assertIs(value, SKIP)
        self.assertFalse(warnings)

        bare = self.converter.with_context(
            import_file=True,
            parent_fields_hierarchy=["child_ids"],
            import_skip_records=["type"],
        )
        with self.assertRaises(ValueError):
            bare._str_to_selection(fld, "not_a_real_type")

    def test_str_to_selection_description_built_once(self):
        fld = self.env["ir.actions.server"]._fields["update_field_type"]
        self.assertTrue(callable(fld.selection), "need a callable selection")
        calls = []
        orig = type(fld)._description_selection

        def spy(self, env, *args, **kwargs):
            calls.append(1)
            return orig(self, env, *args, **kwargs)

        with patch.object(type(fld), "_description_selection", spy):
            with self.assertRaises(ValueError):
                self.converter._str_to_selection(fld, "zzz_nonexistent_value")
        self.assertLessEqual(
            len(calls),
            5,
            "selection description must be built a constant number of times, "
            "not once per selection item",
        )

    def test_str_to_selection_index_single_query(self):
        fld = self.env["res.partner"]._fields["tz"]
        n = len(fld.selection)
        self.assertGreater(n, 100, "need a large static selection")
        self.converter._get_transaction_cache().clear()
        self.env["ir.model.fields.selection"].flush_model()

        cr = self.env.cr
        calls = []
        orig = cr.execute

        def spy(query, params=None):
            calls.append(1)
            return orig(query, params) if params is not None else orig(query)

        with patch.object(cr, "execute", spy):
            for item, _label in fld.selection:
                self.assertEqual(
                    self.converter._str_to_selection(fld, str(item))[0], item
                )
        self.assertLessEqual(
            len(calls),
            2,
            f"resolving all {n} items must build one whole-field index, not "
            f"issue a query per item (got {len(calls)} queries)",
        )

    def test_db_id_for_non_str_reference_is_clean_error(self):
        for subfield in (".id", "id"):
            with self.assertRaises(ValueError):
                self.converter._get_db_id(self.flds["m2o"], subfield, 123456789)

    def test_referencing_subfield_empty_record(self):
        with self.assertRaises(ValueError) as cm:
            self.converter._get_subfield_referencing({})
        self.assertNotIn("unpack", str(cm.exception))

    def test_o2m_unknown_subfield_is_valueerror(self):
        fld = self.env["res.partner"]._fields["child_ids"]
        with self.assertRaises(ValueError) as cm:
            self.converter._str_to_one2many(fld, [{"bogus.x": "42"}])
        self.assertIn("bogus.x", str(cm.exception.args[0]))

    def test_load_o2m_unknown_subfield_logs_not_crash(self):
        result = self.env["res.partner"].load(
            ["name", "child_ids/name", "child_ids/bogus.x"],
            [["IFLD15 Parent", "IFLD15 Child", "42"]],
        )
        self.assertFalse(result["ids"], "the erroneous import must not create ids")
        errors = [m for m in result["messages"] if m.get("type") == "error"]
        self.assertTrue(errors, "expected a per-field import error message")
        self.assertEqual(errors[0].get("field"), "child_ids")
        self.assertIn("bogus.x", errors[0]["message"])

    def test_name_create_programming_error_propagates(self):
        converter = self.converter.with_context(
            name_create_enabled_fields={"parent_id": True}
        )
        PartnerClass = type(self.env["res.partner"])
        with (
            patch.object(
                PartnerClass, "name_create", side_effect=TypeError("broken override")
            ),
            self.assertRaises(TypeError),
        ):
            converter._get_db_id(self.flds["m2o"], None, "zzz no such partner ifld16")

    def test_name_create_user_error_becomes_import_message(self):
        converter = self.converter.with_context(
            name_create_enabled_fields={"parent_id": True}
        )
        PartnerClass = type(self.env["res.partner"])
        with (
            patch.object(PartnerClass, "name_create", side_effect=UserError("nope")),
            self.assertRaises(ValueError) as cm,
        ):
            converter._get_db_id(self.flds["m2o"], None, "zzz no such partner ifld16")
        self.assertIn("Cannot create new", str(cm.exception.args[0]))

    def test_m2m_blank_comma_segments_dropped(self):
        tag = self.env["res.partner.tag"].create({"name": "IFLD17 Tag"})
        converter = self.converter._resolve_converter_field(
            self.env["res.partner"]._fields["tag_ids"]
        )
        for raw in ("IFLD17 Tag,", ",IFLD17 Tag", "IFLD17 Tag, ", "IFLD17 Tag,,"):
            commands, warnings = converter([{None: raw}])
            self.assertFalse(warnings)
            self.assertEqual(
                commands,
                [Command.set([tag.id])],
                f"{raw!r} must resolve to exactly one reference",
            )

    def test_load_m2m_trailing_comma_imports(self):
        self.env["res.partner.tag"].create({"name": "IFLD17 E2E"})
        result = self.env["res.partner"].load(
            ["name", "tag_ids"], [["IFLD17 Partner", "IFLD17 E2E,"]]
        )
        self.assertFalse(result["messages"])
        self.assertTrue(result["ids"])
        partner = self.env["res.partner"].browse(result["ids"])
        self.assertEqual(partner.tag_ids.mapped("name"), ["IFLD17 E2E"])

    def test_o2m_blank_comma_segment_creates_no_record(self):
        child = self.env["res.partner"].create({"name": "IFLD18 Child"})
        self.env["ir.model.data"].create(
            {
                "module": "base",
                "name": "ifld18_child",
                "model": "res.partner",
                "res_id": child.id,
            }
        )
        commands, warnings = self.converter._str_to_one2many(
            self.env["res.partner"]._fields["child_ids"],
            [{"id": "base.ifld18_child,"}],
        )
        self.assertFalse(warnings)
        self.assertEqual(commands, [Command.link(child.id)])

    def test_o2m_link_omits_empty_update(self):
        child = self.env["res.partner"].create({"name": "IFLD18b Child"})
        self.env["ir.model.data"].create(
            {
                "module": "base",
                "name": "ifld18b_child",
                "model": "res.partner",
                "res_id": child.id,
            }
        )
        commands, _warnings = self.converter._str_to_one2many(
            self.env["res.partner"]._fields["child_ids"],
            [{"id": "base.ifld18b_child"}],
        )
        self.assertNotIn(
            Command.update(child.id, {}),
            commands,
            "an empty update command must not be emitted",
        )

    def test_non_str_error_param_survives_second_format_pass(self):
        with self.assertRaises(ValueError) as cm:
            self.converter._str_to_properties(
                self.flds["bool"], [{"name": "x", "string": "100% off"}]
            )
        message = str(cm.exception.args[0])
        formatted = message % {"record": 0, "field": "Props"}
        self.assertIn("100% off", formatted)

    def test_xmlid_model_mismatch_is_reportable_import_error(self):
        lang = self.env["res.lang"].search([], limit=1)
        self.env["ir.model.data"].create(
            {
                "module": "base",
                "name": "ifld20_pct%x",
                "model": "res.lang",
                "res_id": lang.id,
            }
        )
        self.env.flush_all()
        result = self.env["res.partner"].load(
            ["name", "parent_id/id"], [["IFLD20", "base.ifld20_pct%x"]]
        )
        self.assertFalse(result["ids"])
        errors = [m for m in result["messages"] if m.get("type") == "error"]
        self.assertTrue(errors, "expected a per-record import error message")
        self.assertIn("base.ifld20_pct%x", errors[0]["message"])
        self.assertIn("res.lang", errors[0]["message"])

    def test_driver_error_text_with_percent_is_escaped(self):
        converter = self.converter

        def boom(_value):
            raise psycopg.DataError('invalid input syntax for integer: "50%"')

        messages = []
        with patch.object(
            type(converter), "_resolve_converter_field", lambda *a, **kw: boom
        ):
            convert = converter._get_converter_record(self.env["res.partner"])
            convert({"name": "x"}, lambda f, e: messages.append(str(e.args[0])))

        self.assertTrue(messages, "expected the driver error to be logged")
        formatted = messages[0] % {"record": 0, "field": "Name"}
        self.assertIn('"50%"', formatted)

    def test_unknown_field_reported_and_not_written(self):
        convert = self.converter._get_converter_record(self.env["res.partner"])
        logged = []
        converted = convert(
            {"name": "x", "ifld22_empty": "", "ifld22_filled": "v"},
            lambda f, e: logged.append((f, str(e.args[0]))),
        )
        self.assertEqual(converted, {"name": "x"})
        self.assertEqual(
            sorted(f for f, _m in logged), ["ifld22_empty", "ifld22_filled"]
        )
        for _field, message in logged:
            self.assertIn("does not exist", message)

    def test_relational_property_policy_path_matches_column(self):
        captured = []

        def spy(this, field, record, *, multi):
            captured.append(field.name)
            return [], []

        with patch.object(type(self.converter), "_get_reference_ids", spy):
            self.converter._str_to_properties(
                self.flds["bool"],
                [
                    {
                        "name": "my_prop",
                        "type": "many2many",
                        "string": "My Display Label",
                        "comodel": "res.partner",
                        "value": [{None: "whatever"}],
                    }
                ],
            )
        self.assertEqual(captured, ["is_company.my_prop"])

    def test_selection_translation_index_is_ordered(self):
        field = self.env["res.partner"]._fields["type"]
        self.converter._get_transaction_cache().clear()
        queries = []
        orig_execute = type(self.env.cr).execute

        def spy(cr, query, *args, **kwargs):
            queries.append(str(query))
            return orig_execute(cr, query, *args, **kwargs)

        with patch.object(type(self.env.cr), "execute", spy):
            self.converter._get_selection_index(field)
        selection_queries = [q for q in queries if "ir_model_fields_selection" in q]
        self.assertTrue(selection_queries, "expected the selection label query")
        self.assertTrue(
            any("ORDER BY" in q.upper() for q in selection_queries),
            "the selection label query must be deterministically ordered",
        )

    def test_load_unknown_column_reports_instead_of_crashing(self):
        for column in ("bogus.x", "nosuchfield"):
            with self.subTest(column=column):
                result = self.env["res.partner"].load(
                    ["name", column], [["IFLD25", "42"]]
                )
                self.assertFalse(result["ids"])
                errors = [m for m in result["messages"] if m.get("type") == "error"]
                self.assertTrue(errors, "expected a per-field import error")
                self.assertEqual(errors[0].get("field"), column)
                self.assertIn("does not exist", errors[0]["message"])
        self.env.cr.execute("SELECT 1")
        self.assertEqual(self.env.cr.fetchone(), (1,))

    def test_skip_records_ignores_columns_absent_from_the_import(self):
        model = self.env["res.partner"].with_context(
            import_file=True, import_skip_records=["type"]
        )
        result = model.load(["name"], [["IFLD26 A"], ["IFLD26 B"]])
        self.assertFalse(result["messages"])
        self.assertEqual(len(result["ids"] or []), 2, "no record may be skipped")

    def test_skip_records_still_skips_the_unresolved_record(self):
        model = self.env["res.partner"].with_context(
            import_file=True, import_skip_records=["type"]
        )
        result = model.load(
            ["name", "type"],
            [["IFLD26 bad", "not_a_real_type"], ["IFLD26 ok", "contact"]],
        )
        self.assertFalse(result["messages"])
        self.assertEqual(len(result["ids"] or []), 1, "only the bad row is skipped")

    def test_nested_skip_records_skips_the_parent_record(self):
        model = self.env["res.partner"].with_context(
            import_file=True, import_skip_records=["child_ids/type"]
        )
        result = model.load(
            ["name", "child_ids/name", "child_ids/type"],
            [["IFLD27 Parent", "IFLD27 Child", "not_a_real_type"]],
        )
        self.assertFalse(result["messages"])
        self.assertFalse(result["ids"], "the record must be skipped")
        self.assertFalse(
            self.env["res.partner"].search([("name", "=", "IFLD27 Parent")])
        )

    def test_nested_skip_records_keeps_resolvable_records(self):
        model = self.env["res.partner"].with_context(
            import_file=True, import_skip_records=["child_ids/type"]
        )
        result = model.load(
            ["name", "child_ids/name", "child_ids/type"],
            [["IFLD27 Good", "IFLD27 Good Child", "contact"]],
        )
        self.assertFalse(result["messages"])
        self.assertEqual(len(result["ids"] or []), 1)

    def test_name_create_driver_error_leaves_cursor_usable(self):
        converter = self.converter.with_context(
            name_create_enabled_fields={"parent_id": True}
        )

        def boom(*args, **kwargs):
            self.env.cr.execute("SELECT 1 / 0")

        PartnerClass = type(self.env["res.partner"])
        with patch.object(PartnerClass, "name_create", side_effect=boom):
            with self.assertRaises(ValueError) as cm:
                converter._get_db_id(
                    self.flds["m2o"], None, "zzz no such partner ifld28"
                )
        self.assertIn("Cannot create new", str(cm.exception.args[0]))
        self.env.cr.execute("SELECT 1")
        self.assertEqual(self.env.cr.fetchone(), (1,))

    def test_repeated_references_resolved_once_per_import(self):
        parent = self.env["res.partner"].create({"name": "IFLD29 Shared Parent"})
        self.env.flush_all()
        PartnerClass = type(self.env["res.partner"])
        calls = []
        orig = PartnerClass.name_search

        def spy(this, *args, **kwargs):
            calls.append(kwargs.get("name"))
            return orig(this, *args, **kwargs)

        rows = [[f"IFLD29 c{i}", "IFLD29 Shared Parent"] for i in range(6)]
        with patch.object(PartnerClass, "name_search", spy):
            result = self.env["res.partner"].load(["name", "parent_id"], rows)
        self.assertFalse(result["messages"])
        self.assertEqual(len(result["ids"] or []), 6)
        self.assertLessEqual(
            len(calls), 1, f"6 identical references must search once, got {len(calls)}"
        )
        self.assertEqual(
            self.env["res.partner"].browse(result["ids"]).mapped("parent_id"), parent
        )

    def test_references_to_existing_records_do_not_split_the_batch(self):
        Partner = self.env["res.partner"]
        Partner.create([{"name": f"IFLD96 parent {i}"} for i in range(40)])
        self.env.flush_all()
        PartnerClass = type(Partner)
        batches = []
        original = PartnerClass._load_data_list

        def spy(this, data_list, *args, **kwargs):
            batches.append(len(data_list))
            return original(this, data_list, *args, **kwargs)

        rows = [[f"IFLD96 child {i}", f"IFLD96 parent {i}"] for i in range(40)]
        with patch.object(PartnerClass, "_load_data_list", spy):
            result = Partner.load(["name", "parent_id"], rows)
        self.assertFalse(result["messages"])
        self.assertEqual(len(result["ids"]), 40)
        self.assertEqual(
            batches,
            [40],
            "a name that already resolves must not flush the pending batch",
        )

    def test_a_reference_to_an_earlier_row_of_the_same_import_resolves(self):
        Partner = self.env["res.partner"]
        result = Partner.load(
            ["name", "parent_id"],
            [["IFLD96 first", ""], ["IFLD96 second", "IFLD96 first"]],
        )
        self.assertFalse(result["messages"])
        first, second = Partner.browse(result["ids"])
        self.assertEqual(second.parent_id, first)

    def test_existing_names_are_prefetched_in_one_query_per_model(self):
        Partner = self.env["res.partner"]
        Partner.create([{"name": f"IFLD97 parent {i}"} for i in range(30)])
        self.env.flush_all()
        converter_type = type(self.env["ir.fields.converter"])
        searches = []
        original = converter_type._get_ref_from_name

        def spy(this, field, value):
            searches.append(value)
            return original(this, field, value)

        rows = [[f"IFLD97 child {i}", f"IFLD97 parent {i}"] for i in range(30)]
        with patch.object(converter_type, "_get_ref_from_name", spy):
            result = Partner.load(["name", "parent_id"], rows)
        self.assertFalse(result["messages"])
        self.assertEqual(
            searches, [], "every existing name must come from the prefetch"
        )
        parents = Partner.browse(result["ids"]).mapped("parent_id.name")
        self.assertEqual(parents, [f"IFLD97 parent {i}" for i in range(30)])

    def test_prefetch_attributes_a_match_on_a_secondary_name_field(self):
        Partner = self.env["res.partner"]
        self.assertIn("email", Partner._get_rec_names_search_fields())
        target = Partner.create({"name": "IFLD97 By Mail", "email": "ifld97@x.test"})
        other = Partner.create({"name": "IFLD97 Other", "email": "ifld97b@x.test"})
        self.env.flush_all()
        result = Partner.load(
            ["name", "parent_id"],
            [["IFLD97 c1", "ifld97@x.test"], ["IFLD97 c2", "ifld97b@x.test"]],
        )
        self.assertFalse(result["messages"])
        self.assertEqual(
            Partner.browse(result["ids"]).mapped("parent_id"), target + other
        )

    def test_prefetch_keeps_the_multiple_matches_warning(self):
        Partner = self.env["res.partner"]
        Partner.create([{"name": "IFLD97 Twin"}, {"name": "IFLD97 Twin"}])
        Partner.create({"name": "IFLD97 Single"})
        self.env.flush_all()
        result = Partner.load(
            ["name", "parent_id"],
            [["IFLD97 c1", "IFLD97 Twin"], ["IFLD97 c2", "IFLD97 Single"]],
        )
        self.assertTrue(result["ids"])
        warnings = [m for m in result["messages"] if m["type"] == "warning"]
        self.assertEqual(len(warnings), 1)
        self.assertIn("2 matches", warnings[0]["message"])

    def test_database_ids_and_external_ids_are_prefetched(self):
        Partner = self.env["res.partner"]
        parents = Partner.create([{"name": f"IFLD98 parent {i}"} for i in range(20)])
        self.env["ir.model.data"].create(
            [
                {
                    "module": "__import__",
                    "name": f"ifld98_parent_{i}",
                    "model": "res.partner",
                    "res_id": parent.id,
                }
                for i, parent in enumerate(parents)
            ]
        )
        self.env.flush_all()
        self.env.registry.clear_cache()
        converter_type = type(self.env["ir.fields.converter"])
        misses = []
        original_dbid = converter_type._get_ref_from_dbid
        original_xmlid = converter_type._get_ref_from_xmlid

        def spy_dbid(this, field, value):
            misses.append((".id", value))
            return original_dbid(this, field, value)

        def spy_xmlid(this, field, value):
            misses.append(("id", value))
            return original_xmlid(this, field, value)

        with (
            patch.object(converter_type, "_get_ref_from_dbid", spy_dbid),
            patch.object(converter_type, "_get_ref_from_xmlid", spy_xmlid),
        ):
            by_dbid = Partner.load(
                ["name", "parent_id/.id"],
                [[f"IFLD98 a{i}", str(parent.id)] for i, parent in enumerate(parents)],
            )
            by_xmlid = Partner.load(
                ["name", "parent_id/id"],
                [[f"IFLD98 b{i}", f"__import__.ifld98_parent_{i}"] for i in range(20)],
            )
            by_bare_xmlid = Partner.load(
                ["name", "parent_id/id"],
                [[f"IFLD98 c{i}", f"ifld98_parent_{i}"] for i in range(20)],
            )
        for result in (by_dbid, by_xmlid, by_bare_xmlid):
            self.assertFalse(result["messages"])
            self.assertEqual(Partner.browse(result["ids"]).mapped("parent_id"), parents)
        self.assertEqual(misses, [], "every reference must come from the prefetch")

    def test_a_prefetched_external_id_of_another_model_is_still_a_mismatch_error(self):
        Partner = self.env["res.partner"]
        lang = self.env["res.lang"].search([], limit=1)
        self.env["ir.model.data"].create(
            [
                {
                    "module": "base",
                    "name": "ifld98_lang",
                    "model": "res.lang",
                    "res_id": lang.id,
                },
                {
                    "module": "base",
                    "name": "ifld98_lang2",
                    "model": "res.lang",
                    "res_id": lang.id,
                },
            ]
        )
        self.env.flush_all()
        result = Partner.load(
            ["name", "parent_id/id"],
            [["IFLD98 x", "base.ifld98_lang"], ["IFLD98 y", "base.ifld98_lang2"]],
        )
        self.assertFalse(result["ids"])
        self.assertIn("res.lang", result["messages"][0]["message"])

    def test_a_pending_namesake_still_yields_the_multiple_matches_warning(self):
        Partner = self.env["res.partner"]
        Partner.create({"name": "IFLD100 Twin"})
        self.env.flush_all()
        self.env.invalidate_all()
        result = Partner.load(
            ["name", "parent_id"],
            [["IFLD100 Twin", ""], ["IFLD100 child", "IFLD100 Twin"]],
        )
        warnings = [m for m in result["messages"] if m["type"] == "warning"]
        self.assertEqual(len(warnings), 1, "the row this import creates is a match too")
        self.assertIn("2 matches", warnings[0]["message"])
        self.assertEqual(len(result["ids"]), 2)

    def test_reference_miss_is_not_cached(self):
        converter = self.converter.with_context(
            import_file=True,
            import_set_empty_fields=["parent_id"],
            import_cache=LRU(1024),
        )
        first, _w = converter._get_db_id(self.flds["m2o"], None, "IFLD29b Target")
        self.assertIsNone(first, "the record does not exist yet")
        target = self.env["res.partner"].create({"name": "IFLD29b Target"})
        self.env.flush_all()
        second, _w = converter._get_db_id(self.flds["m2o"], None, "IFLD29b Target")
        self.assertEqual(
            second, target.id, "a cached miss would still report 'not found'"
        )

    def test_reference_cache_does_not_outlive_one_load(self):
        target = self.env["res.partner"].create({"name": "IFLD29c Target"})
        self.env.flush_all()
        first = self.env["res.partner"].load(
            ["name", "parent_id"], [["IFLD29c child", "IFLD29c Target"]]
        )
        self.assertFalse(first["messages"])
        self.env["res.partner"].browse(first["ids"]).unlink()
        target.unlink()
        self.env.flush_all()
        second = self.env["res.partner"].load(
            ["name", "parent_id"], [["IFLD29c child2", "IFLD29c Target"]]
        )
        self.assertFalse(second["ids"], "the deleted target must not resolve")
        self.assertTrue(
            [m for m in second["messages"] if m.get("type") == "error"],
            "expected a 'no matching record' error",
        )

    def test_nested_skip_policy_requires_import_file(self):
        model = self.env["res.partner"].with_context(
            import_skip_records=["child_ids/type"]
        )
        result = model.load(
            ["name", "child_ids/name", "child_ids/type"],
            [["IFLD27b Parent", "IFLD27b Child", "not_a_real_type"]],
        )
        self.assertFalse(result["ids"])
        errors = [m for m in result["messages"] if m.get("type") == "error"]
        self.assertTrue(errors, "the bad cell must be reported, not skipped")
        self.assertEqual(errors[0].get("field_path"), ["child_ids", "type"])

    def test_nested_o2m_without_policy_still_creates_the_child(self):
        model = self.env["res.partner"].with_context(
            import_skip_records=["child_ids/type"]
        )
        result = model.load(
            ["name", "child_ids/name", "child_ids/type"],
            [["IFLD27d Parent", "IFLD27d Child", "contact"]],
        )
        self.assertFalse(result["messages"])
        self.assertEqual(len(result["ids"] or []), 1)
        parent = self.env["res.partner"].browse(result["ids"])
        self.assertEqual(parent.child_ids.mapped("name"), ["IFLD27d Child"])

    def test_deeply_nested_skip_records_propagates(self):
        model = self.env["res.partner"].with_context(
            import_file=True, import_skip_records=["child_ids/child_ids/type"]
        )
        result = model.load(
            [
                "name",
                "child_ids/name",
                "child_ids/child_ids/name",
                "child_ids/child_ids/type",
            ],
            [["IFLD27c P", "IFLD27c C", "IFLD27c GC", "not_a_real_type"]],
        )
        self.assertFalse(result["messages"])
        self.assertFalse(result["ids"], "the record must be skipped")
        self.assertFalse(self.env["res.partner"].search([("name", "=", "IFLD27c P")]))

    def test_many2one_multiple_reference_records_clean_error(self):
        with self.assertRaises(ValueError) as cm:
            self.converter._str_to_many2one(
                self.flds["m2o"], [{None: "a"}, {None: "b"}]
            )
        self.assertNotIn("unpack", str(cm.exception.args[0]))
        self.assertIn("single reference", str(cm.exception.args[0]))

    def test_error_field_path_does_not_invent_property_subfields(self):
        properties_value = [
            {"name": "p1", "type": "integer", "string": "P1", "value": "x"}
        ]
        self.assertEqual(
            self.converter._get_field_path_for_error("props", properties_value),
            ["props"],
        )

    def test_error_field_path_keeps_the_referencing_subfield(self):
        self.assertEqual(
            self.converter._get_field_path_for_error("value", [{"id": "noxidhere"}]),
            ["value", "id"],
        )
        self.assertEqual(
            self.converter._get_field_path_for_error("value", [{None: "somename"}]),
            ["value"],
        )
        nested = self.converter.with_context(parent_fields_hierarchy=["child_ids"])
        self.assertEqual(
            nested._get_field_path_for_error("type", "bad"), ["child_ids", "type"]
        )

    def test_o2m_subfield_label_with_percent_is_reported(self):
        fld = self.env["res.partner"]._fields["type"]
        with patch.object(fld, "string", "Address Type (%)"):
            result = (
                self.env["res.partner"]
                .with_context(import_file=True)
                .load(
                    ["name", "child_ids/name", "child_ids/type"],
                    [["IFLD32 Parent", "IFLD32 Child", "not_a_real_type"]],
                )
            )
        self.assertFalse(result["ids"])
        errors = [m for m in result["messages"] if m.get("type") == "error"]
        self.assertTrue(errors, "expected a per-record import error message")
        self.assertIn("Address Type (%)", errors[0]["message"])
        self.assertEqual(errors[0].get("field_path"), ["child_ids", "type"])

    def test_o2m_unknown_subfield_with_percent_is_reported(self):
        result = self.env["res.partner"].load(
            ["name", "child_ids/name", "child_ids/bogus%x"],
            [["IFLD32b Parent", "IFLD32b Child", "42"]],
        )
        self.assertFalse(result["ids"])
        errors = [m for m in result["messages"] if m.get("type") == "error"]
        self.assertTrue(errors, "expected a per-field import error message")
        self.assertIn("bogus%x", errors[0]["message"])

    def test_property_missing_type_metadata_is_reported(self):
        for ptype, missing in (
            ("selection", "selection"),
            ("tags", "tags"),
            ("many2one", "comodel"),
            ("many2many", "comodel"),
        ):
            with self.subTest(type=ptype):
                with self.assertRaises(ValueError) as cm:
                    self.converter._str_to_properties(
                        self.flds["bool"],
                        [
                            {
                                "name": "p",
                                "type": ptype,
                                "string": "P",
                                "value": "whatever",
                            }
                        ],
                    )
                self.assertIn(missing, str(cm.exception.args[0]))

    def test_boolean_property_policy_path_matches_column(self):
        payload = [
            {"name": "mybool", "type": "boolean", "string": "My Bool", "value": "maybe"}
        ]
        column = self.converter.with_context(
            import_file=True, import_skip_records=["is_company.mybool"]
        )
        value, warnings = column._str_to_properties(self.flds["bool"], payload)
        self.assertIs(value, SKIP, "the skip sentinel must propagate")
        self.assertFalse(warnings)

        parent = self.converter.with_context(
            import_file=True, import_skip_records=["is_company"]
        )
        with self.assertRaises(ValueError):
            parent._str_to_properties(self.flds["bool"], payload)

    def test_xmlid_model_mismatch_does_not_depend_on_id_overlap(self):
        self.env.cr.execute("SELECT COALESCE(max(id), 0) + 1000 FROM res_partner")
        [free_id] = self.env.cr.fetchone()
        self.env["ir.model.data"].create(
            {
                "module": "base",
                "name": "ifld35_elsewhere",
                "model": "res.lang",
                "res_id": free_id,
            }
        )
        self.env.flush_all()
        result = self.env["res.partner"].load(
            ["name", "parent_id/id"], [["IFLD35", "base.ifld35_elsewhere"]]
        )
        self.assertFalse(result["ids"])
        errors = [m for m in result["messages"] if m.get("type") == "error"]
        self.assertTrue(errors)
        self.assertIn("res.lang", errors[0]["message"])
        self.assertNotIn("No matching record", errors[0]["message"])

    def test_name_create_enabled_uses_the_full_field_path(self):
        result = (
            self.env["res.partner"]
            .with_context(
                import_file=True,
                name_create_enabled_fields={"child_ids/parent_id": True},
            )
            .load(
                ["name", "child_ids/name", "child_ids/parent_id"],
                [["IFLD36 Parent", "IFLD36 Child", "IFLD36 Created By Name"]],
            )
        )
        self.assertFalse(result["messages"])
        self.assertTrue(result["ids"])
        created = self.env["res.partner"].search(
            [("name", "=", "IFLD36 Created By Name")]
        )
        self.assertTrue(created, "the nested reference must have been name_created")

    def test_import_policy_is_a_single_decision(self):
        both = self.converter.with_context(
            import_file=True,
            import_skip_records=["type", "tag_ids", "parent_id"],
            import_set_empty_fields=["type", "tag_ids", "parent_id"],
        )
        partner_fields = self.env["res.partner"]._fields
        self.assertIs(both._str_to_selection(partner_fields["type"], "zzz")[0], SKIP)
        self.assertIs(
            both._str_to_many2many(partner_fields["tag_ids"], [{None: "zzz"}])[0],
            SKIP,
        )
        self.assertIs(
            both._str_to_many2one(partner_fields["parent_id"], [{None: "zzz"}])[0], SKIP
        )

    def test_non_text_reference_is_a_clean_error(self):
        partner_fields = self.env["res.partner"]._fields
        converters = {
            "tag_ids": self.converter._str_to_many2many,
            "child_ids": self.converter._str_to_one2many,
        }
        for fname, convert in converters.items():
            for raw in (12345, ["a", "b"]):
                with self.subTest(field=fname, raw=raw):
                    with self.assertRaises(ValueError) as cm:
                        convert(partner_fields[fname], [{None: raw}])
                    self.assertIn(type(raw).__name__, str(cm.exception.args[0]))

    def test_name_create_enabled_does_not_leak_across_depths(self):
        result = (
            self.env["res.partner"]
            .with_context(
                import_file=True,
                name_create_enabled_fields={"parent_id": True},
            )
            .load(
                ["name", "child_ids/name", "child_ids/parent_id"],
                [["IFLD36b Parent", "IFLD36b Child", "IFLD36b Must Not Exist"]],
            )
        )
        errors = [m for m in result["messages"] if m.get("type") == "error"]
        self.assertTrue(errors, "the nested reference must not resolve")
        self.assertFalse(
            self.env["res.partner"].search([("name", "=", "IFLD36b Must Not Exist")]),
            "a top-level name_create option must not apply to a nested column",
        )

    def test_nested_error_carries_its_own_field_path(self):
        messages = []
        model = self.env["res.partner"].with_context(import_file=True)
        result = model.load(
            ["name", "child_ids/name", "child_ids/type"],
            [["IFLD31 Parent", "IFLD31 Child", "not_a_real_type"]],
        )
        messages = [m for m in result["messages"] if m.get("type") == "error"]
        self.assertTrue(messages)
        self.assertEqual(messages[0].get("field_path"), ["child_ids", "type"])

    def test_many2one_reference_is_stripped_like_many2many(self):
        partner = self.env["res.partner"].create({"name": "IFLD39 Parent"})
        tag = self.env["res.partner.tag"].create({"name": "IFLD39 Tag"})
        fields = self.env["res.partner"]._fields
        for raw in (
            "IFLD39 Parent",
            " IFLD39 Parent",
            "IFLD39 Parent ",
            "\tIFLD39 Parent\n",
        ):
            with self.subTest(raw=raw):
                got, warnings = self.converter._str_to_many2one(
                    fields["parent_id"], [{None: raw}]
                )
                self.assertFalse(warnings)
                self.assertEqual(got, partner.id)
        commands, _w = self.converter._str_to_many2many(
            fields["tag_ids"], [{None: " IFLD39 Tag "}]
        )
        self.assertEqual(commands, [Command.set([tag.id])])

    def test_many2one_reference_accepts_a_raw_database_id(self):
        partner = self.env["res.partner"].create({"name": "IFLD39b Partner"})
        got, warnings = self.converter._str_to_many2one(
            self.env["res.partner"]._fields["parent_id"], [{".id": partner.id}]
        )
        self.assertFalse(warnings)
        self.assertEqual(got, partner.id)

    def test_set_empty_many2one_is_false_not_the_skip_sentinel(self):
        fields = self.env["res.partner"]._fields
        converter = self.converter.with_context(
            import_file=True,
            import_set_empty_fields=["parent_id", "type"],
        )
        got, _w = converter._str_to_many2one(
            fields["parent_id"], [{None: "IFLD40 nope"}]
        )
        self.assertIs(got, False)
        self.assertIs(
            converter._str_to_selection(fields["type"], "IFLD40 nope")[0], False
        )

    def test_skip_record_many2one_returns_the_skip_sentinel(self):
        converter = self.converter.with_context(
            import_file=True, import_skip_records=["parent_id"]
        )
        got, _w = converter._str_to_many2one(
            self.env["res.partner"]._fields["parent_id"], [{None: "IFLD40b nope"}]
        )
        self.assertIs(got, SKIP)

    def test_database_id_possible_values_shows_database_ids(self):
        field = self.env["res.partner"]._fields["parent_id"]
        external = self.converter._prepare_action_possible_values(field, "id")
        self.assertEqual(external["res_model"], "ir.model.data")
        self.assertEqual(external["domain"], [("model", "=", "res.partner")])
        for subfield in (None, ".id"):
            action = self.converter._prepare_action_possible_values(field, subfield)
            self.assertEqual(
                action["res_model"],
                "res.partner",
                "a database id is not an external id: the records ARE the values",
            )
            self.assertNotIn("domain", action)

    def test_unparseable_datetime_is_reported_not_a_server_fault(self):
        with self.assertRaises(ValueError) as cm:
            self.converter._str_to_datetime(self.flds["dt"], "")
        self.assertIn("datetime", str(cm.exception.args[0]))

    def test_malformed_property_definition_is_reported(self):
        field = self.env["res.partner"]._fields["properties"]
        base = {"name": "p1", "string": "P1"}
        cases = {
            "short tags row": dict(base, type="tags", tags=[["a", "A"]], value="a"),
            "short selection row": dict(
                base, type="selection", selection=[["a"]], value="a"
            ),
            "non-text type": dict(base, type=["nonsense"], value=1),
        }
        for label, property_dict in cases.items():
            with self.subTest(case=label):
                with self.assertRaises(ValueError) as cm:
                    self.converter._str_to_properties(field, [property_dict])
                message = str(cm.exception.args[0])
                self.assertNotIn("unpack", message)
                self.assertNotIn("unhashable", message)

    def test_non_numeric_property_value_is_reported(self):
        field = self.env["res.partner"]._fields["properties"]
        base = {"name": "p1", "string": "P1"}
        for property_type, value in (("integer", [1, 2]), ("float", {"a": 1})):
            with self.subTest(type=property_type):
                with self.assertRaises(ValueError) as cm:
                    self.converter._str_to_properties(
                        field, [dict(base, type=property_type, value=value)]
                    )
                self.assertIn("P1", str(cm.exception.args[0]))

    def _define_partner_properties(self, definition):
        record = (
            self.env["properties.base.definition"]
            .sudo()
            ._get_definition_for_property_field("res.partner", "properties")
        )
        record.properties_definition = definition
        self.env.cr.flush()
        self.env.registry.clear_cache()

    def test_unknown_property_comodel_does_not_abort_the_import(self):
        blob = json.dumps(
            [
                {
                    "name": "p",
                    "type": "many2one",
                    "string": "P",
                    "comodel": "no.such.model",
                    "value": [{"id": "base.x"}],
                }
            ]
        )
        model = self.env["res.partner"].with_context(import_file=True)
        result = model.load(
            ["name", "properties"], [["IFLD45 Bad", blob], ["IFLD45 Good", ""]]
        )
        self.assertTrue(result["messages"], "the bad cell must be reported")
        self.assertIn(
            "no.such.model",
            " ".join(m.get("message", "") for m in result["messages"]),
        )

    def test_skip_record_on_a_property_column_skips_the_record(self):
        self._define_partner_properties(
            [{"name": "pb", "type": "boolean", "string": "PB"}]
        )
        model = self.env["res.partner"].with_context(
            import_file=True, import_skip_records=["properties.pb"]
        )
        converted = self.converter.with_context(
            import_file=True, import_skip_records=["properties.pb"]
        )._str_to_properties(
            self.env["res.partner"]._fields["properties"],
            [{"name": "pb", "type": "boolean", "string": "PB", "value": "maybe"}],
        )
        self.assertIs(
            converted[0],
            SKIP,
            "the policy path is `properties.pb`; the converter decides, and the "
            "record it belongs to is dropped by load()",
        )
        result = model.load(["name", "properties.pb"], [["IFLD46 SkipMe", "maybe"]])
        self.assertFalse(result["ids"], "the record must be skipped, not created")
        self.assertFalse(
            self.env["res.partner"].search([("name", "=", "IFLD46 SkipMe")])
        )

    def test_set_empty_property_many2many_does_not_fail_the_import(self):
        self._define_partner_properties(
            [
                {
                    "name": "pm",
                    "type": "many2many",
                    "string": "PM",
                    "comodel": "res.partner.tag",
                }
            ]
        )
        tag = self.env["res.partner.tag"].create({"name": "IFLD47 Tag"})
        model = self.env["res.partner"].with_context(
            import_file=True, import_set_empty_fields=["properties.pm"]
        )
        result = model.load(
            ["name", "properties.pm"], [["IFLD47 Mixed", "IFLD47 Tag,zzz nope zzz"]]
        )
        self.assertFalse(result["messages"])
        self.assertTrue(result["ids"])
        partner = self.env["res.partner"].browse(result["ids"][0])
        self.assertEqual(partner.properties["pm"].ids, [tag.id])

    def test_property_selection_obeys_the_import_policy(self):
        field = self.flds["bool"]
        payload = [
            {
                "name": "sel",
                "type": "selection",
                "string": "Sel",
                "selection": [["a", "A"]],
                "value": "nope",
            }
        ]
        empty = self.converter.with_context(
            import_file=True, import_set_empty_fields=["is_company.sel"]
        )
        self.assertIs(empty._str_to_properties(field, payload)[0][0]["value"], False)

        skip = self.converter.with_context(
            import_file=True, import_skip_records=["is_company.sel"]
        )
        self.assertIs(skip._str_to_properties(field, payload)[0], SKIP)

        with self.assertRaises(ValueError):
            self.converter._str_to_properties(field, payload)

    def test_nested_converter_is_built_once_per_import(self):
        calls = []
        converter_type = type(self.converter)
        original = converter_type._get_converter_record

        def spy(this, model):
            calls.append(model._name)
            return original(this, model)

        rows = [[f"IFLD49 P{i}", f"IFLD49 C{i}"] for i in range(25)]
        with patch.object(converter_type, "_get_converter_record", spy):
            result = self.env["res.partner"].load(["name", "child_ids/name"], rows)
        self.assertFalse(result["messages"])
        self.assertEqual(len(result["ids"]), 25)
        self.assertLessEqual(
            len(calls),
            4,
            "the one2many converter must be reused across records, not rebuilt "
            f"per row (built {len(calls)} times for {len(rows)} records)",
        )

    def test_one2many_payload_is_validated_like_the_others(self):
        with self.assertRaises(ValueError) as cm:
            self.converter._str_to_one2many(
                self.env["res.partner"]._fields["child_ids"], ["notadict"]
            )
        self.assertNotIn("has no attribute", str(cm.exception.args[0]))

    def test_unsupported_field_type_empty_cell_is_not_written(self):
        Definition = self.env["properties.base.definition"]
        field = Definition._fields["properties_definition"]
        self.assertIsNone(self.converter._resolve_converter_field(field))
        convert = self.converter._get_converter_record(Definition)
        logged = []
        result = convert({"properties_definition": ""}, lambda f, exc: logged.append(f))
        self.assertEqual(
            result, {}, "an empty cell of an unsupported column must not write False"
        )
        self.assertEqual(logged, ["properties_definition"])

    def test_property_datetime_and_date_go_through_the_column_converters(self):
        self._define_partner_properties(
            [
                {"name": "pdt", "type": "datetime", "string": "PDT"},
                {"name": "pd", "type": "date", "string": "PD"},
            ]
        )
        model = self.env["res.partner"].with_context(
            import_file=True, tz="America/Mexico_City"
        )
        result = model.load(
            ["name", "properties.pdt"], [["IFLD95 dt", "2026-01-15 10:00:00"]]
        )
        self.assertFalse(result["messages"])
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT properties FROM res_partner WHERE id = %s", [result["ids"][0]]
        )
        self.assertEqual(
            self.env.cr.fetchone()[0]["pdt"],
            "2026-01-15 16:00:00",
            "a naive datetime property is localized like a datetime column",
        )
        result = model.load(["name", "properties.pd"], [["IFLD95 bad", "2026-13-45"]])
        self.assertFalse(result["ids"])
        [message] = result["messages"]
        self.assertIn("valid date", message["message"])
        self.assertIn("PD", message["message"])

    def test_a_datetime_property_round_trips_through_export_and_import(self):
        self._define_partner_properties(
            [{"name": "pdt", "type": "datetime", "string": "PDT"}]
        )
        Partner = self.env["res.partner"].with_context(tz="America/Mexico_City")
        source = Partner.create(
            {"name": "IFLD95 rt", "properties": {"pdt": "2026-01-15 16:00:00"}}
        )
        [row] = source.export_data(["name", "properties.pdt"])["datas"]
        self.assertEqual(
            str(row[1]),
            "2026-01-15 10:00:00",
            "a datetime property exports in the user's timezone like a column",
        )
        result = Partner.with_context(import_file=True).load(
            ["name", "properties.pdt"], [["IFLD95 rt copy", str(row[1])]]
        )
        self.assertFalse(result["messages"])
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT properties FROM res_partner WHERE id = %s", [result["ids"][0]]
        )
        self.assertEqual(self.env.cr.fetchone()[0]["pdt"], "2026-01-15 16:00:00")

    def test_property_tags_are_split_like_a_many2many_column(self):
        self._define_partner_properties(
            [
                {
                    "name": "pt",
                    "type": "tags",
                    "string": "PT",
                    "tags": [["a", "Alpha", 1], ["b", "Beta", 2]],
                }
            ]
        )
        model = self.env["res.partner"].with_context(import_file=True)
        result = model.load(
            ["name", "properties.pt"], [["IFLD95 tags", "Alpha, beta,"]]
        )
        self.assertFalse(result["messages"])
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT properties FROM res_partner WHERE id = %s", [result["ids"][0]]
        )
        self.assertEqual(self.env.cr.fetchone()[0]["pt"], ["a", "b"])

    def test_property_selection_matches_labels_case_insensitively(self):
        payload = [
            {
                "name": "sel",
                "type": "selection",
                "string": "Sel",
                "selection": [["a", "Alpha"]],
                "value": "ALPHA ",
            }
        ]
        converted, _w = self.converter._str_to_properties(self.flds["bool"], payload)
        self.assertEqual(converted[0]["value"], "a")

    def test_property_choice_value_outranks_another_items_label(self):
        payload = [
            {
                "name": "sel",
                "type": "selection",
                "string": "Sel",
                "selection": [["pending", "Sent"], ["sent", "Delivered"]],
                "value": "SENT",
            }
        ]
        converted, _w = self.converter._str_to_properties(self.flds["bool"], payload)
        self.assertEqual(converted[0]["value"], "sent")

    def test_a_model_overriding_name_search_is_not_batched(self):
        Country = self.env["res.country"]
        self.assertFalse(self.converter._is_name_prefetchable(Country))
        self.assertTrue(self.converter._is_name_prefetchable(self.env["res.partner"]))
        mx = Country.search([("code", "=", "MX")], limit=1)
        result = self.env["res.partner"].load(
            ["name", "country_id"], [["IFLD99 a", "MX"], ["IFLD99 b", "MX"]]
        )
        self.assertFalse(result["messages"])
        self.assertEqual(
            self.env["res.partner"].browse(result["ids"]).mapped("country_id"), mx
        )

    def test_a_property_error_names_the_property(self):
        payload = [{"name": "n", "type": "integer", "string": "Count", "value": "x"}]
        with self.assertRaises(ValueError) as cm:
            self.converter._str_to_properties(self.flds["bool"], payload)
        self.assertIn("%(field)s/Count", cm.exception.args[0])

    def test_a_user_error_in_a_lookup_is_reported_not_hidden(self):
        PartnerClass = type(self.env["res.partner"])
        with patch.object(
            PartnerClass,
            "name_search",
            side_effect=AccessError("IFLD95 no read on partners"),
        ):
            result = (
                self.env["res.partner"]
                .with_context(import_file=True)
                .load(["name", "parent_id"], [["IFLD95 child", "Some Parent"]])
            )
        self.assertFalse(result["ids"])
        [message] = result["messages"]
        self.assertIn("IFLD95 no read on partners", message["message"])
        self.assertNotIn("server logs", message["message"])

    def test_o2m_child_with_a_blank_database_id_creates_nothing(self):
        commands, warnings = self.converter._str_to_one2many(
            self.env["res.partner"]._fields["child_ids"], [{".id": "0"}]
        )
        self.assertEqual(commands, [])
        self.assertFalse(warnings)

    def test_non_text_numbers_are_a_clean_error(self):
        partner_fields = self.env["res.partner"]._fields
        with self.assertRaises(ValueError) as cm:
            self.converter._str_to_integer(partner_fields["color"], [1, 2])
        self.assertIn("integer", cm.exception.args[0])
        with self.assertRaises(ValueError) as cm:
            self.converter._str_to_float(partner_fields["partner_latitude"], {"a": 1})
        self.assertIn("number", cm.exception.args[0])


@tagged("post_install", "-at_install")
class TestImportFiles(TransactionCase):
    @unittest.skipUnless(
        can_import("openpyxl"),
        "openpyxl not available",
    )
    def test_import_contacts_template_xls(self):
        if not loaded_demo_data(self.env):
            self.skipTest("Needs demo data to be able to import those files")
        model = "res.partner"
        filename = "contacts_import_template.xlsx"

        file_content = file_open(f"base/static/xls/{filename}", "rb").read()
        import_wizard = self.env["base_import.import"].create(
            {
                "res_model": model,
                "file": file_content,
                "file_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            },
        )

        result = import_wizard.parse_preview(
            {
                "has_headers": True,
            },
        )
        self.assertIsNone(result.get("error"))
        field_names = ["/".join(v) for v in result["matches"].values()]
        results = import_wizard.execute_import(
            field_names,
            [r.lower() for r in result["headers"]],
            {
                "import_skip_records": [],
                "import_set_empty_fields": [],
                "fallback_values": {},
                "name_create_enabled_fields": {},
                "encoding": "",
                "separator": "",
                "quoting": '"',
                "date_format": "",
                "datetime_format": "",
                "float_thousand_separator": ",",
                "float_decimal_separator": ".",
                "advanced": True,
                "has_headers": True,
                "keep_matches": False,
                "limit": 2000,
                "skip": 0,
                "tracking_disable": True,
            },
        )
        self.assertFalse(
            results["messages"],
            "results should be empty on successful import of ",
        )


@tagged("post_install", "-at_install")
class TestSelectionIndexPrecedence(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.converter = cls.env["ir.fields.converter"]

    def _index_for(self, selection):
        field = self.env["res.partner"]._fields["type"]
        cache = self.converter._get_transaction_cache()
        lang = self.converter.env.lang
        cache.pop(("selection_index", field.model_name, field.name, lang), None)
        with patch.object(
            type(self.converter),
            "_get_selection_and_labels",
            lambda _self, _field: (selection, {}),
        ):
            return self.converter._get_selection_index(field)

    def test_a_value_is_never_shadowed_by_another_items_label(self):
        index = self._index_for([("pending", "Sent"), ("sent", "Delivered")])
        self.assertEqual(index["sent"], "sent", "the raw value must win the token")
        self.assertEqual(index["delivered"], "sent")

    def test_every_raw_value_round_trips_on_every_live_selection(self):
        broken = []
        for model_name in self.env.registry.models:
            model = self.env[model_name]
            for fname, field in model._fields.items():
                if field.type != "selection":
                    continue
                with contextlib.suppress(Exception):
                    selection = [
                        (value, label)
                        for value, label in field._description_selection(self.env)
                        if isinstance(value, str) and isinstance(label, str)
                    ]
                    if not selection:
                        continue
                    index = self.converter._get_selection_index(field)
                    broken += [
                        (model_name, fname, value)
                        for value, _label in selection
                        if value and index.get(value.lower()) != value
                    ]
        self.assertFalse(
            broken, f"selection values that import as a different value: {broken}"
        )

    def test_the_stored_value_survives_a_real_load(self):
        if "mail.notification" not in self.env:
            self.skipTest("mail is not installed")
        partner = self.env["res.partner"].create({"name": "IFLD-SEL owner"})
        message = self.env["mail.message"].create(
            {"model": "res.partner", "res_id": partner.id, "body": "x"}
        )
        self.env.flush_all()
        result = self.env["mail.notification"].load(
            [
                "mail_message_id/.id",
                "res_partner_id/.id",
                "notification_type",
                "notification_status",
            ],
            [[str(message.id), str(partner.id), "email", "sent"]],
        )
        self.assertFalse(result["messages"])
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT notification_status FROM mail_notification WHERE id = %s",
            [result["ids"][0]],
        )
        self.assertEqual(self.env.cr.fetchone()[0], "sent")

    def test_the_error_lists_possible_values_in_the_readers_language(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        field = self.env["res.partner"]._fields["type"]
        french = self.converter.with_context(lang="fr_FR")
        _index, labels = french._get_selection_index_and_labels(field)
        source = dict(french._get_selection_and_labels(field)[0])
        translated = {
            label for item, label in labels.items() if label != source.get(item)
        }
        if not translated:
            self.skipTest("no translated selection labels on this build")
        with self.assertRaises(ValueError) as caught:
            french._str_to_selection(field, "pas une valeur")
        offered = set(caught.exception.args[1]["moreinfo"])
        self.assertTrue(
            offered & translated,
            f"a French message must offer French values, got {offered}",
        )


@tagged("post_install", "-at_install")
class TestConverterContracts(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.converter = cls.env["ir.fields.converter"]

    def test_json_null_is_a_value_not_the_skip_sentinel(self):
        field = self.env["ir.module.module"]._fields["data_file_checksums"]
        value, _warnings = self.converter._str_to_json(field, "null")
        self.assertIsNone(value)
        self.assertIsNot(value, SKIP, "a JSON null must not skip the record")

    def test_a_json_null_row_is_imported_not_silently_dropped(self):
        module = self.env["ir.module.module"].search([("name", "=", "base")], limit=1)
        self.assertTrue(module)
        result = (
            self.env["ir.module.module"]
            .with_context(import_file=True, import_skip_records=["data_file_checksums"])
            .load(["id", "data_file_checksums"], [["base.module_base", "null"]])
        )
        self.assertFalse(result["messages"])
        self.assertEqual(
            len(result["ids"] or []),
            1,
            "a JSON null used to look like the skip sentinel and dropped the row",
        )

    def test_an_empty_reference_record_is_reported_not_a_server_fault(self):
        convert = self.converter.with_context(import_file=True)._get_converter_record(
            self.env["res.partner"]
        )
        logged = []
        result = convert({"parent_id": [{}]}, lambda f, e: logged.append((f, e)))
        self.assertEqual(result, {})
        self.assertEqual([f for f, _e in logged], ["parent_id"])
        self.assertIsInstance(logged[0][1], ValueError)

    def test_an_unexpected_converter_failure_is_reported_not_raised(self):
        def boom(_value):
            raise KeyError("not one of the six")

        with patch.object(
            type(self.converter),
            "_resolve_converter_field",
            lambda *a, **kw: boom,
        ):
            convert = self.converter._get_converter_record(self.env["res.partner"])
            logged = []
            result = convert({"name": "x"}, lambda f, e: logged.append((f, e)))
        self.assertEqual(result, {})
        self.assertEqual([f for f, _e in logged], ["name"])
        self.assertIsInstance(logged[0][1], ValueError)

    def test_an_infrastructure_error_still_propagates(self):
        def boom(_value):
            raise psycopg.OperationalError("connection gone")

        with patch.object(
            type(self.converter),
            "_resolve_converter_field",
            lambda *a, **kw: boom,
        ):
            convert = self.converter._get_converter_record(self.env["res.partner"])
            with self.assertRaises(psycopg.OperationalError):
                convert({"name": "x"}, lambda f, e: None)

    def test_char_import_honours_the_field_trim_attribute(self):
        partner_fields = self.env["res.partner"]._fields
        self.assertTrue(partner_fields["name"].trim)
        value, _w = self.converter._str_to_str(partner_fields["name"], "  Acme  ")
        self.assertEqual(value, "Acme")
        comment = partner_fields["comment"]
        untrimmed, _w = self.converter._str_to_str(comment, "  kept  ")
        self.assertEqual(
            untrimmed, "  kept  ", "only Char declares trim; Text must be left alone"
        )

    def test_a_loaded_name_is_trimmed_like_the_wizard_trims_it(self):
        result = self.env["res.partner"].load(["name"], [["  IFLD-TRIM Co  "]])
        self.assertFalse(result["messages"])
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT name FROM res_partner WHERE id = %s", [result["ids"][0]]
        )
        self.assertEqual(self.env.cr.fetchone()[0], "IFLD-TRIM Co")

    def test_numbers_do_not_accept_python_literal_grammar(self):
        partner_fields = self.env["res.partner"]._fields
        for value in ("1_0", "1_000"):
            with self.assertRaises(ValueError, msg=value):
                self.converter._str_to_integer(partner_fields["color"], value)
            with self.assertRaises(ValueError, msg=value):
                self.converter._str_to_float(partner_fields["partner_latitude"], value)
        self.assertEqual(
            self.converter._str_to_integer(partner_fields["color"], " 12 ")[0], 12
        )

    def test_every_property_type_obeys_the_import_policy(self):
        field = self.env["res.partner"]._fields["is_company"]
        payloads = {
            "integer": {"name": "n", "type": "integer", "string": "N", "value": "x"},
            "float": {"name": "n", "type": "float", "string": "N", "value": "x"},
            "tags": {
                "name": "n",
                "type": "tags",
                "string": "N",
                "tags": [["a", "A", 1]],
                "value": ["nope"],
            },
        }
        for kind, payload in payloads.items():
            with self.subTest(kind=kind):
                with self.assertRaises(ValueError):
                    self.converter._str_to_properties(field, [payload])
                skipping = self.converter.with_context(
                    import_file=True, import_skip_records=["is_company.n"]
                )
                self.assertIs(
                    skipping._str_to_properties(field, [payload])[0],
                    SKIP,
                    f"a bad {kind} property must obey the skip policy",
                )
                emptying = self.converter.with_context(
                    import_file=True, import_set_empty_fields=["is_company.n"]
                )
                self.assertIs(
                    emptying._str_to_properties(field, [payload])[0][0]["value"], False
                )

    def test_a_non_finite_property_float_is_refused_like_the_column(self):
        field = self.env["res.partner"]._fields["is_company"]
        for raw in ("nan", "inf", "-inf"):
            payload = {"name": "n", "type": "float", "string": "N", "value": raw}
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    self.converter._str_to_properties(field, [payload])
                emptying = self.converter.with_context(
                    import_file=True, import_set_empty_fields=["is_company.n"]
                )
                self.assertIs(
                    emptying._str_to_properties(field, [payload])[0][0]["value"], False
                )

    def test_the_boolean_vocabulary_is_derived_from_the_extraction_anchors(self):
        from odoo.addons.base.models.ir_fields import (
            BOOLEAN_FALSE_TERMS,
            BOOLEAN_TRANSLATIONS,
            BOOLEAN_TRUE_TERMS,
        )

        self.assertEqual(
            {term._source for term in BOOLEAN_TRUE_TERMS + BOOLEAN_FALSE_TERMS},
            {term._source for term in BOOLEAN_TRANSLATIONS},
            "the extraction anchors and the vocabulary must not drift apart",
        )
        trues, falses = self.converter._get_boolean_tokens()
        for term in BOOLEAN_TRUE_TERMS:
            self.assertIn(term._source, trues)
        for term in BOOLEAN_FALSE_TERMS:
            self.assertIn(term._source, falses)
