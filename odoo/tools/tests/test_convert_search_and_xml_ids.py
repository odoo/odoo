import typing
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from lxml import etree

from odoo.tools import convert
from odoo.tools.convert import _eval_xml, xml_import


class _Records(list):
    rows: dict = {}

    @property
    def ids(self):
        return list(self)

    def mapped(self, _name):
        return list(self)

    def read(self, fields):
        return [{name: self.rows[rid][name] for name in fields} for rid in self]


class _Model:
    def __init__(self, env, name, fields=()):
        self.env = env
        self.name = name
        self._fields = {field: SimpleNamespace(type=kind) for field, kind in fields}

    def search(self, domain):
        self.env.searches.append((self.name, domain))
        if self.name == "ir.module.module":
            return _Records(self.env.installed)
        return self.env.found.get(self.name, _Records())

    def browse(self, ids):
        return ids


class _Env(dict):
    context: dict = {}

    def __init__(self, found=None, fields=None, installed=(), rows=None):
        super().__init__()
        self.found = {model: _Records(ids) for model, ids in (found or {}).items()}
        for records in self.found.values():
            records.rows = rows or {}
        self.searches = []
        self.installed = list(installed)
        self.fields = fields or {}

    def __getitem__(self, model):
        return _Model(self, model, self.fields.get(model, ()))


def _importer(env, module="probe"):
    importer = xml_import.__new__(xml_import)
    importer.module = module
    importer.envs = [env]
    importer.idref = {}
    importer._installed_modules = None
    return importer


def _evaluated(env: typing.Any, node: etree._Element) -> typing.Any:
    return _eval_xml(_importer(env), node, env)


class TestOneSearchForFieldsAndValues(unittest.TestCase):
    def test_a_many2many_field_sets_every_match(self):
        env = _Env(
            found={"res.groups": [4, 5]},
            fields={"res.users": [("group_ids", "many2many")]},
        )
        value = _importer(env)._eval_field_search(
            env, "res.users", "group_ids", "res.groups", "[('id', '>', 3)]", "id"
        )
        self.assertEqual(value, [(6, 0, [4, 5])])

    def test_a_many2one_field_takes_the_first_match(self):
        env = _Env(
            found={"res.partner": [7, 8]},
            fields={"res.users": [("partner_id", "many2one")]},
        )
        value = _importer(env)._eval_field_search(
            env, "res.users", "partner_id", "res.partner", "[]", "id"
        )
        self.assertEqual(value, 7)

    def test_a_value_whose_name_is_a_many2many_of_the_searched_model_is_a_value(self):
        env = _Env(
            found={"res.groups": [4, 5]},
            fields={"res.groups": [("implied_ids", "many2many")]},
        )
        node = etree.fromstring(
            '<value name="implied_ids" model="res.groups" search="[]"/>'
        )
        with self.assertLogs("odoo.tools.convert", "WARNING") as logs:
            self.assertEqual(_evaluated(env, node), 4)
        self.assertIn("matches 2 records", logs.output[0])

    def test_a_value_matching_nothing_is_false(self):
        env = _Env()
        node = etree.fromstring('<value model="res.groups" search="[]"/>')
        self.assertIs(_evaluated(env, node), False)

    def test_a_value_with_use_stands_for_that_column_of_its_match(self):
        env = _Env(found={"link.tracker.code": [3]}, rows={3: {"code": "a1b2"}})
        node = etree.fromstring(
            '<value model="link.tracker.code" search="[]" use="code"/>'
        )
        self.assertEqual(_evaluated(env, node), "a1b2")

    def test_a_field_with_use_reads_that_column_of_every_match(self):
        env = _Env(
            found={"res.users": [2, 6]},
            fields={"res.groups": [("user_ids", "many2many")]},
            rows={2: {"partner_id": (12, "A")}, 6: {"partner_id": (16, "B")}},
        )
        value = _importer(env)._eval_field_search(
            env, "res.groups", "user_ids", "res.users", "[]", "partner_id"
        )
        self.assertEqual(value, [(6, 0, [12, 16])])

    def test_the_grammar_accepts_use_on_a_searched_value_and_field(self):
        grammar = etree.RelaxNG(
            etree.parse(str(Path(convert.__file__).parent.parent / "import_xml.rng"))
        )
        doc = etree.fromstring(
            '<odoo><function model="link.tracker.click" name="add_click">'
            '<value model="link.tracker.code" search="[]" use="code"/>'
            '</function><record id="x" model="res.groups">'
            '<field name="user_ids" model="res.users" search="[]" use="id"/>'
            "</record></odoo>"
        )
        self.assertTrue(grammar.validate(doc), grammar.error_log)

    def test_the_mass_mailing_demo_traces_fit_the_grammar(self):
        root = Path(convert.__file__).parents[2]
        grammar = etree.RelaxNG(etree.parse(str(root / "odoo" / "import_xml.rng")))
        for module in ("mass_mailing", "mass_mailing_sms"):
            with self.subTest(module=module):
                trace = root / "addons" / module / "demo" / "mailing_trace.xml"
                self.assertTrue(
                    grammar.validate(etree.parse(str(trace))), grammar.error_log
                )


class TestXmlIdReferences(unittest.TestCase):
    def test_a_second_dot_is_refused_with_a_value_error(self):
        with self.assertRaisesRegex(ValueError, "at most one dot"):
            _importer(_Env())._test_xml_id("base.a.b")

    def test_an_uninstalled_module_is_refused_with_a_value_error(self):
        with self.assertRaisesRegex(ValueError, "uninstalled module"):
            _importer(_Env(installed=["base"]))._test_xml_id("sale.order_1")

    def test_the_installed_modules_are_read_once_per_file(self):
        env = _Env(installed=["base", "mail"])
        importer = _importer(env)
        for xml_id in ("base.a", "mail.b", "base.c", "probe.d", "e"):
            importer._test_xml_id(xml_id)
        self.assertEqual(
            env.searches, [("ir.module.module", [("state", "=", "installed")])]
        )


class TestConvertFileRefusal(unittest.TestCase):
    def test_an_unknown_extension_names_the_file_in_its_message(self):
        with (
            mock.patch.object(convert, "file_open", mock.mock_open(read_data=b"")),
            self.assertRaises(ValueError) as caught,
        ):
            convert.convert_file(
                typing.cast("typing.Any", None), "probe", "data/probe.yaml", None
            )
        self.assertEqual(
            caught.exception.args, ("Can't load unknown file type data/probe.yaml.",)
        )


if __name__ == "__main__":
    unittest.main()
