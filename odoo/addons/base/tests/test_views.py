import logging
import os
import pathlib
import re
import tempfile
import time
from collections import defaultdict
from contextlib import contextmanager
from unittest.mock import patch

from lxml import etree
from lxml.builder import E
from markupsafe import Markup
from psycopg import IntegrityError
from psycopg.types.json import Json

from odoo import Command, api
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.fields import Domain
from odoo.tests import common, tagged
from odoo.tests.common import get_cache_key_counter
from odoo.tools import mute_logger, safe_eval, view_validation

from odoo.addons.base.models import ir_ui_view, ir_ui_view_arch
from odoo.addons.base.models.ir_ui_view_arch import ELEMENT_HANDLERS
from odoo.addons.base.tests.common import TransactionCaseWithUserDemo

_logger = logging.getLogger(__name__)


class ViewXMLID(common.TransactionCase):
    def test_model_data_id(self):
        view = self.env.ref("base.view_company_form")
        self.assertTrue(view)
        self.assertTrue(view.model_data_id)
        self.assertEqual(view.model_data_id.complete_name, "base.view_company_form")
        self.assertEqual(view.xml_id, "base.view_company_form")


class ViewCase(TransactionCaseWithUserDemo):
    def setUp(self):
        super().setUp()
        self.View = self.env["ir.ui.view"]

    def assertValid(
        self, arch, name="valid view", inherit_id=False, model="ir.ui.view"
    ):
        return self.View.create(
            {
                "name": name,
                "model": model,
                "inherit_id": inherit_id,
                "arch": arch,
            }
        )

    def assertInvalid(
        self,
        arch,
        expected_message=None,
        name="invalid view",
        inherit_id=False,
        model="ir.ui.view",
    ):
        with mute_logger("odoo.addons.base.models.ir_ui_view"):
            with self.assertRaises(ValidationError) as catcher:
                self.View.create(
                    {
                        "name": name,
                        "model": model,
                        "inherit_id": inherit_id,
                        "arch": arch,
                    }
                )
        message = str(catcher.exception.args[0])
        self.assertEqual(catcher.exception.context["name"], name)
        if expected_message:
            self.assertIn(expected_message, message)
        else:
            _logger.warning(message)

    def assertWarning(
        self,
        arch,
        expected_message=None,
        name="invalid view",
        model="ir.ui.view",
    ):
        with self.assertLogs(
            "odoo.addons.base.models.ir_ui_view", level="WARNING"
        ) as log_catcher:
            self.View.create(
                {
                    "name": name,
                    "model": model,
                    "arch": arch,
                }
            )
        self.assertEqual(
            len(log_catcher.output), 1, "Exactly one warning should be logged"
        )
        message = log_catcher.output[0]
        self.assertIn("View error context", message)
        self.assertIn("'name': '%s'" % name, message)
        if expected_message:
            self.assertIn(expected_message, message)


class TestNodeLocator(common.TransactionCase):
    def test_no_match_xpath(self):
        node = self.env["ir.ui.view"].locate_node(
            E.root(E.foo(), E.bar(), E.baz()),
            E.xpath(expr="//qux"),
        )
        self.assertIsNone(node)

    def test_match_xpath(self):
        bar = E.bar()
        node = self.env["ir.ui.view"].locate_node(
            E.root(E.foo(), bar, E.baz()),
            E.xpath(expr="//bar"),
        )
        self.assertIs(node, bar)

    def test_no_match_field(self):
        node = self.env["ir.ui.view"].locate_node(
            E.root(E.foo(), E.bar(), E.baz()),
            E.field(name="qux"),
        )
        self.assertIsNone(node)

        node = self.env["ir.ui.view"].locate_node(
            E.root(E.field(name="foo"), E.field(name="bar"), E.field(name="baz")),
            E.field(name="qux"),
        )
        self.assertIsNone(node)

    def test_match_field(self):
        bar = E.field(name="bar")
        node = self.env["ir.ui.view"].locate_node(
            E.root(E.field(name="foo"), bar, E.field(name="baz")),
            E.field(name="bar"),
        )
        self.assertIs(node, bar)

    def test_no_match_other(self):
        node = self.env["ir.ui.view"].locate_node(
            E.root(E.foo(), E.bar(), E.baz()),
            E.qux(),
        )
        self.assertIsNone(node)

    def test_match_other(self):
        bar = E.bar()
        node = self.env["ir.ui.view"].locate_node(
            E.root(E.foo(), bar, E.baz()),
            E.bar(),
        )
        self.assertIs(bar, node)

    def test_attribute_mismatch(self):
        node = self.env["ir.ui.view"].locate_node(
            E.root(E.foo(attr="1"), E.bar(attr="2"), E.baz(attr="3")),
            E.bar(attr="5"),
        )
        self.assertIsNone(node)

    def test_attribute_filter(self):
        match = E.bar(attr="2")
        node = self.env["ir.ui.view"].locate_node(
            E.root(E.bar(attr="1"), match, E.root(E.bar(attr="3"))),
            E.bar(attr="2"),
        )
        self.assertIs(node, match)

    def test_version_mismatch(self):
        node = self.env["ir.ui.view"].locate_node(
            E.root(E.foo(attr="1"), version="4"),
            E.foo(attr="1", version="3"),
        )
        self.assertIsNone(node)


class TestViewInheritance(ViewCase):
    def arch_for(self, name, view_type="form", parent=None):
        if not parent:
            element = E(view_type, string=name)
        else:
            element = E(
                view_type,
                E.attribute(name, name="string"),
                position="attributes",
            )
        return etree.tostring(element, encoding="unicode")

    def makeView(self, name, parent=None, arch=None):
        view = self.View.create(
            {
                "model": self.model,
                "name": name,
                "arch": arch or self.arch_for(name, parent=parent),
                "inherit_id": parent,
                "priority": 5,
            }
        )
        self.view_ids[name] = view
        return view

    def get_views(self, names):
        return self.View.concat(*(self.view_ids[name] for name in names))

    def setUp(self):
        super().setUp()

        self.patch(self.registry, "ready", True)

        self.model = "ir.ui.view.custom"
        self.view_ids = {}

        self.a = self.makeView("A")
        self.a1 = self.makeView("A1", self.a.id)
        self.a2 = self.makeView("A2", self.a.id)
        self.a11 = self.makeView("A11", self.a1.id)
        self.a11.mode = "primary"
        self.makeView("A111", self.a11.id)
        self.makeView("A12", self.a1.id)
        self.makeView("A21", self.a2.id)
        self.a22 = self.makeView("A22", self.a2.id)
        self.makeView("A221", self.a22.id)

        self.b = self.makeView("B", arch=self.arch_for("B", "list"))
        self.makeView("B1", self.b.id, arch=self.arch_for("B1", "list", parent=self.b))
        self.c = self.makeView("C", arch=self.arch_for("C", "list"))
        self.c.write({"priority": 1})

        self.d = self.makeView("D")
        self.d1 = self.makeView("D1", self.d.id)
        self.d1.arch = None

    def test_get_inheriting_views(self):
        self.assertEqual(
            self.view_ids["A"]._get_views_inheriting(),
            self.get_views(["A", "A1", "A2", "A12", "A21", "A22", "A221"]),
        )
        self.assertEqual(
            self.view_ids["A21"]._get_views_inheriting(),
            self.get_views(["A21"]),
        )
        self.assertEqual(
            self.view_ids["A11"]._get_views_inheriting(),
            self.get_views(["A11", "A111"]),
        )
        self.assertEqual(
            (self.view_ids["A11"] + self.view_ids["A"])._get_views_inheriting(),
            self.get_views(
                ["A", "A1", "A2", "A11", "A111", "A12", "A21", "A22", "A221"]
            ),
        )

    def test_default_view(self):
        default = self.View.default_view(model=self.model, view_type="form")
        self.assertEqual(default, self.view_ids["A"].id)

        default_list = self.View.default_view(model=self.model, view_type="list")
        self.assertEqual(default_list, self.view_ids["C"].id)

    def test_no_default_view(self):
        self.assertFalse(
            self.View.default_view(model="no_model.exist", view_type="form")
        )
        self.assertFalse(self.View.default_view(model=self.model, view_type="graph"))

    def test_no_recursion(self):
        r1 = self.makeView("R1")
        with self.assertRaises(ValidationError):
            r1.write({"inherit_id": r1.id})

        r2 = self.makeView("R2", r1.id)
        r3 = self.makeView("R3", r2.id)
        with self.assertRaises(ValidationError):
            r2.write({"inherit_id": r3.id})

        with self.assertRaises(ValidationError):
            r1.write({"inherit_id": r3.id})

        with self.assertRaises(ValidationError):
            r1.write(
                {
                    "inherit_id": r1.id,
                    "arch": self.arch_for("itself", parent=True),
                }
            )

    def test_write_arch(self):
        self.env["res.lang"]._activate_lang("fr_FR")

        v = self.makeView("T", arch='<form string="Foo">Bar</form>')
        v.update_field_translations(
            "arch_db", {"fr_FR": {"Foo": "Fou", "Bar": "Barre"}}
        )
        self.assertEqual(v.arch, '<form string="Foo">Bar</form>')

        v.arch = "<form/>"
        self.assertEqual(v.arch, "<form/>")

    def test_get_combined_arch_query_count(self):
        self.env.invalidate_all()
        with self.assertQueryCount(2):
            self.view_ids["A"].get_combined_arch()

    def test_view_validate_button_action_query_count(self):
        _, _, counter = get_cache_key_counter(
            self.env["ir.model.data"]._xmlid_target, "base.action_ui_view"
        )
        hit, miss = counter.hit, counter.miss

        with self.assertQueryCount(9):
            base_view = self.assertValid("""
                <form string="View">
                    <header>
                        <button type="action" name="base.action_ui_view"/>
                        <button type="action" name="base.action_ui_view_custom"/>
                        <button type="action" name="base.action_ui_view"/>
                    </header>
                    <field name="name"/>
                </form>
            """)
        self.assertEqual(counter.hit, hit)
        self.assertEqual(counter.miss, miss + 2)

        with self.assertQueryCount(4):
            self.assertValid(
                """
                <field name="name" position="replace"/>
            """,
                inherit_id=base_view.id,
            )
        self.assertEqual(counter.hit, hit + 2)
        self.assertEqual(counter.miss, miss + 2)

    def test_view_validate_attrs_groups_query_count(self):
        _, _, counter = get_cache_key_counter(
            self.env["ir.model.data"]._xmlid_target, "base.group_system"
        )
        hit, miss = counter.hit, counter.miss

        with self.assertQueryCount(6):
            base_view = self.assertValid("""
                <form string="View">
                    <field name="name" groups="base.group_system"/>
                    <field name="priority" groups="base.group_system"/>
                    <field name="inherit_id" groups="base.group_system"/>
                </form>
            """)
        self.assertEqual(counter.hit, hit)
        self.assertEqual(counter.miss, miss)

        with self.assertQueryCount(3):
            self.assertValid(
                """
                <field name="name" position="replace">
                    <field name="key" groups="base.group_system"/>
                </field>
            """,
                inherit_id=base_view.id,
            )
        self.assertEqual(counter.hit, hit)
        self.assertEqual(counter.miss, miss)

    def test_infer_type_from_arch_db(self):
        for view_type in ("form", "list", "search"):
            with self.subTest(view_type=view_type):
                view = self.View.create(
                    {
                        "name": f"arch_db_{view_type}",
                        "model": "res.partner",
                        "arch_db": f'<{view_type}><field name="name"/></{view_type}>',
                    }
                )
                _logger.debug(
                    "Inferred %s from arch_db for view %s", view.type, view.id
                )
                self.assertEqual(view.type, view_type)

    def test_no_arch(self):
        self.d1._check_xml()

    def test_invalid_locators(self):
        base_view_arch = """
            <form string="View">
                <div name="div1">
                    <field name="id"/>
                </div>
            </form>
        """
        base_view = self.makeView("invalid_xpath_base_view", arch=base_view_arch)

        child_view_arch = """
        <data>
            <xpath expr="//form/div[1]/div[1]" position="attributes">
                <attribute name='string'>Invalid Div</attribute>
            </xpath>
            <field name="invalid_field" position="after">
                <field name="inherit_id"/>
            </field>
            <xpath expr="//form/div[1]" position="inside">
                <xpath expr="//field[@name='invalid_field']" position="move"/>
            </xpath>
        </data>
        """

        child_view = self.View.create(
            {
                "model": self.model,
                "name": "child_view",
                "arch": child_view_arch,
                "inherit_id": base_view.id,
                "priority": 10,
                "active": False,
            }
        )

        child_primary_no_arch = self.View.create(
            {
                "model": self.model,
                "name": "child_view",
                "inherit_id": base_view.id,
                "priority": 18,
                "active": False,
            }
        )

        self.assertEqual(
            child_view.invalid_locators,
            [
                {
                    "tag": "xpath",
                    "attrib": {
                        "expr": "//form/div[1]/div[1]",
                        "position": "attributes",
                    },
                    "sourceline": 2,
                },
                {
                    "tag": "field",
                    "attrib": {"name": "invalid_field", "position": "after"},
                    "sourceline": 5,
                },
                {
                    "tag": "xpath",
                    "attrib": {
                        "expr": "//field[@name='invalid_field']",
                        "position": "move",
                    },
                    "sourceline": 9,
                },
            ],
        )

        self.assertEqual(child_primary_no_arch.invalid_locators, False)

    def test_invalid_locators_survive_a_malformed_move_xpath(self):
        base_view = self.makeView(
            "malformed_move_base", arch="<form><field name='id'/></form>"
        )
        child = self.View.create(
            {
                "model": self.model,
                "name": "malformed_move_child",
                "inherit_id": base_view.id,
                "active": False,
                "priority": 12,
                "arch": (
                    '<xpath expr="//field[@name=\'id\']" position="after">'
                    '<xpath expr="//field[@name=" position="move"/></xpath>'
                ),
            }
        )
        self.assertEqual(
            child.invalid_locators,
            [
                {
                    "tag": "xpath",
                    "attrib": {"expr": "//field[@name=", "position": "move"},
                    "sourceline": 1,
                }
            ],
        )

    def test_invalid_locators_with_valid_xpath(self):
        base_view_arch = """
            <form string="View">
                <div name="div1">
                    <field name="id"/>
                </div>
            </form>
        """
        base_view = self.makeView("invalid_xpath_base_view", arch=base_view_arch)

        child_view_arch = """
        <data>
            <xpath expr="//form/div[1]" position="attributes">
                <attribute name='string'>Valid</attribute>
            </xpath>
            <field name="id" position="after">
                <field name="ref_id"/>
            </field>
            <xpath expr="//div[hasclass('parasite')]" position="inside" >
                <div class="fails" />
            </xpath>
        </data>
        """

        child_view = self.View.create(
            {
                "model": self.model,
                "name": "child_view",
                "arch": child_view_arch,
                "inherit_id": base_view.id,
                "priority": 10,
                "active": False,
            }
        )

        child_applied = self.View.create(
            {
                "model": self.model,
                "name": "child_view",
                "arch": """<data>
                <!-- One comment: should be ignored -->
                <field name="id" position="before">
                    <div class="parasite" />
                </field>
                </data>""",
                "inherit_id": base_view.id,
                "priority": 10,
                "active": True,
            }
        )

        child_view_arch2 = """
        <data>
            <xpath expr="//div[hasclass('parasite')]" position="inside">
                <div class="not_fails"/>
            </xpath>
            <field name="user_id" position="after">
                <div class="fails" />
            </field>
        </data>
        """

        child_view2 = self.View.create(
            {
                "model": self.model,
                "name": "child_view",
                "arch": child_view_arch2,
                "inherit_id": base_view.id,
                "priority": 10,
                "active": False,
            }
        )

        child_view3 = self.View.create(
            {
                "model": self.model,
                "name": "child_view",
                "arch": """<data>
                        <xpath expr="//div[hasclass('parasite')]" position="inside" >
                            <div class="invalid" />
                        </xpath>
                    </data>""",
                "inherit_id": base_view.id,
                "priority": 7,
                "active": False,
            }
        )

        child_view4 = self.View.create(
            {
                "model": self.model,
                "name": "child_view",
                "arch": """<data>
                        <xpath expr="//div[hasclass('parasite')]" position="inside" >
                            <div class="valid" />
                        </xpath>
                    </data>""",
                "inherit_id": child_applied.id,
                "priority": 5,
                "active": True,
            }
        )

        actual_queries = []
        with contextmanager(lambda: self._patchExecute(actual_queries))():
            self.assertEqual(child_applied.invalid_locators, False)
        self.assertTrue(len(actual_queries) > 0)

        re_sql_update = re.compile(r"\bupdate\b", re.IGNORECASE)
        self.assertFalse(any(re_sql_update.search(q) for q in actual_queries))

        self.assertEqual(
            child_view.invalid_locators,
            [
                {
                    "tag": "xpath",
                    "attrib": {
                        "expr": "//div[hasclass('parasite')]",
                        "position": "inside",
                    },
                    "sourceline": 8,
                }
            ],
        )
        self.assertEqual(
            child_view2.invalid_locators,
            [
                {
                    "tag": "field",
                    "attrib": {"name": "user_id", "position": "after"},
                    "sourceline": 5,
                }
            ],
        )
        self.assertEqual(
            child_view3.invalid_locators,
            [
                {
                    "tag": "xpath",
                    "attrib": {
                        "expr": "//div[hasclass('parasite')]",
                        "position": "inside",
                    },
                    "sourceline": 2,
                }
            ],
        )
        self.assertEqual(child_view4.invalid_locators, False)

    def test_nested_move_invalid_locator(self):
        base_view_arch = """
            <form string="View">
                <div name="div1">
                    <div>
                        <span />
                    </div>
                </div>
            </form>
        """
        base_view = self.makeView("invalid_xpath_base_view", arch=base_view_arch)

        child_view = self.View.create(
            {
                "model": self.model,
                "name": "child_view",
                "inherit_id": base_view.id,
                "priority": 10,
                "active": False,
                "arch": """
            <data>
                <xpath expr="/form/div/div" position="replace">
                    <xpath expr="/form/div/div/span" position="move" />
                </xpath>
            </data>
            """,
            }
        )
        self.assertEqual(child_view.invalid_locators, False)

        child_view.arch = """
            <data>
                <xpath expr="/form/div/div" position="replace">
                    <xpath expr="/form/div/div/h1" position="move" />
                </xpath>
            </data>"""
        self.assertEqual(
            child_view.invalid_locators,
            [
                {
                    "attrib": {
                        "expr": "/form/div/div/h1",
                        "position": "move",
                    },
                    "sourceline": 3,
                    "tag": "xpath",
                }
            ],
        )

    def test_broken_hierarchy_locators(self):
        self.patch(self.env.registry.get("ir.ui.view"), "_check_xml", lambda self: True)
        view = self.View.create(
            {
                "model": self.model,
                "name": "child_view",
                "arch": "<form></form>",
                "active": True,
            }
        )
        broken = self.View.create(
            {
                "model": self.model,
                "inherit_id": view.id,
                "name": "child_view",
                "arch": """<data><xpath expr="//group" position="after"><div /></xpath></data>""",
                "active": True,
            }
        )
        not_broken = self.View.create(
            {
                "model": self.model,
                "inherit_id": view.id,
                "name": "child_view",
                "arch": """<data><xpath expr="/form" position="inside"><div /></xpath></data>""",
                "active": True,
            }
        )

        self.assertEqual(
            broken.invalid_locators,
            [
                {
                    "attrib": {"expr": "//group", "position": "after"},
                    "sourceline": 1,
                    "tag": "xpath",
                }
            ],
        )
        self.assertEqual(not_broken.invalid_locators, [{"broken_hierarchy": True}])


class TestApplyInheritanceSpecs(ViewCase):
    def setUp(self):
        super().setUp()
        self.base_arch = E.form(E.field(name="target"), string="Title")
        self.adv_arch = E.form(
            E.field(
                "TEXT1",
                E.field(name="subtarget"),
                "TEXT2",
                E.field(name="anothersubtarget"),
                "TEXT3",
                name="target",
            ),
            string="Title",
        )

    def test_replace_outer(self):
        spec = E.field(E.field(name="replacement"), name="target", position="replace")

        self.View.apply_inheritance_specs(self.base_arch, spec)

        self.assertEqual(
            self.base_arch, E.form(E.field(name="replacement"), string="Title")
        )

    def test_delete(self):
        spec = E.field(name="target", position="replace")

        self.View.apply_inheritance_specs(self.base_arch, spec)

        self.assertEqual(self.base_arch, E.form(string="Title"))

    def test_insert_after(self):
        spec = E.field(E.field(name="inserted"), name="target", position="after")

        self.View.apply_inheritance_specs(self.base_arch, spec)

        self.assertEqual(
            self.base_arch,
            E.form(E.field(name="target"), E.field(name="inserted"), string="Title"),
        )

    def test_insert_before(self):
        spec = E.field(E.field(name="inserted"), name="target", position="before")

        self.View.apply_inheritance_specs(self.base_arch, spec)

        self.assertEqual(
            self.base_arch,
            E.form(E.field(name="inserted"), E.field(name="target"), string="Title"),
        )

    def test_insert_inside(self):
        default = E.field(E.field(name="inserted"), name="target")
        spec = E.field(E.field(name="inserted 2"), name="target", position="inside")

        self.View.apply_inheritance_specs(self.base_arch, default)
        self.View.apply_inheritance_specs(self.base_arch, spec)

        self.assertEqual(
            self.base_arch,
            E.form(
                E.field(
                    E.field(name="inserted"),
                    E.field(name="inserted 2"),
                    name="target",
                ),
                string="Title",
            ),
        )

    def test_replace_inner(self):
        spec = E.field(
            "TEXT 4",
            E.field(name="replacement"),
            "TEXT 5",
            E.field(name="replacement2"),
            "TEXT 6",
            name="target",
            position="replace",
            mode="inner",
        )

        expected = E.form(
            E.field(
                "TEXT 4",
                E.field(name="replacement"),
                "TEXT 5",
                E.field(name="replacement2"),
                "TEXT 6",
                name="target",
            ),
            string="Title",
        )

        self.View.apply_inheritance_specs(self.base_arch, spec)
        self.assertEqual(self.base_arch, expected)

        self.View.apply_inheritance_specs(self.adv_arch, spec)
        self.assertEqual(self.adv_arch, expected)

    def test_replace_inner_2(self):
        spec = E.field(
            "TEXT 4",
            E.xpath(position="move", expr="//field[2]"),
            "TEXT 5",
            E.xpath(expr="//field[@name='subtarget']", position="move"),
            "TEXT 6",
            name="target",
            position="replace",
            mode="inner",
        )

        expected = E.form(
            E.field(
                "TEXT 4",
                E.field(name="anothersubtarget"),
                "TEXT 5",
                E.field(name="subtarget"),
                "TEXT 6",
                name="target",
            ),
            string="Title",
        )

        self.View.apply_inheritance_specs(self.adv_arch, spec)
        self.assertEqual(self.adv_arch, expected)

    def test_unpack_data(self):
        spec = E.data(
            E.field(E.field(name="inserted 0"), name="target"),
            E.field(E.field(name="inserted 1"), name="target"),
            E.field(E.field(name="inserted 2"), name="target"),
            E.field(E.field(name="inserted 3"), name="target"),
        )

        self.View.apply_inheritance_specs(self.base_arch, spec)

        self.assertEqual(
            self.base_arch,
            E.form(
                E.field(
                    E.field(name="inserted 0"),
                    E.field(name="inserted 1"),
                    E.field(name="inserted 2"),
                    E.field(name="inserted 3"),
                    name="target",
                ),
                string="Title",
            ),
        )

    @mute_logger("odoo.addons.base.models.ir_ui_view")
    def test_invalid_position(self):
        spec = E.field(E.field(name="whoops"), name="target", position="serious_series")

        with self.assertRaises(ValueError):
            self.View.apply_inheritance_specs(self.base_arch, spec)

    @mute_logger("odoo.addons.base.models.ir_ui_view")
    def test_incorrect_version(self):
        arch = E.form(E.element(foo="42"))
        spec = E.element(E.field(name="placeholder"), foo="42", version="7.0")

        with self.assertRaises(ValueError):
            self.View.apply_inheritance_specs(arch, spec)

    @mute_logger("odoo.addons.base.models.ir_ui_view")
    def test_target_not_found(self):
        spec = E.field(name="targut")

        with self.assertRaises(ValueError):
            self.View.apply_inheritance_specs(self.base_arch, spec)


class TestApplyInheritanceWrapSpecs(ViewCase):
    def setUp(self):
        super().setUp()
        self.base_arch = E.template(E.div(E.p("Content")))

    def apply_spec(self, spec):
        self.View.apply_inheritance_specs(self.base_arch, spec)

    def test_replace(self):
        spec = E.xpath(E.div("$0", {"class": "some"}), expr="//p", position="replace")

        self.apply_spec(spec)
        self.assertEqual(
            self.base_arch,
            E.template(E.div(E.div(E.p("Content"), {"class": "some"}))),
        )


class TestApplyInheritanceMoveSpecs(ViewCase):
    def setUp(self):
        super().setUp()
        self.base_arch = E.template(
            E.div(E.p("Content", {"class": "some"})), E.div({"class": "target"})
        )
        self.wrapped_arch = E.template(
            E.div("aaaa", E.p("Content", {"class": "some"}), "bbbb"),
            E.div({"class": "target"}),
        )

    def apply_spec(self, arch, spec):
        self.View.apply_inheritance_specs(arch, spec)

    def test_move_replace(self):
        spec = E.xpath(
            E.xpath(expr="//p", position="move"),
            expr="//div[@class='target']",
            position="replace",
        )

        self.apply_spec(self.base_arch, spec)
        self.assertEqual(
            self.base_arch,
            E.template(E.div(), E.p("Content", {"class": "some"})),
        )
        self.apply_spec(self.wrapped_arch, spec)
        self.assertEqual(
            self.wrapped_arch,
            E.template(E.div("aaaabbbb"), E.p("Content", {"class": "some"})),
        )

    def test_move_inside(self):
        spec = E.xpath(
            E.xpath(expr="//p", position="move"),
            expr="//div[@class='target']",
            position="inside",
        )

        self.apply_spec(self.base_arch, spec)
        self.assertEqual(
            self.base_arch,
            E.template(
                E.div(),
                E.div(E.p("Content", {"class": "some"}), {"class": "target"}),
            ),
        )
        self.apply_spec(self.wrapped_arch, spec)
        self.assertEqual(
            self.wrapped_arch,
            E.template(
                E.div("aaaabbbb"),
                E.div(E.p("Content", {"class": "some"}), {"class": "target"}),
            ),
        )

    def test_move_before(self):
        spec = E.xpath(
            E.xpath(expr="//p", position="move"),
            expr="//div[@class='target']",
            position="before",
        )

        self.apply_spec(self.base_arch, spec)
        self.assertEqual(
            self.base_arch,
            E.template(
                E.div(""),
                E.p("Content", {"class": "some"}),
                E.div({"class": "target"}),
            ),
        )
        self.apply_spec(self.wrapped_arch, spec)
        self.assertEqual(
            self.wrapped_arch,
            E.template(
                E.div("aaaabbbb"),
                E.p("Content", {"class": "some"}),
                E.div({"class": "target"}),
            ),
        )

    def test_move_after(self):
        spec = E.xpath(
            E.xpath(expr="//p", position="move"),
            expr="//div[@class='target']",
            position="after",
        )

        self.apply_spec(self.base_arch, spec)
        self.assertEqual(
            self.base_arch,
            E.template(
                E.div(),
                E.div({"class": "target"}),
                E.p("Content", {"class": "some"}),
            ),
        )
        self.apply_spec(self.wrapped_arch, spec)
        self.assertEqual(
            self.wrapped_arch,
            E.template(
                E.div("aaaabbbb"),
                E.div({"class": "target"}),
                E.p("Content", {"class": "some"}),
            ),
        )

    def test_move_with_other_1(self):
        spec = E.xpath(
            E.xpath(expr="//p", position="move"),
            E.p("Content2", {"class": "new_p"}),
            expr="//div[@class='target']",
            position="after",
        )

        self.apply_spec(self.base_arch, spec)
        self.assertEqual(
            self.base_arch,
            E.template(
                E.div(),
                E.div({"class": "target"}),
                E.p("Content", {"class": "some"}),
                E.p("Content2", {"class": "new_p"}),
            ),
        )

    def test_move_with_other_2(self):
        spec = E.xpath(
            E.p("Content2", {"class": "new_p"}),
            E.xpath(expr="//p", position="move"),
            expr="//div[@class='target']",
            position="after",
        )

        self.apply_spec(self.wrapped_arch, spec)
        self.assertEqual(
            self.wrapped_arch,
            E.template(
                E.div("aaaabbbb"),
                E.div({"class": "target"}),
                E.p("Content2", {"class": "new_p"}),
                E.p("Content", {"class": "some"}),
            ),
        )

    def test_move_with_tail(self):
        moved_paragraph_xpath = E.xpath(expr="//p", position="move")
        moved_paragraph_xpath.tail = "tail of paragraph"
        spec = E.xpath(
            E.p("Content2", {"class": "new_p"}),
            moved_paragraph_xpath,
            expr="//div[@class='target']",
            position="after",
        )

        self.apply_spec(self.wrapped_arch, spec)

        moved_paragraph = E.p("Content", {"class": "some"})
        moved_paragraph.tail = "tail of paragraph"
        self.assertEqual(
            self.wrapped_arch,
            E.template(
                E.div("aaaabbbb"),
                E.div({"class": "target"}),
                E.p("Content2", {"class": "new_p"}),
                moved_paragraph,
            ),
        )

    @mute_logger("odoo.addons.base.models.ir_ui_view")
    def test_incorrect_move_1(self):
        spec = E.xpath(
            E.xpath(expr="//p[@name='none']", position="move"),
            expr="//div[@class='target']",
            position="after",
        )

        with self.assertRaises(ValueError):
            self.apply_spec(self.base_arch, spec)

    @mute_logger("odoo.addons.base.models.ir_ui_view")
    def test_incorrect_move_2(self):
        spec = E.xpath(
            E.xpath(E.p("Content2", {"class": "new_p"}), expr="//p", position="move"),
            expr="//div[@class='target']",
            position="after",
        )

        with self.assertRaises(ValueError):
            self.apply_spec(self.base_arch, spec)

    def test_incorrect_move_3(self):
        spec = E.xpath(
            E.div(
                E.xpath(
                    E.p("Content2", {"class": "new_p"}),
                    expr="//p",
                    position="move",
                ),
                {"class": "wrapper"},
            ),
            expr="//div[@class='target']",
            position="after",
        )

        self.apply_spec(self.base_arch, spec)
        self.assertEqual(
            self.base_arch,
            E.template(
                E.div(E.p("Content", {"class": "some"})),
                E.div({"class": "target"}),
                E.div(
                    E.xpath(
                        E.p("Content2", {"class": "new_p"}),
                        expr="//p",
                        position="move",
                    ),
                    {"class": "wrapper"},
                ),
            ),
        )


class TestNoModel(ViewCase):
    def test_create_view_nomodel(self):
        view = self.View.create(
            {
                "name": "dummy",
                "arch": '<template name="foo"/>',
                "inherit_id": False,
                "type": "qweb",
            }
        )
        fields = ["name", "arch", "type", "priority", "inherit_id", "model"]
        [data] = view.read(fields)
        self.assertEqual(
            data,
            {
                "id": view.id,
                "name": "dummy",
                "arch": '<template name="foo"/>',
                "type": "qweb",
                "priority": 16,
                "inherit_id": False,
                "model": False,
            },
        )

    text_para = E.p("", {"class": "legalese"})
    arch = E.body(
        E.div(E.h1("Title"), id="header"),
        E.p("Welcome!"),
        E.div(E.hr(), text_para, id="footer"),
        {"class": "index"},
    )

    def test_qweb_translation(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        ARCH = '<template name="foo">%s</template>'
        TEXT_EN = "Copyright copyrighter"
        TEXT_FR = "Copyrighter, tous droits réservés"
        view = self.View.create(
            {
                "name": "dummy",
                "arch": ARCH % TEXT_EN,
                "inherit_id": False,
                "type": "qweb",
            }
        )
        view.update_field_translations("arch_db", {"fr_FR": {TEXT_EN: TEXT_FR}})
        view = view.with_context(lang="fr_FR")
        self.assertEqual(view.arch, ARCH % TEXT_FR)


class TestTemplating(ViewCase):
    def setUp(self):
        super().setUp()
        self.patch(self.registry, "ready", True)

    def test_render_public_asset_as_a_plain_user(self):
        # The mailing editor and the website builder fetch their templates
        # through this RPC as internal users who may not read ir.ui.view;
        # the access check reads the view's groups on the user's behalf.
        self.View.create(
            {
                "name": "public asset",
                "type": "qweb",
                "key": "base.test_public_asset",
                "arch": "<t><div>public asset</div></t>",
                "group_ids": [Command.link(self.env.ref("base.group_user").id)],
            }
        )
        rendered = (
            self.View.with_user(self.user_demo)
            .render_public_asset("base.test_public_asset")
            .strip()
        )
        self.assertEqual(rendered, "<div>public asset</div>")

    def test_render_public_asset_honours_the_views_groups(self):
        self.View.create(
            {
                "name": "system asset",
                "type": "qweb",
                "key": "base.test_system_asset",
                "arch": "<t><div>system asset</div></t>",
                "group_ids": [Command.link(self.env.ref("base.group_system").id)],
            }
        )
        with self.assertRaises(AccessError):
            self.View.with_user(self.user_demo).render_public_asset(
                "base.test_system_asset"
            )

    def test_branding_t0(self):
        view1 = self.View.create(
            {
                "name": "Base view",
                "type": "qweb",
                "arch": """<root>
                <div role="search">
                    <input type="search" name="search"/>
                    <button type="submit">
                        <i class="oi-search"/>
                    </button>
                </div>
            </root>
            """,
            }
        )
        self.View.create(
            {
                "name": "Extension view",
                "type": "qweb",
                "inherit_id": view1.id,
                "arch": """<xpath expr="//div[@role='search']" position="replace">
                <form>
                    <t>$0</t>
                </form>
            </xpath>
            """,
            }
        )
        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()
        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)
        [initial] = arch.xpath("//div[@role='search']")
        self.assertEqual(
            "1",
            initial.get("data-oe-no-branding"),
            "Injected view must be marked as no-branding",
        )

    def test_branding_inherit(self):
        view1 = self.View.create(
            {
                "name": "Base view",
                "type": "qweb",
                "arch": """<root>
                <item order="1"/>
            </root>
            """,
            }
        )
        view2 = self.View.create(
            {
                "name": "Extension",
                "type": "qweb",
                "inherit_id": view1.id,
                "arch": """<xpath expr="//item" position="before">
                <item order="2"/>
            </xpath>
            """,
            }
        )

        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()

        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        [initial] = arch.xpath("//item[@order=1]")
        self.assertEqual(
            str(view1.id),
            initial.get("data-oe-id"),
            "initial should come from the root view",
        )
        self.assertEqual(
            "/root[1]/item[1]",
            initial.get("data-oe-xpath"),
            "initial's xpath should be within the root view only",
        )

        [second] = arch.xpath("//item[@order=2]")
        self.assertEqual(
            str(view2.id),
            second.get("data-oe-id"),
            "second should come from the extension view",
        )

    def test_branding_inherit_replace_node(self):
        view1 = self.View.create(
            {
                "name": "Base view",
                "type": "qweb",
                "arch": """<hello>
                <world></world>
                <world><t t-esc="hello"/></world>
                <world></world>
            </hello>
            """,
            }
        )
        self.View.create(
            {
                "name": "Extension",
                "type": "qweb",
                "inherit_id": view1.id,
                "arch": """<xpath expr="/hello/world[1]" position="replace">
                <world>Is a ghetto</world>
                <world>Wonder when I'll find paradise</world>
            </xpath>
            """,
            }
        )

        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()

        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        [initial] = arch.xpath("/hello[1]/world[1]")
        self.assertEqual(
            "/xpath/world[1]",
            initial.get("data-oe-xpath"),
            "Inherited nodes have correct xpath",
        )

        [initial] = arch.xpath("/hello[1]/world[2]")
        self.assertEqual(
            "/xpath/world[2]",
            initial.get("data-oe-xpath"),
            "Inherited nodes have correct xpath",
        )

        [initial] = arch.xpath("/hello[1]/world[3]")
        self.assertFalse(
            initial.get("data-oe-xpath"), "node containing t-esc is not branded"
        )

        [initial] = arch.xpath("/hello[1]/world[4]")
        self.assertEqual(
            "/hello[1]/world[3]",
            initial.get("data-oe-xpath"),
            "The node's xpath position should be correct",
        )

    def test_branding_inherit_replace_node2(self):
        view1 = self.View.create(
            {
                "name": "Base view",
                "type": "qweb",
                "arch": """<hello>
                <world></world>
                <world><t t-esc="hello"/></world>
                <world></world>
            </hello>
            """,
            }
        )
        self.View.create(
            {
                "name": "Extension",
                "type": "qweb",
                "inherit_id": view1.id,
                "arch": """<xpath expr="/hello/world[1]" position="replace">
                <war>Is a ghetto</war>
                <world>Wonder when I'll find paradise</world>
            </xpath>
            """,
            }
        )

        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()

        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        [initial] = arch.xpath("/hello[1]/war[1]")
        self.assertEqual(
            "/xpath/war",
            initial.get("data-oe-xpath"),
            "Inherited nodes have correct xpath",
        )

        [initial] = arch.xpath("/hello[1]/world[1]")
        self.assertEqual(
            "/xpath/world",
            initial.get("data-oe-xpath"),
            "Inherited nodes have correct xpath",
        )

        [initial] = arch.xpath("/hello[1]/world[2]")
        self.assertFalse(
            initial.get("data-oe-xpath"), "node containing t-esc is not branded"
        )

        [initial] = arch.xpath("/hello[1]/world[3]")
        self.assertEqual(
            "/hello[1]/world[3]",
            initial.get("data-oe-xpath"),
            "The node's xpath position should be correct",
        )

    def test_branding_inherit_remove_node(self):
        view1 = self.View.create(
            {
                "name": "Base view",
                "type": "qweb",
                "arch": """
                <hello>
                    <world></world>
                    <world></world>

                    <t t-esc="foo"/>
                </hello>
            """,
            }
        )
        self.View.create(
            {
                "name": "Extension",
                "type": "qweb",
                "inherit_id": view1.id,
                "arch": """
                <data>
                    <xpath expr="/hello/world[1]" position="replace"/>
                </data>
            """,
            }
        )

        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()

        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        [initial] = arch.xpath("/hello[1]/world[1]")
        self.assertEqual(
            "/hello[1]/world[2]",
            initial.get("data-oe-xpath"),
            "The node's xpath position should be correct",
        )

    def test_branding_inherit_remove_node2(self):
        view1 = self.View.create(
            {
                "name": "Base view",
                "type": "qweb",
                "arch": """
                <hello>
                    <world></world>
                    <world></world>
                </hello>
            """,
            }
        )
        self.View.create(
            {
                "name": "Extension",
                "type": "qweb",
                "inherit_id": view1.id,
                "arch": """
                <data>
                    <xpath expr="/hello/world[1]" position="replace"/>
                </data>
            """,
            }
        )

        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()

        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        [initial] = arch.xpath("/hello[1]")
        self.assertIsNone(
            initial.get("data-oe-model"),
            "The inner content of the root was xpath'ed, it should not receive branding anymore",
        )

        [initial] = arch.xpath("/hello[1]/world[1]")
        self.assertEqual(
            "/hello[1]/world[2]",
            initial.get("data-oe-xpath"),
            "The node's xpath position should be correct",
        )

    def test_branding_inherit_multi_replace_node(self):
        view1 = self.View.create(
            {
                "name": "Base view",
                "type": "qweb",
                "arch": """
                <hello>
                    <world class="a"></world>
                    <world class="b"></world>
                    <world class="c"></world>
                </hello>
            """,
            }
        )
        view2 = self.View.create(
            {
                "name": "Extension",
                "type": "qweb",
                "inherit_id": view1.id,
                "arch": """
                <data>
                    <xpath expr="//world" position="replace">
                        <world class="new_a"></world>
                        <world class="z"></world>
                    </xpath>
                </data>
            """,
            }
        )
        self.View.create(
            {
                "name": "Extension",
                "type": "qweb",
                "inherit_id": view2.id,
                "arch": """
                <data>
                    <xpath expr="//world[hasclass('new_a')]" position="replace">
                        <world class="another_new_a"></world>
                    </xpath>
                </data>
            """,
            }
        )

        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()
        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        [initial] = arch.xpath('//world[hasclass("z")]')
        self.assertEqual(
            "/data/xpath/world[2]",
            initial.get("data-oe-xpath"),
            "The node's xpath position should be correct",
        )

        [initial] = arch.xpath('//world[hasclass("c")]')
        self.assertEqual(
            "/hello[1]/world[3]",
            initial.get("data-oe-xpath"),
            "The node's xpath position should be correct",
        )

    def test_branding_inherit_multi_replace_node2(self):
        view1 = self.View.create(
            {
                "name": "Base view",
                "type": "qweb",
                "arch": """
                <hello>
                    <world class="a"></world>
                    <world class="b"></world>
                    <world class="c"></world>
                </hello>
            """,
            }
        )
        self.View.create(
            {
                "name": "Extension",
                "type": "qweb",
                "inherit_id": view1.id,
                "arch": """
                <data>
                    <xpath expr="//world" position="replace">
                        <world class="new_a"></world>
                        <world class="z"></world>
                    </xpath>
                </data>
            """,
            }
        )
        self.View.create(
            {
                "name": "Extension",
                "type": "qweb",
                "inherit_id": view1.id,
                "arch": """
                <data>
                    <xpath expr="//world" position="replace">
                        <world class="another_new_a"></world>
                    </xpath>
                </data>
            """,
            }
        )

        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()
        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        [initial] = arch.xpath('//world[hasclass("z")]')
        self.assertEqual(
            "/data/xpath/world[2]",
            initial.get("data-oe-xpath"),
            "The node's xpath position should be correct",
        )

        [initial] = arch.xpath('//world[hasclass("c")]')
        self.assertEqual(
            "/hello[1]/world[3]",
            initial.get("data-oe-xpath"),
            "The node's xpath position should be correct",
        )

    def test_branding_inherit_remove_added_from_inheritance(self):
        view1 = self.View.create(
            {
                "name": "Base view",
                "type": "qweb",
                "arch": """
                <hello>
                    <world class="a"></world>
                    <world class="b"></world>
                </hello>
            """,
            }
        )
        view2 = self.View.create(
            {
                "name": "Extension",
                "type": "qweb",
                "inherit_id": view1.id,
                "arch": """
                <data>
                    <xpath expr="//world[hasclass('a')]" position="after">
                        <world t-field="x"></world>
                        <world class="y"></world>
                    </xpath>
                </data>
            """,
            }
        )
        self.View.create(
            {
                "name": "Extension",
                "type": "qweb",
                "inherit_id": view2.id,
                "arch": """
                <data>
                    <xpath expr="//world[@t-field='x']" position="replace"/>
                </data>
            """,
            }
        )

        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()
        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        [initial] = arch.xpath('//world[hasclass("y")]')
        self.assertEqual(
            "/data/xpath/world[2]",
            initial.get("data-oe-xpath"),
            "The node's xpath position should be correct",
        )

        [initial] = arch.xpath('//world[hasclass("b")]')
        self.assertEqual(
            "/hello[1]/world[2]",
            initial.get("data-oe-xpath"),
            "The node's xpath position should be correct",
        )

    def test_branding_inherit_remove_node_processing_instruction(self):
        view1 = self.View.create(
            {
                "name": "Base view",
                "type": "qweb",
                "arch": """
                <html>
                    <head>
                        <hello></hello>
                    </head>
                    <body>
                        <world></world>
                    </body>
                </html>
            """,
            }
        )
        self.View.create(
            {
                "name": "Extension",
                "type": "qweb",
                "inherit_id": view1.id,
                "arch": """
                <data>
                    <xpath expr="//hello" position="replace"/>
                    <xpath expr="//world" position="replace"/>
                </data>
            """,
            }
        )

        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()
        arch = etree.fromstring(arch_string)

        head = arch.xpath("//head")[0]
        head_child = head[0]
        self.assertEqual(
            head_child.target,
            "apply-inheritance-specs-node-removal",
            "A node was removed at the start of the <head>, a processing instruction should exist as first child node",
        )
        self.assertEqual(
            head_child.text,
            "hello",
            "The processing instruction should mention the tag of the node that was removed",
        )

        body = arch.xpath("//body")[0]
        body_child = body[0]
        self.assertEqual(
            body_child.target,
            "apply-inheritance-specs-node-removal",
            "A node was removed at the start of the <body>, a processing instruction should exist as first child node",
        )
        self.assertEqual(
            body_child.text,
            "world",
            "The processing instruction should mention the tag of the node that was removed",
        )

        self.View.distribute_branding(arch)

        self.assertEqual(
            len(head),
            0,
            "The processing instruction of the <head> should have been removed",
        )
        self.assertEqual(
            len(body),
            0,
            "The processing instruction of the <body> should have been removed",
        )

    def test_branding_inherit_top_t_field(self):
        view1 = self.View.create(
            {
                "name": "Base view",
                "type": "qweb",
                "arch": """
                <hello>
                    <world></world>
                    <world t-field="a"/>
                    <world></world>
                    <world></world>
                </hello>
            """,
            }
        )
        self.View.create(
            {
                "name": "Extension",
                "type": "qweb",
                "inherit_id": view1.id,
                "arch": """
                <xpath expr="/hello/world[3]" position="after">
                    <world t-field="b"/>
                </xpath>
            """,
            }
        )
        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()
        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        [node] = arch.xpath('//*[@t-field="a"]')
        self.assertEqual(
            node.get("data-oe-xpath"),
            "/hello[1]/world[2]",
            "First t-field has indication of xpath",
        )

        [node] = arch.xpath('//*[@t-field="b"]')
        self.assertEqual(
            node.get("data-oe-xpath"),
            "/xpath/world",
            "Inherited t-field has indication of xpath",
        )

        [node] = arch.xpath("//world[last()]")
        self.assertEqual(
            node.get("data-oe-xpath"),
            "/hello[1]/world[4]",
            "The node's xpath position should be correct",
        )

        self.View.create(
            {
                "name": "Extension",
                "type": "qweb",
                "inherit_id": view1.id,
                "arch": """
                <data>
                    <world t-field="a" position="replace">
                        <world t-field="z"/>
                    </world>
                </data>
            """,
            }
        )
        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()
        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        node = arch.xpath("//world")[1]
        self.assertEqual(
            node.get("t-field"), "z", "The node has properly been replaced"
        )

    def test_branding_primary_inherit(self):
        view1 = self.View.create(
            {
                "name": "Base view",
                "type": "qweb",
                "arch": """<root>
                <item order="1"/>
            </root>
            """,
            }
        )
        view2 = self.View.create(
            {
                "name": "Extension",
                "type": "qweb",
                "mode": "primary",
                "inherit_id": view1.id,
                "arch": """<xpath expr="//item" position="after">
                <item order="2"/>
            </xpath>
            """,
            }
        )

        arch_string = view2.with_context(inherit_branding=True).get_combined_arch()

        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        [initial] = arch.xpath("//item[@order=1]")
        self.assertEqual(
            initial.get("data-oe-id"),
            str(view1.id),
            "initial should come from the root view",
        )
        self.assertEqual(
            initial.get("data-oe-xpath"),
            "/root[1]/item[1]",
            "initial's xpath should be within the inherited view only",
        )

        [second] = arch.xpath("//item[@order=2]")
        self.assertEqual(
            second.get("data-oe-id"),
            str(view2.id),
            "second should come from the extension view",
        )
        self.assertEqual(
            second.get("data-oe-xpath"),
            "/xpath/item",
            "second xpath should be on the inheriting view only",
        )

    def test_branding_distribute_inner(self):
        view1 = self.View.create(
            {
                "name": "Base view",
                "type": "qweb",
                "arch": """<root>
                <item order="1"/>
            </root>""",
            }
        )
        view2 = self.View.create(
            {
                "name": "Extension",
                "type": "qweb",
                "inherit_id": view1.id,
                "arch": """<xpath expr="//item" position="before">
                <item order="2">
                    <content t-att-href="foo">bar</content>
                </item>
            </xpath>""",
            }
        )

        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()

        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        self.assertEqual(
            arch,
            E.root(
                E.item(
                    E.content(
                        "bar",
                        {
                            "t-att-href": "foo",
                            "data-oe-model": "ir.ui.view",
                            "data-oe-id": str(view2.id),
                            "data-oe-field": "arch",
                            "data-oe-xpath": "/xpath/item/content[1]",
                        },
                    ),
                    {
                        "order": "2",
                    },
                ),
                E.item(
                    {
                        "order": "1",
                        "data-oe-model": "ir.ui.view",
                        "data-oe-id": str(view1.id),
                        "data-oe-field": "arch",
                        "data-oe-xpath": "/root[1]/item[1]",
                    }
                ),
            ),
        )

    def test_branding_attribute_groups(self):
        view = self.View.create(
            {
                "name": "Base View",
                "type": "qweb",
                "arch": """<root>
                <item groups="base.group_no_one"/>
            </root>""",
            }
        )

        arch_string = view.with_context(inherit_branding=True).get_combined_arch()
        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        self.assertEqual(
            arch,
            E.root(
                E.item(
                    {
                        "groups": "base.group_no_one",
                        "data-oe-model": "ir.ui.view",
                        "data-oe-id": str(view.id),
                        "data-oe-field": "arch",
                        "data-oe-xpath": "/root[1]/item[1]",
                    }
                )
            ),
        )

    def test_call_no_branding(self):
        view = self.View.create(
            {
                "name": "Base View",
                "type": "qweb",
                "arch": """<root>
                <item><span><t t-call="foo"/></span></item>
            </root>""",
            }
        )

        arch_string = view.with_context(inherit_branding=True).get_combined_arch()
        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        self.assertEqual(arch, E.root(E.item(E.span(E.t({"t-call": "foo"})))))

    def test_esc_no_branding(self):
        view = self.View.create(
            {
                "name": "Base View",
                "type": "qweb",
                "arch": """<root>
                <item><span t-esc="foo"/></item>
            </root>""",
            }
        )

        arch_string = view.with_context(inherit_branding=True).get_combined_arch()
        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        self.assertEqual(arch, E.root(E.item(E.span({"t-esc": "foo"}))))

    def test_ignore_unbrand(self):
        view1 = self.View.create(
            {
                "name": "Base view",
                "type": "qweb",
                "arch": """<root>
                <item order="1" t-ignore="true">
                    <t t-esc="foo"/>
                </item>
            </root>""",
            }
        )
        self.View.create(
            {
                "name": "Extension",
                "type": "qweb",
                "inherit_id": view1.id,
                "arch": """<xpath expr="//item[@order='1']" position="inside">
                <item order="2">
                    <content t-att-href="foo">bar</content>
                </item>
            </xpath>""",
            }
        )

        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()

        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        self.assertEqual(
            arch,
            E.root(
                E.item(
                    {"t-ignore": "true", "order": "1"},
                    E.t({"t-esc": "foo"}),
                    E.item({"order": "2"}, E.content({"t-att-href": "foo"}, "bar")),
                )
            ),
            "t-ignore should apply to injected sub-view branding, not just to the main view's",
        )

    def test_branding_remove_add_text(self):
        view1 = self.View.create(
            {
                "name": "Base view",
                "type": "qweb",
                "arch": """<root>
                <item order="1">
                    <item/>
                </item>
            </root>""",
            }
        )
        view2 = self.View.create(
            {
                "name": "Extension",
                "type": "qweb",
                "inherit_id": view1.id,
                "arch": """
            <data>
                <xpath expr="/root/item/item" position="replace" />
                <xpath expr="/root/item" position="inside">A<div/>B</xpath>
            </data>
            """,
            }
        )

        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()
        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        expected = etree.fromstring(f"""
        <root>
            <item order="1">
                A
                <div data-oe-id="{view2.id}" data-oe-xpath="/data/xpath[2]/div" data-oe-model="ir.ui.view" data-oe-field="arch"/>
                B
            </item>
        </root>
        """)
        self.assertEqual(arch, expected)


@tagged("post_install", "-at_install")
class TestViews(ViewCase):
    def test_nonexistent_attribute_removal(self):
        self.View.create(
            {
                "name": "Test View",
                "model": "ir.ui.view",
                "inherit_id": self.ref("base.view_view_tree"),
                "arch": """<?xml version="1.0"?>
                        <xpath expr="//field[@name='name']" position="attributes">
                            <attribute name="non_existing_attribute"></attribute>
                        </xpath>
                    """,
            }
        )

    def _insert_view(self, **kw):
        kw.pop("id", None)
        kw.setdefault("mode", "extension" if kw.get("inherit_id") else "primary")
        kw.setdefault("active", True)
        if "arch_db" in kw:
            arch_db = kw["arch_db"]
            if kw.get("inherit_id"):
                self.cr.execute(
                    "SELECT type FROM ir_ui_view WHERE id = %s",
                    [kw["inherit_id"]],
                )
                kw["type"] = self.cr.fetchone()[0]
            else:
                kw["type"] = etree.fromstring(arch_db).tag
            kw["arch_db"] = (
                Json({"en_US": arch_db})
                if self.env.lang in (None, "en_US")
                else Json({"en_US": arch_db, self.env.lang: arch_db})
            )

        keys = sorted(kw)
        fields = ",".join('"%s"' % (k.replace('"', r"\""),) for k in keys)
        params = ",".join("%%(%s)s" % (k,) for k in keys)

        query = "INSERT INTO ir_ui_view(%s) VALUES(%s) RETURNING id" % (
            fields,
            params,
        )
        self.cr.execute(query, kw)
        return self.cr.fetchone()[0]

    def test_view_root_node_matches_view_type(self):
        view = self.View.create(
            {
                "name": "foo",
                "model": "ir.ui.view",
                "arch": """
                <form>
                </form>
            """,
            }
        )
        self.assertEqual(view.type, "form")

        with self.assertRaises(ValidationError):
            self.View.create(
                {
                    "name": "foo",
                    "model": "ir.ui.view",
                    "type": "form",
                    "arch": """
                    <data>
                        <div>
                        </div>
                        <form>
                        </form>
                    </data>
                """,
                }
            )

    def test_custom_view_validation(self):
        model = "ir.actions.act_url"

        def validate():
            views = self.View._get_custom_views([model])
            return views.with_context(load_all_views=True)._check_xml()

        vid = self._insert_view(
            name="base view",
            model=model,
            priority=1,
            arch_db="""<?xml version="1.0"?>
                        <list string="view">
                          <field name="url"/>
                        </list>
                    """,
        )
        self.assertTrue(validate())

        self._insert_view(
            name="inherited view",
            model=model,
            priority=1,
            inherit_id=vid,
            arch_db="""<?xml version="1.0"?>
                        <xpath expr="//field[@name='url']" position="before">
                          <field name="name"/>
                        </xpath>
                    """,
        )
        self.assertTrue(validate())

        self._insert_view(
            name="inherited view 2",
            model=model,
            priority=5,
            inherit_id=vid,
            arch_db="""<?xml version="1.0"?>
                        <xpath expr="//field[@name='name']" position="after">
                          <field name="target"/>
                        </xpath>
                    """,
        )
        self.assertTrue(validate())

    def test_view_inheritance(self):
        view1 = self.View.create(
            {
                "name": "bob",
                "model": "ir.ui.view",
                "arch": """
                <form string="Base title">
                    <separator name="separator" string="Separator" colspan="4"/>
                    <footer>
                        <button name="action_archive" type="object" string="Next button" class="btn-primary"/>
                        <button string="Skip" special="cancel" class="btn-secondary"/>
                    </footer>
                </form>
            """,
            }
        )
        view2 = self.View.create(
            {
                "name": "edmund",
                "model": "ir.ui.view",
                "inherit_id": view1.id,
                "arch": """
                <data>
                    <form position="attributes">
                        <attribute name="string">Replacement title</attribute>
                    </form>
                    <footer position="replace">
                        <footer>
                            <button name="action_archive" type="object" string="New button"/>
                        </footer>
                    </footer>
                    <separator name="separator" position="replace">
                        <p>Replacement data</p>
                    </separator>
                </data>
            """,
            }
        )
        view3 = self.View.create(
            {
                "name": "jake",
                "model": "ir.ui.view",
                "inherit_id": view1.id,
                "priority": 17,
                "arch": """
                <footer position="attributes">
                    <attribute name="thing">bob tata lolo</attribute>
                    <attribute name="thing" add="bibi and co" remove="tata" separator=" " />
                    <attribute name="otherthing">bob, tata,lolo</attribute>
                    <attribute name="otherthing" remove="tata, bob"/>
                </footer>
            """,
            }
        )

        view = self.View.with_context(check_view_ids=[view2.id, view3.id]).get_view(
            view2.id, "form"
        )
        self.assertEqual(
            etree.fromstring(
                view["arch"], parser=etree.XMLParser(remove_blank_text=True)
            ),
            E.form(
                E.p("Replacement data"),
                E.footer(
                    E.button(
                        name="action_archive",
                        type="object",
                        string="New button",
                    ),
                    thing="bob lolo bibi and co",
                    otherthing="lolo",
                ),
                string="Replacement title",
            ),
        )

    def test_view_inheritance_text_inside(self):
        view1 = self.View.create(
            {
                "name": "alpha",
                "model": "ir.ui.view",
                "arch": '<form string="F">(<div/>)</form>',
            }
        )
        view2 = self.View.create(
            {
                "name": "beta",
                "model": "ir.ui.view",
                "inherit_id": view1.id,
                "arch": '<div position="inside">a<p/>b<p/>c</div>',
            }
        )
        view = self.View.with_context(check_view_ids=view2.ids).get_view(view1.id)
        self.assertEqual(
            view["arch"],
            '<form string="F">(<div>a<p/>b<p/>c</div>)</form>',
        )

    def test_view_inheritance_text_after(self):
        view1 = self.View.create(
            {
                "name": "alpha",
                "model": "ir.ui.view",
                "arch": '<form string="F">(<div/>)</form>',
            }
        )
        view2 = self.View.create(
            {
                "name": "beta",
                "model": "ir.ui.view",
                "inherit_id": view1.id,
                "arch": '<div position="after">a<p/>b<p/>c</div>',
            }
        )
        view = self.View.with_context(check_view_ids=view2.ids).get_view(view1.id)
        self.assertEqual(
            view["arch"],
            '<form string="F">(<div/>a<p/>b<p/>c)</form>',
        )

    def test_view_inheritance_text_before(self):
        view1 = self.View.create(
            {
                "name": "alpha",
                "model": "ir.ui.view",
                "arch": '<form string="F">(<div/>)</form>',
            }
        )
        view2 = self.View.create(
            {
                "name": "beta",
                "model": "ir.ui.view",
                "inherit_id": view1.id,
                "arch": '<div position="before">a<p/>b<p/>c</div>',
            }
        )
        view = self.View.with_context(check_view_ids=view2.ids).get_view(view1.id)
        self.assertEqual(
            view["arch"],
            '<form string="F">(a<p/>b<p/>c<div/>)</form>',
        )

    def test_view_inheritance_divergent_models(self):
        view1 = self.View.create(
            {
                "name": "bob",
                "model": "ir.ui.view.custom",
                "arch": """
                <form string="Base title">
                    <separator name="separator" string="Separator" colspan="4"/>
                    <footer>
                        <button name="action_archive" type="object" string="Next button" class="btn-primary"/>
                        <button string="Skip" special="cancel" class="btn-secondary"/>
                    </footer>
                </form>
            """,
            }
        )
        view2 = self.View.create(
            {
                "name": "edmund",
                "model": "ir.ui.view",
                "inherit_id": view1.id,
                "arch": """
                <data>
                    <form position="attributes">
                        <attribute name="string">Replacement title</attribute>
                    </form>
                    <footer position="replace">
                        <footer>
                            <button name="action_unarchive" type="object" string="New button"/>
                        </footer>
                    </footer>
                    <separator name="separator" position="replace">
                        <p>Replacement data</p>
                    </separator>
                </data>
            """,
            }
        )
        view3 = self.View.create(
            {
                "name": "jake",
                "model": "ir.ui.menu",
                "inherit_id": view1.id,
                "priority": 17,
                "arch": """
                <footer position="attributes">
                    <attribute name="thing">bob</attribute>
                </footer>
            """,
            }
        )

        view = self.View.with_context(check_view_ids=[view2.id, view3.id]).get_view(
            view2.id, view_type="form"
        )
        self.assertEqual(
            etree.fromstring(
                view["arch"], parser=etree.XMLParser(remove_blank_text=True)
            ),
            E.form(
                E.p("Replacement data"),
                E.footer(
                    E.button(
                        name="action_unarchive",
                        type="object",
                        string="New button",
                    )
                ),
                string="Replacement title",
            ),
        )

    def test_invalid_field(self):
        self.assertInvalid(
            """
                <form string="View">
                    <field name="name"/>
                    <field name="not_a_field"/>
                </form>
            """,
            'Field "not_a_field" does not exist in model "ir.ui.view"',
        )
        self.assertInvalid(
            """
                <form string="View">
                    <field/>
                </form>
            """,
            'Field tag must have a "name" attribute defined',
        )

    def test_invalid_subfield(self):
        arch = """
            <form string="View">
                <field name="name"/>
                <field name="inherit_children_ids">
                    <list name="Children">
                        <field name="name"/>
                        <field name="not_a_field"/>
                    </list>
                </field>
            </form>
        """
        self.assertInvalid(
            arch,
            '''Field "not_a_field" does not exist in model "ir.ui.view"''',
        )

    def test_parent_ref_in_root_view_is_tolerated(self):
        self.assertValid(
            """
                <form string="View">
                    <field name="name" invisible="parent.does_not_exist"/>
                </form>
            """,
        )

    def test_reset_arch(self):
        view = self.assertValid(
            '<form string="View"><field name="name"/></form>',
            name="reset arch base",
        )
        original = view.arch

        view.write({"arch": '<form string="Edited"><field name="name"/></form>'})
        self.assertNotEqual(view.arch, original)
        self.assertEqual(view.arch_prev, original)

        view.reset_arch(mode="soft")
        self.assertEqual(view.arch, original)

        self.assertFalse(view.arch_fs)
        view.reset_arch(mode="hard")
        self.assertEqual(view.arch, original)

    def test_invalid_type(self):
        with self.assertRaises(ValidationError):
            self.View.create(
                {
                    "name": "invalid_view",
                    "arch": "<template></template>",
                    "inherit_id": False,
                }
            )

    def test_attribute_node_with_no_name(self):
        with self.assertRaises(ValidationError):
            self.View.create(
                {
                    "name": "also_invalid_view",
                    "type": "list",
                    "arch": "<attribute></attribute>",
                    "inherit_id": False,
                }
            )

    def test_xml_editor_rejects_encoding_declaration(self):
        with self.assertRaises(UserError):
            self.View.create(
                {
                    "name": "encoding_declaration_view",
                    "arch_base": "<?xml version='1.0' encoding='utf-8'?>",
                    "inherit_id": False,
                }
            )

        view = self.assertValid(
            "<form string='Test'></form>", name="test_xml_encoding_view"
        )
        for field in ("arch", "arch_base"):
            with self.subTest(field=field):
                original_value = view[field]

                with self.assertRaises(UserError):
                    view.write({field: "<?xml version='1.0' encoding='utf-8'?><form/>"})

                self.assertXMLEqual(view[field], original_value)

    def test_context_in_view(self):
        arch = """
            <form string="View">
                <field name="name"/>%s
                <field name="inherit_id" context="{'stuff': model}"/>
            </form>
        """
        view = self.assertValid(arch % '<field name="model"/>')
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )

        view = self.assertValid(arch % "")
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )

    def test_context_in_subview(self):
        arch = """
            <form string="View">
                <field name="name"/>%s
                <field name="inherit_children_ids">
                    <form string="Children">
                        <field name="name"/>%s
                        <field name="inherit_id" context="{'stuff': model}"/>
                    </form>
                </field>
            </form>
        """
        view = self.assertValid(arch % ("", '<field name="model"/>'))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )

        view = self.assertValid(arch % ("", ""))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//field/form/field[@name="model"][@invisible][@readonly]'
            )
        )

        view = self.assertValid(arch % ('<field name="model"/>', ""))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//field/form/field[@name="model"][@invisible][@readonly]'
            )
        )

    def test_context_in_subview_with_parent(self):
        arch = """
            <form string="View">
                <field name="name"/>%s
                <field name="inherit_children_ids">
                    <form string="Children">
                        <field name="name"/>%s
                        <field name="inherit_id" context="{'stuff': parent.model}"/>
                    </form>
                </field>
            </form>
        """

        view = self.assertValid(arch % ('<field name="model"/>', ""))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )

        view = self.assertValid(arch % ("", ""))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field/form/field[@name="model"][@invisible][@readonly]'
            )
        )

        view = self.assertValid(arch % ("", '<field name="model"/>'))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field/form/field[@name="model"][@invisible][@readonly]'
            )
        )

    def test_context_in_subsubview_with_parent(self):
        arch = """
            <form string="View">
                <field name="name"/>%s
                <field name="inherit_children_ids">
                    <form string="Children">
                        <field name="name"/>%s
                        <field name="inherit_children_ids">
                            <form string="Children">
                                <field name="name"/>%s
                                <field name="inherit_id" context="{'stuff': parent.parent.model}"/>
                            </form>
                        </field>
                    </form>
                    <list>
                        <field name="name"/>
                    </list>
                </field>
            </form>
        """

        view = self.assertValid(arch % ('<field name="model"/>', "", ""))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )

        view = self.assertValid(arch % ("", "", ""))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field//field[@name="model"][@invisible][@readonly]'
            )
        )

        view = self.assertValid(arch % ("", '<field name="model"/>', ""))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field//field[@name="model"][@invisible][@readonly]'
            )
        )

        view = self.assertValid(arch % ("", "", '<field name="model"/>'))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field//field[@name="model"][@invisible][@readonly]'
            )
        )

    def test_domain_id_case(self):
        self.assertValid("""
            <form string="View">
                <field name="inherit_id" domain="[('id', '=', False)]"/>
            </form>
        """)

    def test_domain_boolean_case(self):
        arch = """
            <form string="View">
                %s
                <field name="inherit_id" domain="[(%s, '=', %s)]"/>
            </form>
        """
        self.assertValid(arch % ("", "1", "1"))
        self.assertValid(arch % ("", "0", "1"))
        self.assertValid(arch % ('<field name="name"/>', "1", "0 if name else 1"))
        self.assertInvalid(
            arch
            % (
                '<field name="name"/><field name="type"/>',
                "'tata' if name else 'tutu'",
                "type",
            ),
            "Wrong domain formatting",
        )
        view = self.assertValid(arch % ("", "1", "0 if name else 1"))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//field[@name="name"][@invisible][@readonly]'
            )
        )

    def test_domain_in_view(self):
        arch = """
            <form string="View">
                <field name="name"/>%s
                <field name="inherit_id" domain="[('model', '=', model)]"/>
            </form>
        """
        view = self.assertValid(arch % '<field name="model"/>')
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )

        view = self.assertValid(arch % "")
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )

    def test_domain_unknown_field(self):
        self.assertInvalid(
            """
                <form string="View">
                    <field name="name"/>
                    <field name="inherit_id" domain="[('invalid_field', '=', 'res.users')]"/>
                </form>
            """,
            """Unknown field "ir.ui.view.invalid_field" in domain of <field name="inherit_id"> ([('invalid_field', '=', 'res.users')])""",
        )

    def test_domain_field_searchable(self):
        arch = """
            <form string="View">
                <field name="name"/>
                <field name="inherit_id" domain="[('%s', '=', 'test')]"/>
            </form>
        """
        self.assertValid(arch % "model_data_id")
        self.assertInvalid(
            arch % "xml_id",
            """Unsearchable field “xml_id” in path “xml_id” in domain of <field name="inherit_id"> ([('xml_id', '=', 'test')])""",
        )

    def test_domain_date_part_is_a_property_not_a_hop(self):
        arch = """
            <form string="View">
                <field name="name"/>
                <field name="inherit_id" domain="[('%s', '=', 1)]"/>
            </form>
        """
        self.assertValid(arch % "create_date.month_number")
        self.assertValid(arch % "create_date.day_of_month")

        for path in (
            "create_date.not_a_granularity",
            "create_date.month_number.deeper",
            "name.month_number",
        ):
            field = path.split(".")[0]
            self.assertInvalid(
                arch % path,
                f"""Non-relational field “{field}” in path “{path}” in domain """
                f"""of <field name="inherit_id"> ([('{path}', '=', 1)])""",
            )

    def test_domain_field_no_comodel(self):
        self.assertInvalid(
            """
            <form string="View">
                <field name="name" domain="[('test', '=', 'test')]"/>
            </form>
        """,
            "Domain on non-relational field \"name\" makes no sense (domain:[('test', '=', 'test')])",
        )

    def test_domain_in_subview(self):
        arch = """
            <form string="View">
                <field name="name"/>%s
                <field name="inherit_children_ids">
                    <form string="Children">
                        <field name="name"/>%s
                        <field name="inherit_id" domain="[('model', '=', model)]"/>
                    </form>
                </field>
            </form>
        """
        self.assertValid(arch % ("", '<field name="model"/>'))

        view = self.assertValid(arch % ("", ""))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//field/form/field[@name="model"][@invisible][@readonly]'
            )
        )

        view = self.assertValid(arch % ('<field name="model"/>', ""))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//field/form/field[@name="model"][@invisible][@readonly]'
            )
        )

    def test_domain_in_subview_with_parent(self):
        arch = """
            <form string="View">
                <field name="name"/>%s
                <field name="inherit_children_ids">
                    <form string="Children">
                        <field name="name"/>%s
                        <field name="inherit_id" domain="[('model', '=', parent.model)]"/>
                    </form>
                </field>%s
            </form>
        """
        view = self.assertValid(arch % ('<field name="model"/>', "", ""))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )

        view = self.assertValid(arch % ("", "", '<field name="model"/>'))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )

        view = self.assertValid(arch % ("", "", ""))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )

        view = self.assertValid(arch % ("", '<field name="model"/>', ""))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )

    def test_domain_on_field_in_view(self):
        field = self.env["ir.ui.view"]._fields["inherit_id"]
        self.patch(field, "domain", "[('model', '=', model)]")

        arch = """
            <form string="View">
                <field name="name"/>%s
                <field name="inherit_id"/>
            </form>
        """
        view = self.assertValid(arch % '<field name="model"/>')
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )

        view = self.assertValid(arch % "")
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )

    def test_domain_on_field_in_subview(self):
        field = self.env["ir.ui.view"]._fields["inherit_id"]
        self.patch(field, "domain", "[('model', '=', model)]")

        arch = """
            <form string="View">
                <field name="name"/>%s
                <field name="inherit_children_ids">
                    <form string="Children">
                        <field name="name"/>%s
                        <field name="inherit_id"/>
                    </form>
                </field>
            </form>
        """
        view = self.assertValid(arch % ("", '<field name="model"/>'))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )

        view = self.assertValid(arch % ("", ""))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//field/form/field[@name="model"][@invisible][@readonly]'
            )
        )

    def test_domain_on_field_in_subview_with_parent(self):
        field = self.env["ir.ui.view"]._fields["inherit_id"]
        self.patch(field, "domain", "[('model', '=', parent.model)]")

        arch = """
            <form string="View">
                <field name="name"/>%s
                <field name="inherit_children_ids">
                    <form string="Children">
                        <field name="name"/>%s
                        <field name="inherit_id"/>
                    </form>
                </field>
            </form>
        """
        view = self.assertValid(arch % ('<field name="model"/>', ""))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )

        view = self.assertValid(arch % ("", ""))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field/form/field[@name="model"][@invisible][@readonly]'
            )
        )

        view = self.assertValid(arch % ("", '<field name="model"/>'))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field/form/field[@name="model"][@invisible][@readonly]'
            )
        )

    def test_domain_on_field_in_noneditable_subview(self):
        field = self.env["ir.ui.view"]._fields["inherit_id"]
        self.patch(field, "domain", "[('model', '=', model)]")

        arch = """
            <form string="View">
                <field name="name"/>
                <field name="inherit_children_ids">
                    <list string="Children"%s>
                        <field name="name"/>
                        <field name="inherit_id"/>
                    </list>
                </field>
            </form>
        """
        view = self.assertValid(arch % "")
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )

        view = self.assertValid(arch % ' editable="bottom"')
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//field/list/field[@name="model"][@column_invisible][@readonly]'
            )
        )

    def test_domain_on_readonly_field_in_view(self):
        field = self.env["ir.ui.view"]._fields["inherit_id"]
        self.patch(field, "domain", "[('model', '=', model)]")

        arch = """
            <form string="View">
                <field name="name"/>
                <field name="inherit_id" readonly="1"/>
            </form>
        """
        self.assertValid(arch)

        self.patch(field, "readonly", True)
        arch = """
            <form string="View">
                <field name="name"/>
                <field name="inherit_id"/>
            </form>
        """
        self.assertValid(arch)

    def test_domain_on_readonly_field_in_subview(self):
        field = self.env["ir.ui.view"]._fields["inherit_id"]
        self.patch(field, "domain", "[('model', '=', model)]")

        arch = """
            <form string="View">
                <field name="name"/>
                <field name="inherit_children_ids"%s>
                    <form string="Children">
                        <field name="name"/>
                        <field name="inherit_id"/>
                    </form>
                </field>
            </form>
        """
        view = self.assertValid(arch % ' readonly="1"')
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )

        view = self.assertValid(arch % "")
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//field/form/field[@name="model"][@invisible][@readonly]'
            )
        )

    def test_domain_in_filter(self):
        arch = """
            <search string="Search">
                <field name="%s"/>
                <filter string="Dummy" name="draft" domain="[('%s', '=', 'dummy')]"/>
            </search>
        """
        self.assertValid(arch % ("name", "name"))
        self.assertValid(arch % ("name", "inherit_children_ids.name"))
        self.assertInvalid(
            arch % ("invalid_field", "name"),
            'Field "invalid_field" does not exist in model "ir.ui.view"',
        )
        self.assertInvalid(
            arch % ("name", "invalid_field"),
            """Unknown field "ir.ui.view.invalid_field" in domain of <filter name="draft"> ([('invalid_field', '=', 'dummy')])""",
        )
        self.assertInvalid(
            arch % ("name", "inherit_children_ids.invalid_field"),
            """Unknown field "ir.ui.view.invalid_field" in domain of <filter name="draft"> ([('inherit_children_ids.invalid_field', '=', 'dummy')])""",
        )

    def test_group_by_in_filter(self):
        arch = """
            <search string="Search">
                <filter string="Date" name="month" domain="[]" context="{'group_by':'%s'}"/>
            </search>
        """
        self.assertValid(arch % "name")
        self.assertInvalid(
            arch % "invalid_field",
            """Unknown field “invalid_field” in "group_by" value in context=“{'group_by':'invalid_field'}”""",
        )

    def test_domain_invalid_in_filter(self):
        self.assertInvalid(
            """ <search string="Search">
                    <filter string="Dummy" name="draft" domain="['name', '=', 'dummy']"/>
                </search>
            """,
            """Invalid domain of <filter name="draft">: “['name', '=', 'dummy']”""",
        )

    def test_searchpanel(self):
        arch = """
            <search>
                %s
                <searchpanel>
                    %s
                    <field name="group_ids" select="multi" domain="[('%s', '=', %s)]" enable_counters="1"/>
                </searchpanel>
            </search>
        """
        view = self.assertValid(
            arch % ("", '<field name="inherit_id"/>', "view_access", "inherit_id")
        )
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field[@name="inherit_id"][@invisible][@readonly]'
            )
        )
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field[@name="view_access"][@invisible][@readonly]'
            )
        )

        view = self.assertValid(
            arch % ('<field name="inherit_id"/>', "", "view_access", "inherit_id")
        )
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//searchpanel/field[@name="inherit_id"][@invisible][@readonly]'
            )
        )

        view = self.assertValid(
            arch
            % (
                "",
                '<field name="inherit_id"/>',
                "view_access",
                "parent.arch_updated",
            )
        )
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field[@name="view_access"][@invisible][@readonly]'
            )
        )

        self.assertInvalid(
            arch % ("", '<field name="inherit_id"/>', "view_access", "view_access"),
            """field “view_access” does not exist in model “ir.ui.view”.""",
        )
        self.assertInvalid(
            arch % ("", '<field name="inherit_id"/>', "inherit_id", "inherit_id"),
            """Unknown field "res.groups.inherit_id" in domain of <field name="group_ids"> ([('inherit_id', '=', inherit_id)])""",
        )

        arch = """
            <search>
                <searchpanel>
                    <field name="inherit_id" enable_counters="1"/>
                </searchpanel>
                <searchpanel>
                    <field name="inherit_id" enable_counters="1"/>
                </searchpanel>
            </search>
        """
        self.assertInvalid(arch, "Search tag can only contain one search panel")

    def test_groups_field(self):
        arch = """
            <form string="View">
                <field name="name" groups="%s"/>
            </form>
        """
        self.assertValid(arch % "base.group_no_one")
        self.assertWarning(arch % "base.dummy")

    def test_attrs_groups_behavior(self):
        view = self.View.create(
            {
                "name": "foo",
                "model": "res.partner",
                "arch": """
                <form>
                    <field name="name"/>
                    <field name="company_id" groups="base.group_system"/>
                    <div id="foo"/>
                    <div id="bar" groups="base.group_system"/>
                </form>
            """,
            }
        )
        user_demo = self.user_demo
        self.assertFalse(user_demo.has_group("base.group_system"))
        arch = (
            self.env["res.partner"]
            .with_user(user_demo)
            .get_view(view_id=view.id)["arch"]
        )
        tree = etree.fromstring(arch)
        self.assertTrue(tree.xpath('//field[@name="name"]'))
        self.assertFalse(tree.xpath('//field[@name="company_id"]'))
        self.assertTrue(tree.xpath('//div[@id="foo"]'))
        self.assertFalse(tree.xpath('//div[@id="bar"]'))

        user_admin = self.env.ref("base.user_admin")
        self.assertTrue(user_admin.has_group("base.group_system"))
        arch = (
            self.env["res.partner"]
            .with_user(user_admin)
            .get_view(view_id=view.id)["arch"]
        )
        tree = etree.fromstring(arch)
        self.assertTrue(tree.xpath('//field[@name="name"]'))
        self.assertTrue(tree.xpath('//field[@name="company_id"]'))
        self.assertTrue(tree.xpath('//div[@id="foo"]'))
        self.assertTrue(tree.xpath('//div[@id="bar"]'))

    def test_projection_is_shared_by_capability_signature(self):
        view = self.View.create(
            {
                "name": "foo",
                "model": "res.partner",
                "arch": """
                <form>
                    <field name="name"/>
                    <field name="company_id" groups="base.group_system"/>
                </form>
            """,
            }
        )
        Partner = self.env["res.partner"]
        demo = Partner.with_user(self.user_demo)
        admin = Partner.with_user(self.env.ref("base.user_admin"))

        first = demo.get_view(view_id=view.id)
        second = demo.get_view(view_id=view.id)
        self.assertIs(first["ir"], second["ir"])
        self.assertIsNot(first, second)
        self.assertEqual(first["arch"], second["arch"])
        with self.assertRaises(NotImplementedError):
            first["ir"]["kind"] = "mutated"

        other = admin.get_view(view_id=view.id)
        self.assertIsNot(first["ir"], other["ir"])
        self.assertFalse(
            etree.fromstring(first["arch"]).xpath("//field[@name='company_id']")
        )
        self.assertTrue(
            etree.fromstring(other["arch"]).xpath("//field[@name='company_id']")
        )

    def test_projection_signature_covers_the_kanban_group_by_comodel(self):
        view = self.View.create(
            {
                "name": "foo",
                "model": "res.partner",
                "arch": """
                <kanban default_group_by="user_id">
                    <templates>
                        <t t-name="card"><field name="name"/></t>
                    </templates>
                </kanban>
            """,
            }
        )
        Partner = self.env["res.partner"]
        demo = Partner.with_user(self.user_demo)
        admin = Partner.with_user(self.env.ref("base.user_admin"))
        capabilities = Partner._get_view_cache(view.id, "kanban")["capabilities"]
        self.assertEqual(capabilities[1], (("res.partner", "user_id"),))
        self.assertIn(
            "res.users",
            [entry[0] for entry in demo._view_capability_signature(capabilities)[1]],
        )

        self.assertFalse(
            self.env["res.users"].with_user(self.user_demo).has_access("create")
        )
        demo_root = etree.fromstring(demo.get_view(view_id=view.id)["arch"])
        admin_root = etree.fromstring(admin.get_view(view_id=view.id)["arch"])
        self.assertEqual(demo_root.get("group_create"), "False")
        self.assertIsNone(admin_root.get("group_create"))

    def test_attrs_groups_validation(self):
        def validate(arch, valid=False, parent=False, field="name", model="ir.ui.view"):
            parent = "parent." if parent else ""
            if valid:
                self.assertValid(
                    arch % {"attrs": f"""invisible="{parent}{field} == 'foo'" """},
                    model=model,
                )
                self.assertValid(
                    arch
                    % {"attrs": f"""domain="[('name', '!=', {parent}{field})]" """},
                    model=model,
                )
                self.assertValid(
                    arch
                    % {"attrs": f"""context="{{'default_name': {parent}{field}}}" """},
                    model=model,
                )
                self.assertValid(
                    arch
                    % {"attrs": f"""decoration-info="{parent}{field} == 'foo'" """},
                    model=model,
                )
            else:
                self.assertInvalid(
                    arch % {"attrs": f"""invisible="{parent}{field} == 'foo'" """},
                    f"""Field '{field}' used in modifier 'invisible' ({parent}{field} == 'foo') is restricted to the group(s)""",
                    model=model,
                )
                target = "inherit_id" if model == "ir.ui.view" else "company_id"
                self.assertInvalid(
                    arch
                    % {"attrs": f"""domain="[('name', '!=', {parent}{field})]" """},
                    f"""Field '{field}' used in domain of <field name="{target}"> ([('name', '!=', {parent}{field})]) is restricted to the group(s)""",
                    model=model,
                )
                self.assertInvalid(
                    arch
                    % {"attrs": f"""context="{{'default_name': {parent}{field}}}" """},
                    f"""Field '{field}' used in context ({{'default_name': {parent}{field}}}) is restricted to the group(s)""",
                    model=model,
                )
                self.assertInvalid(
                    arch
                    % {"attrs": f"""decoration-info="{parent}{field} == 'foo'" """},
                    f"""Field '{field}' used in decoration-info="{parent}{field} == 'foo'" is restricted to the group(s)""",
                    model=model,
                )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="inherit_children_ids">
                    <list editable="bottom">
                        <field name="inherit_id" groups="base.group_system" %(attrs)s/>
                    </list>
                </field>
            </form>
        """,
            valid=True,
            parent=True,
        )

        validate(
            """
            <form string="View">
                <field name="name"/>
                <field name="inherit_children_ids">
                    <list editable="bottom">
                        <field name="inherit_id" groups="base.group_system" %(attrs)s/>
                    </list>
                </field>
            </form>
        """,
            valid=True,
            parent=True,
        )

        validate(
            """
            <form string="View">
                <field name="name"/>
                <field name="inherit_id" %(attrs)s groups="base.group_system"/>
            </form>
        """,
            valid=True,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="inherit_id" groups="base.group_system" %(attrs)s/>
            </form>
        """,
            valid=True,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.group_portal"/>
                <field name="name" groups="base.group_system"/>
                <field name="inherit_id" groups="base.group_system" %(attrs)s/>
            </form>
        """,
            valid=True,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="name" groups="base.group_portal"/>
                <field name="inherit_id" groups="base.group_system" %(attrs)s/>
                <field name="inherit_id" groups="base.group_portal" %(attrs)s/>
            </form>
        """,
            valid=True,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.group_portal,base.group_system"/>
                <field name="inherit_id" groups="base.group_system" %(attrs)s/>
            </form>
        """,
            valid=True,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.group_erp_manager"/>
                <field name="inherit_id" groups="base.group_system" %(attrs)s/>
            </form>
        """,
            valid=True,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.group_erp_manager"/>
                <field name="inherit_children_ids">
                    <list editable="bottom">
                        <field name="inherit_id" groups="base.group_system" %(attrs)s/>
                    </list>
                </field>
            </form>
        """,
            valid=True,
            parent=True,
        )

        validate(
            """
            <form string="View">
                <group groups="base.group_system">
                    <field name="name"/>
                    <field name="inherit_id" %(attrs)s/>
                </group>
            </form>
        """,
            valid=True,
        )

        validate(
            """
            <form string="View">
                <group groups="base.group_system">
                    <field name="name"/>
                    <field name="inherit_id" %(attrs)s groups="base.group_multi_currency,base.group_multi_company"/>
                </group>
            </form>
        """,
            valid=True,
        )

        validate(
            """
            <form string="View">
                <group groups="base.group_system">
                    <field name="name"/>
                </group>
                <group groups="base.group_system">
                    <field name="inherit_id" %(attrs)s/>
                </group>
            </form>
        """,
            valid=True,
        )

        validate(
            """
            <form string="View">
                <group groups="base.group_erp_manager">
                    <field name="name"/>
                </group>
                <group groups="base.group_system">
                    <field name="inherit_id" %(attrs)s/>
                </group>
            </form>
        """,
            valid=True,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="inherit_children_ids" groups="base.group_system">
                    <list editable="bottom">
                        <field name="inherit_id" %(attrs)s/>
                    </list>
                </field>
            </form>
        """,
            valid=True,
            parent=True,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.group_erp_manager"/>
                <field name="inherit_children_ids" groups="base.group_system">
                    <list editable="bottom">
                        <field name="inherit_id" %(attrs)s/>
                    </list>
                </field>
            </form>
        """,
            valid=True,
            parent=True,
        )

        validate(
            """
            <form string="View">
                <field name="name"/>
                <field name="inherit_id" groups="!base.group_system" %(attrs)s/>
            </form>
        """,
            valid=True,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="!base.group_user"/>
                <field name="inherit_id" groups="!base.group_user,!base.group_portal" %(attrs)s/>
            </form>
        """,
            valid=True,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="!base.group_system"/>
                <field name="inherit_id" groups="!base.group_user" %(attrs)s/>
            </form>
        """,
            valid=True,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="!base.group_system"/>
                <field name="name" groups="base.group_system"/>
                <field name="inherit_id" %(attrs)s/>
            </form>
        """,
            valid=True,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="!base.group_system"/>
                <field name="name" groups="base.group_system"/>
                <field name="inherit_id" groups="base.group_system" %(attrs)s/>
            </form>
        """,
            valid=True,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="!base.group_system"/>
                <field name="name" groups="base.group_system"/>
                <field name="inherit_id" groups="!base.group_system" %(attrs)s/>
            </form>
        """,
            valid=True,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="!base.group_system"/>
                <field name="name" groups="base.group_system"/>
                <field name="inherit_id" groups="base.group_portal" %(attrs)s/>
            </form>
        """,
            valid=True,
        )

        validate(
            """
            <form string="View attachment">
                <field name="access_token"/>
                <field name="company_id" %(attrs)s groups="base.group_user"/>
            </form>
        """,
            model="ir.attachment",
            field="access_token",
            valid=True,
        )
        validate(
            """
            <form string="View attachment">
                <field name="company_id" %(attrs)s groups="base.group_user"/>
            </form>
        """,
            model="ir.attachment",
            field="access_token",
            valid=True,
        )
        validate(
            """
            <form string="View attachment">
                <field name="company_id" %(attrs)s groups="base.group_erp_manager"/>
            </form>
        """,
            model="ir.attachment",
            field="access_token",
            valid=True,
        )
        validate(
            """
            <form string="View attachment">
                <group groups="base.group_erp_manager">
                    <field name="company_id" %(attrs)s/>
                </group>
            </form>
        """,
            model="ir.attachment",
            field="access_token",
            valid=True,
        )

        validate(
            """
            <form string="View attachment">
                <field name="access_token"/>
                <field name="company_id" %(attrs)s/>
            </form>
        """,
            model="ir.attachment",
            field="access_token",
            valid=True,
        )
        validate(
            """
            <form string="View attachment">
                <field name="access_token"/>
                <field name="company_id" %(attrs)s groups="base.group_portal"/>
            </form>
        """,
            model="ir.attachment",
            field="access_token",
            valid=True,
        )
        validate(
            """
            <form string="View attachment">
                <field name="company_id" %(attrs)s groups="base.group_portal"/>
            </form>
        """,
            model="ir.attachment",
            field="access_token",
            valid=True,
        )
        validate(
            """
            <form string="View attachment">
                <field name="company_id" %(attrs)s/>
            </form>
        """,
            model="ir.attachment",
            field="access_token",
            valid=True,
        )

    @mute_logger("odoo.addons.base.models.ir_ui_view")
    def test_attrs_missing_field(self):
        user = self.env["res.users"].create(
            {
                "name": "A User",
                "login": "a_user",
                "email": "a@user.com",
                "group_ids": [(4, self.env.ref("base.group_user").id)],
            }
        )

        def validate(template, field, demo=True, no_add=False):
            view = self.View.create(
                {
                    "name": "Form view attachment",
                    "model": "ir.attachment",
                    "arch": template,
                }
            )
            arch = self.env["ir.attachment"]._get_view_cache(view_id=view.id)["arch"]
            tree = etree.fromstring(arch)
            nodes = tree.xpath(
                f"//field[@name='{field}'][@invisible='True'][@readonly='True']"
            )
            if no_add:
                nodes = [etree.tostring(node, encoding="unicode") for node in nodes]
                self.assertFalse(
                    nodes, f"Field '{field}' should not be added automatically"
                )
                return
            self.assertTrue(
                len(nodes) == 1,
                f"Field '{field}' should be added automatically",
            )

            arch = self.env["ir.attachment"].get_view(view_id=view.id)["arch"]
            tree = etree.fromstring(arch)
            nodes = tree.xpath(
                f"//field[@name='{field}'][@invisible='True'][@readonly='True']"
            )
            self.assertTrue(
                len(nodes) == 1,
                f"Field '{field}' should be added automatically",
            )

            arch = (
                self.env["ir.attachment"]
                .with_user(user)
                .get_view(view_id=view.id)["arch"]
            )
            tree = etree.fromstring(arch)
            nodes = tree.xpath(
                f"//field[@name='{field}'][@invisible='True'][@readonly='True']"
            )
            if demo:
                self.assertTrue(
                    len(nodes) == 1,
                    f"Field '{field}' should be added automatically",
                )
            else:
                self.assertFalse(
                    nodes,
                    f"Field '{field}' should be added automatically but was removed by access rigth",
                )

        validate(
            """
                <form string="View attachment">
                    <field name="company_id" invisible="name != 'toto'"/>
                </form>
            """,
            field="name",
        )

        validate(
            """
                <form string="View attachment">
                    <field name="company_id" invisible="not access_token" groups="base.group_erp_manager"/>
                </form>
            """,
            field="access_token",
            demo=False,
        )

        validate(
            """
                <form string="View attachment">
                    <field name="company_id" invisible="not name" groups="base.group_erp_manager"/>
                    <field name="company_id" invisible="not name" groups="base.group_system"/>
                </form>
            """,
            field="name",
            demo=False,
        )
        validate(
            """
                <form string="View attachment">
                    <field name="company_id" invisible="not name" groups="base.group_erp_manager"/>
                    <field name="company_id" invisible="not name" groups="base.group_system"/>
                    <field name="company_id" invisible="not name" groups="base.group_multi_company"/>
                    <field name="company_id" invisible="not name" groups="base.group_user"/>
                </form>
            """,
            field="name",
            demo=True,
        )
        validate(
            """
                <form string="View attachment">
                    <field name="company_id" invisible="not name" groups="base.group_erp_manager"/>
                    <field name="company_id" invisible="not name"/>
                </form>
            """,
            field="name",
            demo=True,
        )

        validate(
            """
                <form string="View attachment">
                    <group groups="base.group_erp_manager">
                        <field name="company_id" invisible="not access_token"/>
                    </group>
                </form>
            """,
            field="access_token",
            demo=False,
        )
        validate(
            """
                <form string="View attachment">
                    <group groups="base.group_erp_manager">
                        <field name="company_id" invisible="not name" groups="base.group_multi_company"/>
                        <field name="company_id" invisible="not name" groups="base.group_user"/>
                    </group>
                </form>
            """,
            field="name",
            demo=False,
        )
        validate(
            """
                <form string="View attachment">
                    <group groups="base.group_erp_manager" invisible="not display_name">
                        <field name="company_id" invisible="not name" groups="base.group_multi_company"/>
                        <field name="company_id" invisible="not name" groups="base.group_user"/>
                    </group>
                </form>
            """,
            field="name",
            demo=False,
        )
        validate(
            """
                <form string="View attachment">
                    <group groups="base.group_erp_manager" invisible="not display_name">
                        <field name="company_id" invisible="not name" groups="base.group_multi_company"/>
                        <field name="company_id" invisible="not name" groups="base.group_user"/>
                    </group>
                </form>
            """,
            field="display_name",
            demo=False,
        )
        validate(
            """
                <form string="View attachment">
                    <group groups="base.group_user" invisible="not display_name">
                        <field name="company_id" invisible="not name" groups="base.group_multi_company"/>
                        <field name="company_id" invisible="not name" groups="base.group_erp_manager"/>
                    </group>
                </form>
            """,
            field="name",
            demo=False,
        )
        validate(
            """
                <form string="View attachment">
                    <group groups="base.group_user" invisible="not display_name">
                        <field name="company_id" invisible="not name" groups="base.group_multi_company"/>
                        <field name="company_id" invisible="not name" groups="base.group_erp_manager"/>
                    </group>
                </form>
            """,
            field="display_name",
            demo=True,
        )

        validate(
            """
                <form string="View attachment">
                    <field name="name" groups="base.group_user"/>
                    <field name="name" groups="base.group_multi_company"/>

                    <group groups="base.group_erp_manager" invisible="not name">
                        <field name="company_id" invisible="not name" groups="base.group_multi_company"/>
                        <field name="company_id" invisible="not name" groups="base.group_user"/>
                    </group>
                </form>
            """,
            field="name",
            no_add=True,
        )

        validate(
            """
                <form string="View attachment">
                    <field name="access_token" invisible="not name"/>
                </form>
            """,
            field="name",
            demo=True,
        )

    def test_empty_groups_attrib(self):
        view = self.View.create(
            {
                "name": "foo",
                "model": "res.partner",
                "arch": """
                <form>
                    <field name="name" groups="" />
                </form>
            """,
            }
        )
        arch = self.env["res.partner"].get_view(view_id=view.id)["arch"]
        tree = etree.fromstring(arch)
        nodes = tree.xpath("//field[@name='name' and not (@groups)]")
        self.assertEqual(1, len(nodes))

    def test_invisible_groups_with_groups_in_model(self):
        self.patch(self.env.registry["res.partner"].name, "groups", "base.group_system")
        self.env.user.group_ids += self.env.ref("base.group_multi_company")
        view = self.View.create(
            {
                "name": "foo",
                "model": "res.partner",
                "arch": """
                <form>
                    <field name="active"/>
                    <field name="name" groups="base.group_multi_company" invisible="active"/>
                </form>
            """,
            }
        )
        arch = self.env["res.partner"].get_view(view_id=view.id)["arch"]
        tree = etree.fromstring(arch)
        node_field_name = tree.xpath('//field[@name="name"]')[0]
        self.assertEqual(node_field_name.get("invisible"), "active")

    def test_button(self):
        arch = """
            <form>
                <button type="object" name="%s"/>
            </form>
        """
        self.assertValid(arch % "action_archive", name="valid button name")
        self.assertInvalid(
            arch % "wtfzzz",
            "wtfzzz is not a valid action on ir.ui.view",
            name="button name is not even a method",
        )
        self.assertInvalid(
            arch % "_check_xml",
            "_check_xml on ir.ui.view is private and cannot be called from a button",
            name="button name is a private method",
        )
        self.assertWarning(
            arch % "postprocess_and_fields",
            name="button name is a method that requires extra arguments",
        )
        arch = """
            <form>
                <button type="action" name="%s"/>
            </form>
        """
        self.assertInvalid(
            arch % 0,
            "Action 0 (id: 0) does not exist for button of type action.",
        )
        self.assertInvalid(
            arch % "base.random_xmlid",
            "Invalid xmlid base.random_xmlid for button of type action",
        )
        self.assertInvalid(
            '<form><button special="dummy"/></form>',
            "Invalid special 'dummy' in button",
        )
        self.assertInvalid(
            arch % "base.partner_root",
            "base.partner_root is of type res.partner, expected a subclass of ir.actions.actions",
        )

    def test_tree(self):
        arch = """
            <list>
                <field name="name"/>
                <button type='object' name="action_archive"/>
                %s
            </list>
        """
        self.assertValid(arch % "")
        self.assertInvalid(
            arch % "<group/>",
            "List child can only have one of field, button, control, groupby, widget, header tag (not group)",
        )

    def test_tree_groupby(self):
        arch = """
            <list>
                <field name="name"/>
                <groupby name="%s">
                    <button type="object" name="action_archive"/>
                </groupby>
            </list>
        """
        self.assertValid(arch % ("model_data_id"))
        self.assertInvalid(
            arch % ("type"),
            "Field 'type' found in 'groupby' node can only be of type many2one, found selection",
        )
        self.assertInvalid(
            arch % ("dummy"),
            "Field 'dummy' found in 'groupby' node does not exist in model ir.ui.view",
        )

    def test_tree_groupby_many2one(self):
        arch = """
            <list>
                <field name="name"/>
                %s
                <groupby name="model_data_id">
                    %s
                    <button type="object" name="action_archive" invisible="noupdate" string="Button1"/>
                </groupby>
            </list>
        """
        view = self.assertValid(arch % ("", '<field name="noupdate"/>'))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field[@name="noupdate"][@invisible][@readonly]'
            )
        )

        view = self.assertValid(arch % ("", ""))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//groupby/field[@name="noupdate"][@invisible][@readonly]'
            )
        )

        self.assertInvalid(
            arch % ('<field name="noupdate"/>', ""),
            '''Field "noupdate" does not exist in model "ir.ui.view"''',
        )
        self.assertInvalid(
            arch % ("", '<field name="noupdate"/><field name="fake_field"/>'),
            '''Field "fake_field" does not exist in model "ir.model.data"''',
        )

    def test_check_xml_on_reenable(self):
        view1 = self.View.create(
            {
                "name": "valid _check_xml",
                "model": "ir.ui.view",
                "arch": """
                <form string="View">
                    <field name="name"/>
                </form>
            """,
            }
        )
        view2 = self.View.create(
            {
                "name": "valid _check_xml",
                "model": "ir.ui.view",
                "inherit_id": view1.id,
                "active": False,
                "arch": """
                <field name="foo" position="after">
                    <field name="bar"/>
                </field>
            """,
            }
        )
        with self.assertRaises(ValidationError):
            view2.active = True

        view2.write(
            {
                "active": True,
                "arch": """
                <field name="name" position="after">
                    <span>bar</span>
                </field>
            """,
            }
        )

    def test_for_in_label(self):
        self.assertValid('<form><field name="model"/><label for="model"/></form>')
        self.assertInvalid(
            '<form><field name="model"/><label/></form>',
            """Label tag must contain a "for". To match label style without corresponding field or button, use 'class="o_form_label"'""",
        )
        self.assertInvalid(
            '<form><label for="model"/></form>',
            """Name or id “model” in <label for="..."> must be present in view but is missing.""",
        )

    def test_col_colspan_numerical(self):
        self.assertValid('<form><group col="5"></group></form>')
        self.assertInvalid(
            '<form><group col="alpha"></group></form>',
            "“col” value must be an integer (alpha)",
        )
        self.assertValid('<form><div colspan="5"></div></form>')
        self.assertInvalid(
            '<form><div colspan="alpha"></div></form>',
            "“colspan” value must be an integer (alpha)",
        )

    def test_valid_alerts(self):
        self.assertValid('<form><div class="alert alert-success" role="alert"/></form>')
        self.assertValid(
            '<form><div class="alert alert-success" role="alertdialog"/></form>'
        )
        self.assertValid(
            '<form><div class="alert alert-success" role="status"/></form>'
        )
        self.assertWarning('<form><div class="alert alert-success"/></form>')

    def test_valid_prohibited_none_role(self):
        self.assertWarning('<form><div role="none"/></form>')
        self.assertWarning('<form><div role="presentation"/></form>')

    def test_valid_alternative_image_text(self):
        self.assertValid('<form><img src="a" alt="a image"></img></form>')
        self.assertWarning('<form><img src="a"></img></form>')

    def test_valid_accessibility_icon_text(self):
        self.assertWarning(
            '<form><span class="fa-solid fa-triangle-exclamation"/></form>',
            "A <span> with fa class (fa-solid fa-triangle-exclamation) must have title in its tag, parents, descendants or have text",
        )
        self.assertWarning(
            '<form><button icon="fa-warning"/></form>',
            "A button with icon attribute (fa-warning) must have title in its tag, parents, descendants or have text",
        )
        self.assertWarning(
            '<form><span class="fa-solid fa-triangle-exclamation"/><label for="key"/><field name="key"/></form>',
            "A <span> with fa class (fa-solid fa-triangle-exclamation) must have title in its tag, parents, descendants or have text",
        )
        self.assertValid('<form><button icon="fa-warning"/>text</form>')
        self.assertValid(
            '<form><span class="fa-solid fa-triangle-exclamation"/>text</form>'
        )
        self.assertValid(
            '<form><span class="fa-solid fa-triangle-exclamation"/><label for="key" string="Some Text"/><field name="key"/></form>'
        )
        self.assertValid(
            '<form><span class="fa-solid fa-triangle-exclamation"/><field name="key" string="Some Text"/></form>'
        )
        self.assertValid(
            '<form>text<span class="fa-solid fa-triangle-exclamation"/></form>'
        )
        self.assertValid(
            '<form><span class="fa-solid fa-triangle-exclamation">text</span></form>'
        )
        self.assertValid(
            '<form><span title="text" class="fa-solid fa-triangle-exclamation"/></form>'
        )
        self.assertValid(
            '<form><span aria-label="text" class="fa-solid fa-triangle-exclamation"/></form>'
        )

    def test_valid_simili_button(self):
        self.assertWarning('<form><a class="btn"/></form>')
        self.assertValid('<form><a class="btn" role="button"/></form>')

    def test_valid_dialog(self):
        self.assertWarning('<form><div class="modal"/></form>')
        self.assertValid('<form><div role="dialog" class="modal"></div></form>')
        self.assertWarning('<form><div class="modal-header"/></form>')
        self.assertValid('<form><header class="modal-header"/></form>')
        self.assertWarning('<form><div class="modal-footer"/></form>')
        self.assertValid('<form><footer class="modal-footer"/></form>')
        self.assertWarning('<form><div class="modal-body"/></form>')
        self.assertValid('<form><main class="modal-body"/></form>')

    def test_valid_simili_dropdown(self):
        self.assertValid('<form><ul class="dropdown-menu" role="menu"></ul></form>')
        self.assertWarning('<form><ul class="dropdown-menu"></ul></form>')

    def test_valid_simili_progressbar(self):
        self.assertValid(
            '<form><div class="o_progressbar" role="progressbar" aria-valuenow="14" aria-valuemin="0" aria-valuemax="100">14%</div></form>'
        )
        self.assertWarning(
            '<form><div class="o_progressbar" aria-valuenow="14" aria-valuemin="0" aria-valuemax="100">14%</div></form>'
        )
        self.assertWarning(
            '<form><div class="o_progressbar" role="progressbar" aria-valuemin="0" aria-valuemax="100">14%</div></form>'
        )
        self.assertWarning(
            '<form><div class="o_progressbar" role="progressbar" aria-valuenow="14" aria-valuemax="100">14%</div></form>'
        )
        self.assertWarning(
            '<form><div class="o_progressbar" role="progressbar" aria-valuenow="14" aria-valuemin="0" >14%</div></form>',
            expected_message="o_progressbar class must have aria-valuemax attribute",
        )

    def test_valid_simili_tabpanel(self):
        self.assertValid('<form><div class="tab-pane" role="tabpanel"/></form>')
        self.assertWarning('<form><div class="tab-pane"/></form>')

    def test_valid_simili_tablist(self):
        self.assertValid('<form><div class="nav-tabs" role="tablist"/></form>')
        self.assertWarning('<form><div class="nav-tabs"/></form>')

    def test_valid_simili_tab(self):
        self.assertValid(
            '<form><a data-bs-toggle="tab" role="tab" aria-controls="test"/></form>'
        )
        self.assertWarning(
            '<form><a data-bs-toggle="tab" aria-controls="test"/></form>'
        )
        self.assertWarning('<form><a data-bs-toggle="tab" role="tab"/></form>')
        self.assertWarning(
            '<form><a data-bs-toggle="tab" role="tab" aria-controls="#test"/></form>'
        )

    def test_valid_focusable_button(self):
        self.assertValid('<form><a class="btn" role="button"/></form>')
        self.assertValid('<form><button class="btn" role="button"/></form>')
        self.assertValid('<form><select class="btn" role="button"/></form>')
        self.assertValid(
            '<form><input type="button" class="btn" role="button"/></form>'
        )
        self.assertValid(
            '<form><input type="submit" class="btn" role="button"/></form>'
        )
        self.assertValid('<form><input type="reset" class="btn" role="button"/></form>')
        self.assertValid(
            '<form><div type="reset" class="btn btn-group" role="button"/></form>'
        )
        self.assertValid(
            '<form><div type="reset" class="btn btn-toolbar" role="button"/></form>'
        )
        self.assertValid(
            '<form><div type="reset" class="btn btn-addr" role="button"/></form>'
        )
        self.assertWarning('<form><div class="btn" role="button"/></form>')
        self.assertWarning(
            '<form><input type="email" class="btn" role="button"/></form>'
        )

    def test_partial_validation(self):
        self.View = self.View.with_context(load_all_views=True)

        view0 = self.assertValid("""
            <form string="View">
                <field name="model"/>
                <field name="inherit_id" domain="[('model', '=', model)]"/>
            </form>
        """)

        self.assertInvalid(
            """<form position="inside">
                <field name="group_ids" domain="[('invalid_field', '=', 'dummy')]"/>
            </form>""",
            """Unknown field "res.groups.invalid_field" in domain of <field name="group_ids"> ([('invalid_field', '=', 'dummy')]))""",
            inherit_id=view0.id,
        )
        view1 = self.assertValid(
            """<form position="inside">
                <field name="name"/>
            </form>""",
            inherit_id=view0.id,
        )
        view2 = self.assertValid(
            """<form position="inside">
                <field name="group_ids" domain="[('name', '=', name)]"/>
                <label for="group_ids"/>
            </form>""",
            inherit_id=view1.id,
        )

        self.assertInvalid(
            """<field name="inherit_id" position="attributes">
                <attribute name="domain">[('invalid_field', '=', 'dummy')]</attribute>
            </field>""",
            """Unknown field "ir.ui.view.invalid_field" in domain of <field name="inherit_id"> ([('invalid_field', '=', 'dummy')]))""",
            inherit_id=view0.id,
        )

        view_arch = self.View.get_views([(view0.id, "form")])["views"]["form"]["arch"]
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )
        view0bis = None
        view0bis = self.assertValid(
            """<field name="model" position="replace"/>""",
            inherit_id=view0.id,
        )
        view_arch = self.View.get_views([(view0.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )
        view0bis.active = False
        view_arch = self.View.get_views([(view0.id, "form")])["views"]["form"]["arch"]
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )

        self.assertValid(
            """<field name="group_ids" position="before">
                <label for="group_ids" position="move"/>
            </field>""",
            inherit_id=view2.id,
        )

        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field[@name="name"][@invisible][@readonly]'
            )
        )
        view1.arch = """<form position="inside">
            <field name="type"/>
        </form>"""
        view_arch = self.View.get_views([(view0.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//field[@name="name"][@invisible][@readonly]'
            )
        )

    def test_graph_fields(self):
        self.assertValid(
            '<graph string="Graph"><field name="model" type="row"/><field name="inherit_id" type="measure"/></graph>'
        )
        self.assertInvalid(
            '<graph string="Graph"><label for="model"/><field name="model" type="row"/><field name="inherit_id" type="measure"/></graph>',
            "A <graph> can only contains <field> nodes, found a <label>",
        )

    def test_graph_attributes(self):
        self.assertValid(
            '<graph string="Graph" cumulated="1" ><field name="model" type="row"/><field name="inherit_id" type="measure"/></graph>'
        )

    def test_view_ref(self):
        view = self.assertValid("""
                <form>
                    <field name="group_ids" class="canary"/>
                </form>
            """)
        self.env["ir.model.data"].create(
            {
                "module": "base",
                "name": "test_views_test_view_ref",
                "model": "ir.ui.view",
                "res_id": view.id,
            }
        )
        view_data = (
            self.env["ir.ui.view"]
            .with_context(form_view_ref="base.test_views_test_view_ref")
            .get_view()
        )
        self.assertEqual(
            view.id,
            view_data["id"],
            "The view returned should be test_views_test_view_ref",
        )
        view_data = (
            self.env["ir.ui.view"]
            .with_context(form_view_ref="base.test_views_test_view_ref")
            .get_view(view.id)
        )
        tree = etree.fromstring(view_data["arch"])
        field_groups_id = tree.xpath('//field[@name="group_ids"]')[0]
        self.assertEqual(
            len(field_groups_id.xpath(".//*[@class='canary']")),
            0,
            "The view test_views_test_view_ref should not be in the views of the many2many field all_group_ids",
        )

    def test_forbidden_owl_directives_in_form(self):
        arch = "<form>%s</form>"

        self.assertInvalid(
            arch % ('<span t-esc="x"/>'),
            """Error while validating view near:

<form __validate__="1"><span t-esc="x"/></form>
Forbidden owl directive used in arch (t-esc).""",
        )

        self.assertInvalid(
            arch % ('<span t-on-click="x.doIt()"/>'),
            """Error while validating view near:

<form __validate__="1"><span t-on-click="x.doIt()"/></form>
Forbidden owl directive used in arch (t-on-click).""",
        )

    @mute_logger("odoo.addons.base.models.ir_ui_view")
    def test_forbidden_owl_directives_in_kanban(self):
        arch = "<kanban><templates><t t-name='card'>%s</t></templates></kanban>"
        self.assertValid(arch % ('<span t-esc="record.resId"/>'))
        self.assertValid(arch % ('<t t-debug=""/>'))

        self.assertInvalid(
            arch % ('<span t-on-click="x.doIt()"/>'),
            """Error while validating view near:

<kanban __validate__="1"><templates><t t-name="card"><span t-on-click="x.doIt()"/></t></templates></kanban>
Forbidden owl directive used in arch (t-on-click).""",
        )

    @mute_logger("odoo.addons.base.models.ir_ui_view")
    def test_forbidden_data_tooltip_attributes_in_form(self):
        arch = "<form>%s</form>"

        self.assertInvalid(
            arch % ('<span data-tooltip="Test"/>'),
            """Error while validating view near:

<form __validate__="1"><span data-tooltip="Test"/></form>
Forbidden attribute used in arch (data-tooltip).""",
        )

        self.assertInvalid(
            arch % ('<span data-tooltip-template="test"/>'),
            """Error while validating view near:

<form __validate__="1"><span data-tooltip-template="test"/></form>
Forbidden attribute used in arch (data-tooltip-template).""",
        )

    @mute_logger("odoo.addons.base.models.ir_ui_view")
    def test_forbidden_data_tooltip_attributes_in_kanban(self):
        arch = "<kanban><templates><t t-name='card'>%s</t></templates></kanban>"

        self.assertInvalid(
            arch % ('<span data-tooltip="Test"/>'),
            """Error while validating view near:

<kanban __validate__="1"><templates><t t-name="card"><span data-tooltip="Test"/></t></templates></kanban>
Forbidden attribute used in arch (data-tooltip).""",
        )

        self.assertInvalid(
            arch % ('<span data-tooltip-template="test"/>'),
            """Error while validating view near:

<kanban __validate__="1"><templates><t t-name="card"><span data-tooltip-template="test"/></t></templates></kanban>
Forbidden attribute used in arch (data-tooltip-template).""",
        )

        self.assertInvalid(
            arch % ('<span t-att-data-tooltip="test"/>'),
            """Error while validating view near:

<kanban __validate__="1"><templates><t t-name="card"><span t-att-data-tooltip="test"/></t></templates></kanban>
Forbidden attribute used in arch (t-att-data-tooltip).""",
        )

        self.assertInvalid(
            arch % ('<span t-attf-data-tooltip-template="{{ test }}"/>'),
            """Error while validating view near:

<kanban __validate__="1"><templates><t t-name="card"><span t-attf-data-tooltip-template="{{ test }}"/></t></templates></kanban>
Forbidden attribute used in arch (t-attf-data-tooltip-template).""",
        )

    @mute_logger("odoo.addons.base.models.ir_ui_view")
    def test_forbidden_use_of___comp___in_kanban(self):
        arch = "<kanban><templates><t t-name='card'>%s</t></templates></kanban>"
        self.assertInvalid(
            arch % '<t t-esc="__comp__.props.resId"/>',
            """Error while validating view near:

<kanban __validate__="1"><templates><t t-name="card"><t t-esc="__comp__.props.resId"/></t></templates></kanban>
Forbidden use of `__comp__` in arch.""",
        )

    @mute_logger("odoo.addons.base.models.ir_ui_view")
    def test_check_primary_when_update_siblins_inherited_tree(self):
        View = self.env["ir.ui.view"]
        p1 = View.create(
            {
                "name": "test_view_p1",
                "type": "qweb",
                "key": "website.test_view_p1",
                "arch_db": """<div><p1/></div>""",
            }
        )
        View.create(
            {
                "name": "test_view_e1",
                "mode": "extension",
                "inherit_id": p1.id,
                "arch_db": '<div position="inside"><e1/></div>',
                "key": "website.test_view_e1",
            }
        )
        e2 = View.create(
            {
                "name": "test_view_e2",
                "mode": "extension",
                "inherit_id": p1.id,
                "arch_db": '<div position="inside"><e2/></div>',
                "key": "website.test_view_e2",
            }
        )
        View.create(
            {
                "name": "test_view_e3",
                "mode": "extension",
                "inherit_id": p1.id,
                "arch_db": '<div position="inside"><e3/></div>',
                "key": "website.test_view_e3",
            }
        )
        e4 = View.create(
            {
                "name": "test_view_e4",
                "mode": "extension",
                "inherit_id": p1.id,
                "arch_db": '<div position="inside"><e4/></div>',
                "key": "website.test_view_e4",
            }
        )
        p2 = View.create(
            {
                "name": "test_view_p2",
                "mode": "primary",
                "inherit_id": e2.id,
                "arch_db": '<e4 position="replace"><p2/></e4>',
                "key": "website.test_view_p2",
                "active": False,
            }
        )
        View.create(
            {
                "name": "test_view_e5",
                "mode": "extension",
                "inherit_id": p1.id,
                "arch_db": '<div position="inside"><e5/></div>',
                "key": "website.test_view_e5",
            }
        )

        self.assertEqual(
            self.env["ir.qweb"]._render(p1.id),
            "<div><p1></p1><e1></e1><e2></e2><e3></e3><e4></e4><e5></e5></div>",
        )
        e4.active = False
        self.assertEqual(
            self.env["ir.qweb"]._render(p1.id),
            "<div><p1></p1><e1></e1><e2></e2><e3></e3><e5></e5></div>",
        )

        with self.assertRaises(ValidationError) as catcher:
            p2.active = True
        self.assertIn(
            "Element '<e4>' cannot be located in parent view",
            str(catcher.exception.args[0]),
        )

        e4.active = True
        p2.active = True
        self.assertEqual(
            self.env["ir.qweb"]._render(p1.id),
            "<div><p1></p1><e1></e1><e2></e2><e3></e3><e4></e4><e5></e5></div>",
        )
        self.assertEqual(
            self.env["ir.qweb"]._render(p2.id),
            "<div><p1></p1><e1></e1><e2></e2><e3></e3><p2></p2><e5></e5></div>",
        )

        with self.assertRaises(ValidationError) as catcher:
            e4.active = False
        self.assertIn(
            "Element '<e4>' cannot be located in parent view",
            str(catcher.exception.args[0]),
        )

        with self.assertRaises(ValidationError) as catcher:
            View.create(
                {
                    "name": "test_view_e6",
                    "mode": "extension",
                    "inherit_id": e2.id,
                    "arch_db": '<e4 position="replace"><e6/></e4>',
                    "key": "website.test_view_e6",
                }
            )
        self.assertIn(
            "Element '<e4>' cannot be located in parent view",
            str(catcher.exception.args[0]),
        )

    def test_customization_dropped_only_on_arch_impacting_write(self):
        Custom = self.env["ir.ui.view.custom"]

        def make():
            view = self.View.create(
                {
                    "name": "cust_base",
                    "model": "ir.ui.view",
                    "arch": '<form><field name="name"/></form>',
                }
            )
            custom = Custom.create(
                {
                    "ref_id": view.id,
                    "user_id": self.env.uid,
                    "arch": '<form><field name="name"/></form>',
                }
            )
            return view, custom

        view, custom = make()
        view.write({"name": "renamed"})
        self.assertTrue(custom.exists(), "name write must preserve customization")

        view, custom = make()
        view.write({"arch_fs": "base/foo.xml"})
        self.assertTrue(custom.exists(), "arch_fs write must preserve customization")

        view, custom = make()
        view.write(
            {"arch": '<form><field name="name"/><field name="create_uid"/></form>'}
        )
        self.assertFalse(custom.exists(), "arch write must drop customization")

        view, custom = make()
        view.write({"priority": 42})
        self.assertFalse(custom.exists(), "priority write must drop customization")

    def test_calendar_aggregate_field_is_validated(self):
        self.View.create(
            {
                "name": "cal ok",
                "model": "res.users",
                "arch": '<calendar date_start="login_date" aggregate="id:count">'
                '<field name="name"/></calendar>',
            }
        )
        with mute_logger("odoo.addons.base.models.ir_ui_view"):
            with self.assertRaises(ValidationError):
                self.View.create(
                    {
                        "name": "cal bad",
                        "model": "res.users",
                        "arch": '<calendar date_start="login_date" '
                        'aggregate="nonexistent_field:count">'
                        '<field name="name"/></calendar>',
                    }
                )


@tagged("post_install", "-at_install")
class TestDebugger(common.TransactionCase):
    def test_t_debug_in_qweb_based_views(self):
        View = self.env["ir.ui.view"]
        views_with_t_debug = View.search([["arch_db", "like", "t-debug="]])
        self.assertEqual([v.xml_id for v in views_with_t_debug], [])


class TestViewTranslations(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.lang"]._activate_lang("fr_FR")
        cls.env["res.lang"]._activate_lang("nl_NL")
        cls.env["ir.module.module"]._load_module_terms(["base"], ["fr_FR", "nl_NL"])

    def create_view(self, archf, terms, **kwargs):
        view = self.env["ir.ui.view"].create(
            {
                "name": "test",
                "model": "res.partner",
                "arch": archf % terms,
            }
        )
        self.env.flush_all()
        val = {"en_US": archf % terms}
        for lang, trans_terms in kwargs.items():
            val[lang] = archf % trans_terms
        query = "UPDATE ir_ui_view SET arch_db = %s WHERE id = %s"
        self.env.cr.execute(query, [Json(val), view.id])
        self.env.invalidate_all()
        return view

    def test_sync(self):
        archf = '<form string="X">%s</form>'
        terms_en = ("Bread and cheeze",)
        terms_fr = ("Pain et fromage",)
        terms_nl = ("Brood and kaas",)
        view = self.create_view(
            archf, terms_en, en_US=terms_en, fr_FR=terms_fr, nl_NL=terms_nl
        )

        env_nolang = self.env(context={})
        env_en = self.env(context={"lang": "en_US"})
        env_fr = self.env(context={"lang": "fr_FR"})
        env_nl = self.env(context={"lang": "nl_NL"})

        self.assertEqual(view.with_env(env_nolang).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_en).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_fr).arch, archf % terms_fr)
        self.assertEqual(view.with_env(env_nl).arch, archf % terms_nl)

        terms_en = ("Bread and cheese",)
        view.with_env(env_en).write({"arch": archf % terms_en})

        self.assertEqual(view.with_env(env_nolang).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_en).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_fr).arch, archf % terms_fr)
        self.assertEqual(view.with_env(env_nl).arch, archf % terms_nl)

        view = self.create_view(
            archf, terms_fr, en_US=terms_en, fr_FR=terms_fr, nl_NL=terms_nl
        )
        new_terms_fr = ("Pains et fromage",)
        view.with_env(env_fr).write({"arch": archf % new_terms_fr})

        self.assertEqual(view.with_env(env_nolang).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_en).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_fr).arch, archf % new_terms_fr)
        self.assertEqual(view.with_env(env_nl).arch, archf % terms_nl)

    def test_sync_xml(self):
        archf = '<form string="X">%s</form>'
        terms_en = ("Bread and cheese",)
        terms_fr = ("Pain et fromage",)
        terms_nl = ("Brood and kaas",)
        view = self.create_view(
            archf, terms_en, en_US=terms_en, fr_FR=terms_fr, nl_NL=terms_nl
        )

        env_nolang = self.env(context={})
        env_en = self.env(context={"lang": "en_US"})
        env_fr = self.env(context={"lang": "fr_FR"})
        env_nl = self.env(context={"lang": "nl_NL"})

        self.assertEqual(view.with_env(env_nolang).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_en).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_fr).arch, archf % terms_fr)
        self.assertEqual(view.with_env(env_nl).arch, archf % terms_nl)

        terms_en = ('Bread <span style="font-weight:bold">and</span> cheese',)
        view.with_env(env_en).write({"arch": archf % terms_en})

        self.assertEqual(view.with_env(env_nolang).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_en).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_fr).arch, archf % terms_fr)
        self.assertEqual(view.with_env(env_nl).arch, archf % terms_nl)

        terms_en = ('Bread <span style="font-weight:bold">and</span> butter',)
        view.with_env(env_en).write({"arch": archf % terms_en})

        self.assertEqual(view.with_env(env_nolang).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_en).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_fr).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_nl).arch, archf % terms_en)

    def test_sync_update(self):
        archf = '<form string="X"><div>%s</div><div>%s</div></form>'
        terms_src = ("Subtotal", "Subtotal:")
        terms_en = ("", "Sub total:")
        view = self.create_view(archf, terms_src, en_US=terms_en)

        new_arch = archf % ("Subtotal", "Subtotal : <br/>")
        view.write({"arch": new_arch})
        self.assertEqual(view.arch, new_arch)

    def test_cache_consistency(self):
        view = self.env["ir.ui.view"].create(
            {
                "name": "test_translate_xml_cache_invalidation",
                "model": "res.partner",
                "arch": "<form><b>content</b></form>",
            }
        )
        view_fr = view.with_context({"lang": "fr_FR"})
        self.assertIn("<b>", view.arch_db)
        self.assertIn("<b>", view.arch)
        self.assertIn("<b>", view_fr.arch_db)
        self.assertIn("<b>", view_fr.arch)

        view.write({"arch": "<form><i>content</i></form>"})
        self.assertIn("<i>", view.arch_db)
        self.assertIn("<i>", view.arch)
        self.assertIn("<i>", view_fr.arch_db)
        self.assertIn("<i>", view_fr.arch)

    def test_no_groups_for_inherited(self):
        parent = self.env["ir.ui.view"].create(
            {
                "name": "test_no_groups_for_inherited_parent",
                "model": "ir.ui.view",
                "arch": "<form></form>",
            }
        )

        view = self.env["ir.ui.view"].create(
            {
                "name": "test_no_groups_for_inherited_child",
                "model": "ir.ui.view",
                "arch": "<data></data>",
                "inherit_id": parent.id,
                "mode": "extension",
            }
        )

        with self.assertRaises(ValidationError):
            view.write({"group_ids": [1]})

        view.write({"mode": "primary"})
        view.write({"group_ids": [1]})

        with self.assertRaises(ValidationError):
            view.write({"mode": "extension"})


class ViewModeField(ViewCase):
    def test_mode_implicit_value(self):
        view = self.View.create({"inherit_id": None, "arch": "<qweb/>"})
        self.assertEqual(view.mode, "primary")

        view2 = self.View.create({"inherit_id": view.id, "arch": "<qweb/>"})
        self.assertEqual(view2.mode, "extension")

        view2.write({"inherit_id": None})
        self.assertEqual(view2.mode, "primary")

        view2.write({"inherit_id": view.id})
        self.assertEqual(view2.mode, "extension")

    @mute_logger("odoo.db")
    def test_mode_explicit(self):
        view = self.View.create({"inherit_id": None, "arch": "<qweb/>"})
        view2 = self.View.create(
            {"inherit_id": view.id, "mode": "primary", "arch": "<qweb/>"}
        )
        self.assertEqual(view.mode, "primary")
        self.assertEqual(view2.mode, "primary")

        with self.assertRaises(IntegrityError):
            self.View.create(
                {"inherit_id": None, "mode": "extension", "arch": "<qweb/>"}
            )

    @mute_logger("odoo.db")
    def test_pure_primary_to_extension(self):
        view_pure_primary = self.View.create({"inherit_id": None, "arch": "<qweb/>"})
        with self.assertRaises(IntegrityError):
            view_pure_primary.write({"mode": "extension"})
            view_pure_primary.env.flush_all()

    def test_inherit_primary_to_extension(self):
        base = self.View.create(
            {
                "inherit_id": None,
                "arch": "<qweb/>",
            }
        )
        view = self.View.create(
            {"inherit_id": base.id, "mode": "primary", "arch": "<qweb/>"}
        )

        view.write({"mode": "extension"})

    def test_default_extension_to_primary(self):
        base = self.View.create(
            {
                "inherit_id": None,
                "arch": "<qweb/>",
            }
        )
        view = self.View.create({"inherit_id": base.id, "arch": "<qweb/>"})

        view.write({"mode": "primary"})

    def test_change_inherit_of_primary(self):
        base1 = self.View.create(
            {
                "inherit_id": None,
                "arch": "<qweb/>",
            }
        )
        base2 = self.View.create(
            {
                "inherit_id": None,
                "arch": "<qweb/>",
            }
        )
        view = self.View.create(
            {
                "mode": "primary",
                "inherit_id": base1.id,
                "arch": "<qweb/>",
            }
        )
        self.assertEqual(view.mode, "primary")
        view.write({"inherit_id": base2.id})
        self.assertEqual(view.mode, "primary")

    def test_mode_defaults_per_view_in_a_mixed_batch(self):
        base1 = self.View.create({"arch": "<qweb/>"})
        base2 = self.View.create({"arch": "<qweb/>"})
        fresh = self.View.create({"arch": "<qweb/>"})
        inheriting = self.View.create(
            {"mode": "primary", "inherit_id": base1.id, "arch": "<qweb/>"}
        )
        (fresh + inheriting).write({"inherit_id": base2.id})
        self.assertEqual(fresh.mode, "extension")
        self.assertEqual(inheriting.mode, "primary")
        self.assertEqual((fresh + inheriting).inherit_id, base2)


class TestDefaultView(ViewCase):
    def test_default_view_base(self):
        self.View.create(
            {
                "inherit_id": False,
                "priority": 10,
                "mode": "primary",
                "arch": "<qweb/>",
            }
        )
        view2 = self.View.create(
            {
                "inherit_id": False,
                "priority": 1,
                "mode": "primary",
                "arch": "<qweb/>",
            }
        )

        default = self.View.default_view(False, "qweb")
        self.assertEqual(
            default,
            view2.id,
            "default_view should get the view with the lowest priority for a (model, view_type) pair",
        )

    def test_default_view_primary(self):
        view1 = self.View.create(
            {
                "inherit_id": False,
                "priority": 10,
                "mode": "primary",
                "arch": "<qweb/>",
            }
        )
        self.View.create(
            {
                "inherit_id": False,
                "priority": 5,
                "mode": "primary",
                "arch": "<qweb/>",
            }
        )
        view3 = self.View.create(
            {
                "inherit_id": view1.id,
                "priority": 1,
                "mode": "primary",
                "arch": "<qweb/>",
            }
        )

        default = self.View.default_view(False, "qweb")
        self.assertEqual(
            default,
            view3.id,
            "default_view should get the view with the lowest priority for "
            "a (model, view_type) pair in all the primary tables",
        )

    def test_default_list_view(self):
        arch = self.View._get_default_list_view()
        self.assertEqual(arch.tag, "list")
        self.assertEqual(arch.get("string"), self.View._description)
        fields = arch.findall("field")
        self.assertEqual([f.get("name") for f in fields], ["name"])

    def test_default_search_view(self):
        arch = self.View._get_default_search_view()
        self.assertEqual(arch.tag, "search")
        self.assertEqual([f.get("name") for f in arch.findall("field")], ["name"])

    def test_default_kanban_view(self):
        arch = self.View._get_default_kanban_view()
        self.assertEqual(arch.tag, "kanban")
        card = arch.find('templates/t[@t-name="card"]')
        self.assertIsNotNone(card, "kanban should embed a 'card' template")
        self.assertEqual([f.get("name") for f in card.findall("field")], ["name"])

    def test_default_pivot_view(self):
        arch = self.View._get_default_pivot_view()
        self.assertEqual(arch.tag, "pivot")
        self.assertEqual(arch.get("string"), self.View._description)
        self.assertEqual(len(arch), 0, "default pivot view should have no children")

    def test_default_graph_view(self):
        arch = self.View._get_default_graph_view()
        self.assertEqual(arch.tag, "graph")
        self.assertEqual([f.get("name") for f in arch.findall("field")], ["name"])

    def test_calendar_view_missing_date_start(self):
        with self.assertRaises(UserError):
            self.View._get_default_calendar_view()

    def test_calendar_view_missing_stop_and_delay(self):
        self.patch(type(self.View), "_date_name", "name")
        with self.assertRaises(UserError):
            self.View._get_default_calendar_view()

    def test_get_view_is_readonly(self):
        View = type(self.env["ir.ui.view"])
        self.assertTrue(
            api.is_readonly(View, "get_view"),
            "get_view should carry @api.readonly (read/write split)",
        )
        self.assertTrue(api.is_readonly(View, "get_views"))
        self.assertFalse(api.is_readonly(View, "write"))


class TestViewCombined(ViewCase):
    def setUp(self):
        super().setUp()

        self.a1 = self.View.create({"model": "a", "arch": "<qweb><a1/></qweb>"})
        self.a2 = self.View.create(
            {
                "model": "a",
                "inherit_id": self.a1.id,
                "priority": 5,
                "arch": '<xpath expr="//a1" position="after"><a2/></xpath>',
            }
        )
        self.a3 = self.View.create(
            {
                "model": "a",
                "inherit_id": self.a1.id,
                "arch": '<xpath expr="//a1" position="after"><a3/></xpath>',
            }
        )
        self.a4 = self.View.create(
            {
                "model": "a",
                "inherit_id": self.a1.id,
                "mode": "primary",
                "arch": '<xpath expr="//a1" position="after"><a4/></xpath>',
            }
        )

        self.b1 = self.View.create(
            {
                "model": "b",
                "inherit_id": self.a3.id,
                "mode": "primary",
                "arch": '<xpath expr="//a1" position="after"><b1/></xpath>',
            }
        )
        self.b2 = self.View.create(
            {
                "model": "b",
                "inherit_id": self.b1.id,
                "arch": '<xpath expr="//a1" position="after"><b2/></xpath>',
            }
        )

        self.c1 = self.View.create(
            {
                "model": "c",
                "inherit_id": self.a1.id,
                "mode": "primary",
                "arch": '<xpath expr="//a1" position="after"><c1/></xpath>',
            }
        )
        self.c2 = self.View.create(
            {
                "model": "c",
                "inherit_id": self.c1.id,
                "priority": 5,
                "arch": '<xpath expr="//a1" position="after"><c2/></xpath>',
            }
        )
        self.c3 = self.View.create(
            {
                "model": "c",
                "inherit_id": self.c2.id,
                "priority": 10,
                "arch": '<xpath expr="//a1" position="after"><c3/></xpath>',
            }
        )

        self.d1 = self.View.create(
            {
                "model": "d",
                "inherit_id": self.b1.id,
                "mode": "primary",
                "arch": '<xpath expr="//a1" position="after"><d1/></xpath>',
            }
        )

    def test_basic_read(self):
        context = {"check_view_ids": self.View.search([]).ids}
        arch = self.a1.with_context(context).get_combined_arch()
        self.assertEqual(
            etree.fromstring(arch),
            E.qweb(
                E.a1(),
                E.a3(),
                E.a2(),
            ),
            arch,
        )

    def test_read_from_child(self):
        context = {"check_view_ids": self.View.search([]).ids}
        arch = self.a3.with_context(context).get_combined_arch()
        self.assertEqual(
            etree.fromstring(arch),
            E.qweb(
                E.a1(),
                E.a3(),
                E.a2(),
            ),
            arch,
        )

    def test_read_from_child_primary(self):
        context = {"check_view_ids": self.View.search([]).ids}
        arch = self.a4.with_context(context).get_combined_arch()
        self.assertEqual(
            etree.fromstring(arch),
            E.qweb(
                E.a1(),
                E.a4(),
                E.a3(),
                E.a2(),
            ),
            arch,
        )

    def test_cross_model_simple(self):
        context = {"check_view_ids": self.View.search([]).ids}
        arch = self.c2.with_context(context).get_combined_arch()
        self.assertEqual(
            etree.fromstring(arch),
            E.qweb(
                E.a1(),
                E.c3(),
                E.c2(),
                E.c1(),
                E.a3(),
                E.a2(),
            ),
            arch,
        )

    def test_cross_model_double(self):
        context = {"check_view_ids": self.View.search([]).ids}
        arch = self.d1.with_context(context).get_combined_arch()
        self.assertEqual(
            etree.fromstring(arch),
            E.qweb(
                E.a1(),
                E.d1(),
                E.b2(),
                E.b1(),
                E.a3(),
                E.a2(),
            ),
            arch,
        )

    def test_primary_after_extensions(self):
        a = self.View.create(
            {
                "model": "a",
                "arch": "<qweb><a/></qweb>",
            }
        )
        b = self.View.create(
            {
                "model": "a",
                "inherit_id": a.id,
                "arch": '<a position="after"><b/></a>',
            }
        )
        self.View.create(
            {
                "model": "a",
                "inherit_id": a.id,
                "arch": '<a position="after"><c/></a>',
            }
        )
        self.View.create(
            {
                "model": "a",
                "inherit_id": b.id,
                "mode": "primary",
                "arch": '<a position="replace"/>',
            }
        )

    def test_inherit_python_expression(self):
        main_view = self.View.create(
            {
                "model": "res.partner",
                "arch": """
                <form>
                    <sheet>
                        <field name="name"/>
                    </sheet>
                </form>""",
            }
        )

        def test_inherit(arch, result):
            view = self.View.create(
                {
                    "model": "res.partner",
                    "inherit_id": main_view.id,
                    "mode": "primary",
                    "arch": arch,
                }
            )
            python_expr = etree.fromstring(view.get_combined_arch())[0][0].get(
                "invisible"
            )
            self.assertEqual(python_expr, result)

        test_inherit(
            """
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">name == 'a'</attribute>
                </xpath>
            </data>
        """,
            "name == 'a'",
        )

        test_inherit(
            """
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">name == 'a'</attribute>
                </xpath>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">True</attribute>
                </xpath>
            </data>
        """,
            "True",
        )

        test_inherit(
            """
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">name == 'a'</attribute>
                </xpath>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible" add="name == 'b'" separator="or"/>
                </xpath>
            </data>
        """,
            "(name == 'a') or (name == 'b')",
        )

        test_inherit(
            """
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">name == 'e' and name == 'f'</attribute>
                    <attribute name="invisible" add="id == 33" separator="and"/>
                </xpath>
            </data>
        """,
            "(name == 'e' and name == 'f') and (id == 33)",
        )

        test_inherit(
            """
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">name == 'e' and name == 'f'</attribute>
                    <attribute name="invisible" add="id == 33" separator="and"/>
                    <attribute name="invisible" add="id == 42" separator="or"/>
                    <attribute name="invisible" add="id == 1" separator=" and "/>
                </xpath>
            </data>
        """,
            "(((name == 'e' and name == 'f') and (id == 33)) or (id == 42)) and (id == 1)",
        )

        test_inherit(
            """
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">id == 1</attribute>
                    <attribute name="invisible" add="id == 2" separator="and"/>
                    <attribute name="invisible" add="id == 3" separator="and"/>
                    <attribute name="invisible" add="id == 4" separator="and"/>
                </xpath>
            </data>
        """,
            "(((id == 1) and (id == 2)) and (id == 3)) and (id == 4)",
        )

        test_inherit(
            """
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">(((id == 1) and (id == 2)) and (id == 3)) and (id == 4)</attribute>
                    <attribute name="invisible" remove="id == 2" separator="and"/>
                </xpath>
            </data>
        """,
            "(((id == 1)) and (id == 3)) and (id == 4)",
        )

        test_inherit(
            """
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">(id == 1) and (id == 2) and (id == 3)</attribute>
                    <attribute name="invisible" remove="id == 2" separator="and"/>
                </xpath>
            </data>
        """,
            "(id == 1) and (id == 3)",
        )

        test_inherit(
            """
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">(((id == 1) and (id == 2)) and (id == 3)) and (id == 4)</attribute>
                    <attribute name="invisible" remove="id == 3" separator="and"/>
                </xpath>
            </data>
        """,
            "(((id == 1) and (id == 2))) and (id == 4)",
        )

        test_inherit(
            """
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">id == 1</attribute>
                    <attribute name="invisible" add="id == 2" separator="and"/>
                    <attribute name="invisible" remove="id == 2" separator="and"/>
                    <attribute name="invisible" remove="id == 1" separator="and"/>
                </xpath>
            </data>
        """,
            None,
        )

        test_inherit(
            """
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">id == 1</attribute>
                    <attribute name="invisible" add="id == 2" separator="and"/>
                    <attribute name="invisible" add="id == 3" separator="and"/>
                    <attribute name="invisible" add="id == 4" separator="and"/>
                    <attribute name="invisible" remove="id == 3" separator="and"/>
                </xpath>
            </data>
        """,
            "(((id == 1) and (id == 2))) and (id == 4)",
        )

        test_inherit(
            """
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">(((id == 1) and (id == 2)) and (id == 3)) and (id == 4)</attribute>
                    <attribute name="invisible" remove="id == 3" separator="and"/>
                    <attribute name="invisible" remove="NO_MATCH" separator="and"/>
                </xpath>
            </data>
        """,
            "(((id == 1) and (id == 2))) and (id == 4)",
        )

        test_inherit(
            """
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">id == 1</attribute>
                    <attribute name="invisible" add="id == 2" separator="and"/>
                    <attribute name="invisible" remove="id == 2" separator="and"/>
                    <attribute name="invisible" remove="id == 1" add="name" separator="and"/>
                </xpath>
            </data>
        """,
            "name",
        )

        test_inherit(
            """
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">id == 1</attribute>
                    <attribute name="invisible" add="id == 2" separator="and"/>
                    <attribute name="invisible" remove="id == 2" add="name == 'foo'" separator="and"/>
                    <attribute name="invisible" add="name" separator="and"/>
                </xpath>
            </data>
        """,
            "(((id == 1)) and (name == 'foo')) and (name)",
        )

        test_inherit(
            """
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">1 or not name</attribute>
                    <attribute name="invisible" remove="1" separator="or"/>
                </xpath>
            </data>
        """,
            "not name",
        )

        test_inherit(
            """
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">1 or not name</attribute>
                    <attribute name="invisible" add="id == 2" separator="and"/>
                    <attribute name="invisible" remove="1" separator="or"/>
                    <attribute name="invisible" remove="not name" separator="and"/>
                </xpath>
            </data>
        """,
            "(id == 2)",
        )

        test_inherit(
            """
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">1 or not name</attribute>
                    <attribute name="invisible" add="id == 2" separator="and"/>
                    <attribute name="invisible" remove="1" separator="or"/>
                </xpath>
            </data>
        """,
            "(not name) and (id == 2)",
        )

        self.assertInvalid(
            """ <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible" position="add">True</attribute>
                </xpath>
            </data> """,
            "Invalid attributes 'position' in element <attribute>",
            inherit_id=main_view.id,
            model=main_view.model,
        )

        self.assertInvalid(
            """ <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible" add="True">text</attribute>
                </xpath>
            </data> """,
            "Element <attribute> with 'add' or 'remove' cannot contain text 'text'",
            inherit_id=main_view.id,
            model=main_view.model,
        )

        self.assertInvalid(
            """ <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">id == 1</attribute>
                    <attribute name="invisible" add="id == 2" separator="else"/>
                </xpath>
            </data> """,
            "Invalid separator 'else' for python expression 'invisible'; valid values are 'and' and 'or'",
            inherit_id=main_view.id,
            model=main_view.model,
        )

    def test_multi_combine(self):
        n1 = self.View.create({"model": "a", "arch": "<qweb><n1/></qweb>"})
        self.View.create(
            {
                "model": "a",
                "inherit_id": n1.id,
                "priority": 5,
                "arch": '<xpath expr="//n1" position="after"><n2/></xpath>',
            }
        )
        n3 = self.View.create(
            {
                "model": "a",
                "inherit_id": n1.id,
                "priority": 1,
                "arch": '<xpath expr="//n1" position="after"><n3/></xpath>',
            }
        )
        n4 = self.View.create(
            {
                "model": "a",
                "inherit_id": n3.id,
                "mode": "primary",
                "arch": '<xpath expr="//n1" position="after"><n4/></xpath>',
            }
        )

        arch_a4 = self.a4.get_combined_arch()
        arch_n4 = n4.get_combined_arch()
        trees = (self.a4 + n4)._get_combined_archs()
        self.assertEqual(
            {
                k: etree.tostring(tree, encoding="unicode")
                for k, tree in zip(["a4", "n4"], trees, strict=False)
            },
            {"a4": arch_a4, "n4": arch_n4},
        )

    def test_multi_combine_with_same_ancestor(self):
        arch_a4 = self.a4.get_combined_arch()
        arch_c2 = self.c2.get_combined_arch()
        trees = (self.a4 + self.c2)._get_combined_archs()
        self.assertEqual(
            {
                k: etree.tostring(tree, encoding="unicode")
                for k, tree in zip(["a4", "c2"], trees, strict=False)
            },
            {"a4": arch_a4, "c2": arch_c2},
        )


class TestOptionalViews(ViewCase):
    def setUp(self):
        super().setUp()
        self.v0 = self.View.create(
            {
                "model": "a",
                "arch": "<qweb><base/></qweb>",
            }
        )
        self.v1 = self.View.create(
            {
                "model": "a",
                "inherit_id": self.v0.id,
                "active": True,
                "priority": 10,
                "arch": '<xpath expr="//base" position="after"><v1/></xpath>',
            }
        )
        self.v2 = self.View.create(
            {
                "model": "a",
                "inherit_id": self.v0.id,
                "active": True,
                "priority": 9,
                "arch": '<xpath expr="//base" position="after"><v2/></xpath>',
            }
        )
        self.v3 = self.View.create(
            {
                "model": "a",
                "inherit_id": self.v0.id,
                "active": False,
                "priority": 8,
                "arch": '<xpath expr="//base" position="after"><v3/></xpath>',
            }
        )

    def test_applied(self):
        context = {"check_view_ids": self.View.search([]).ids}
        arch = self.v0.with_context(context).get_combined_arch()
        self.assertEqual(
            etree.fromstring(arch),
            E.qweb(
                E.base(),
                E.v1(),
                E.v2(),
            ),
        )

    def test_applied_state_toggle(self):
        self.v2.action_archive()
        context = {"check_view_ids": self.View.search([]).ids}
        arch = self.v0.with_context(context).get_combined_arch()
        self.assertEqual(
            etree.fromstring(arch),
            E.qweb(
                E.base(),
                E.v1(),
            ),
        )

        self.v3.action_unarchive()
        context = {"check_view_ids": self.View.search([]).ids}
        arch = self.v0.with_context(context).get_combined_arch()
        self.assertEqual(
            etree.fromstring(arch),
            E.qweb(
                E.base(),
                E.v1(),
                E.v3(),
            ),
        )

        self.v2.action_unarchive()
        context = {"check_view_ids": self.View.search([]).ids}
        arch = self.v0.with_context(context).get_combined_arch()
        self.assertEqual(
            etree.fromstring(arch),
            E.qweb(
                E.base(),
                E.v1(),
                E.v2(),
                E.v3(),
            ),
        )


class TestXPathExtentions(common.BaseCase):
    def test_hasclass(self):
        tree = E.node(
            E.node({"class": "foo bar baz"}),
            E.node({"class": "foo bar"}),
            {"class": "foo"},
        )

        self.assertEqual(len(tree.xpath('//node[hasclass("foo")]')), 3)
        self.assertEqual(len(tree.xpath('//node[hasclass("bar")]')), 2)
        self.assertEqual(len(tree.xpath('//node[hasclass("baz")]')), 1)
        self.assertEqual(
            len(tree.xpath('//node[hasclass("foo")][not(hasclass("bar"))]')), 1
        )
        self.assertEqual(len(tree.xpath('//node[hasclass("foo", "baz")]')), 1)


class TestQWebRender(ViewCase):
    def test_render(self):
        view1 = self.View.create(
            {
                "name": "dummy",
                "type": "qweb",
                "arch": """
                <t t-name="base.dummy">
                    <div><span>something</span></div>
                </t>
        """,
            }
        )
        view2 = self.View.create(
            {
                "name": "dummy_ext",
                "type": "qweb",
                "inherit_id": view1.id,
                "arch": """
                <xpath expr="//div" position="inside">
                    <span>another thing</span>
                </xpath>
            """,
            }
        )
        view3 = self.View.create(
            {
                "name": "dummy_primary_ext",
                "type": "qweb",
                "inherit_id": view1.id,
                "mode": "primary",
                "arch": """
                <xpath expr="//div" position="inside">
                    <span>another primary thing</span>
                </xpath>
            """,
            }
        )

        content1 = (
            self.env["ir.qweb"]
            .with_context(check_view_ids=[view1.id, view2.id])
            ._render(view1.id)
        )
        content2 = (
            self.env["ir.qweb"]
            .with_context(check_view_ids=[view1.id, view2.id])
            ._render(view2.id)
        )

        self.assertEqual(content1, content2)

        self.env.cr.execute(
            "INSERT INTO ir_model_data(name, model, res_id, module)"
            "VALUES ('dummy', 'ir.ui.view', %s, 'base')" % view1.id
        )
        self.env.cr.execute(
            "INSERT INTO ir_model_data(name, model, res_id, module)"
            "VALUES ('dummy_ext', 'ir.ui.view', %s, 'base')" % view2.id
        )

        content1 = (
            self.env["ir.qweb"]
            .with_context(check_view_ids=[view1.id, view2.id])
            ._render("base.dummy")
        )
        content2 = (
            self.env["ir.qweb"]
            .with_context(check_view_ids=[view1.id, view2.id])
            ._render("base.dummy_ext")
        )

        self.assertEqual(content1, content2)

        content1 = (
            self.env["ir.qweb"]
            .with_context(check_view_ids=[view1.id, view2.id, view3.id])
            ._render(view1.id)
        )
        content3 = (
            self.env["ir.qweb"]
            .with_context(check_view_ids=[view1.id, view2.id, view3.id])
            ._render(view3.id)
        )

        self.assertNotEqual(content1, content3)

        self.env.cr.execute(
            "INSERT INTO ir_model_data(name, model, res_id, module)"
            "VALUES ('dummy_primary_ext', 'ir.ui.view', %s, 'base')" % view3.id
        )

        content1 = (
            self.env["ir.qweb"]
            .with_context(check_view_ids=[view1.id, view2.id, view3.id])
            ._render("base.dummy")
        )
        content3 = (
            self.env["ir.qweb"]
            .with_context(check_view_ids=[view1.id, view2.id, view3.id])
            ._render("base.dummy_primary_ext")
        )

        self.assertNotEqual(content1, content3)


class TestTemplateCache(ViewCase):
    def test_preload_missing_template_caches_error(self):
        missing_xmlid = "base.template_that_does_not_exist"

        preload = self.View.sudo()._preload_views([missing_xmlid])
        self.assertTrue(preload[missing_xmlid]["error"])

        info = self.View._get_cached_template_info(missing_xmlid)
        self.assertIsInstance(info["error"], MissingError)
        self.assertIsNone(info["id"])

        with self.assertRaises(MissingError):
            self.View._get_template_view(missing_xmlid, raise_if_not_found=True)
        self.assertFalse(
            self.View._get_template_view(missing_xmlid, raise_if_not_found=False)
        )

    def test_preload_missing_template_id_caches_error(self):
        missing_id = self.View.search([], order="id desc", limit=1).id + 1000

        preload = self.View.sudo()._preload_views([missing_id])
        self.assertTrue(preload[missing_id]["error"])

        info = self.View._get_cached_template_info(missing_id)
        self.assertIsInstance(info["error"], MissingError)
        with self.assertRaises(MissingError):
            self.View._get_template_view(missing_id, raise_if_not_found=True)


class TestViewRefResolution(ViewCase):
    def test_view_ref_wrong_model_warns_and_falls_back(self):
        default_id = self.View.default_view("res.partner", "form")
        with self.assertLogs(
            "odoo.addons.base.models.ir_ui_view_base", level="WARNING"
        ) as capture:
            view_data = (
                self.env["res.partner"]
                .with_context(form_view_ref="base.module_category_hidden")
                .get_view()
            )
        self.assertEqual(view_data["id"], default_id)
        self.assertIn("ir.module.category record, not an ir.ui.view", capture.output[0])

    def test_view_ref_dangling_warns_and_falls_back(self):
        default_id = self.View.default_view("res.partner", "form")
        with self.assertLogs(
            "odoo.addons.base.models.ir_ui_view_base", level="WARNING"
        ) as capture:
            view_data = (
                self.env["res.partner"]
                .with_context(form_view_ref="base.there_is_no_such_xmlid")
                .get_view()
            )
        self.assertEqual(view_data["id"], default_id)
        self.assertIn("does not match any record", capture.output[0])

    def test_view_cache_key_order_insensitive(self):
        Partner = self.env["res.partner"]
        key1 = Partner.with_context(
            form_view_ref="a.b", list_view_ref="c.d"
        )._get_view_cache_key(view_type="form")
        key2 = Partner.with_context(
            list_view_ref="c.d", form_view_ref="a.b"
        )._get_view_cache_key(view_type="form")
        self.assertEqual(key1, key2)


class TestButtonTypeValidation(ViewCase):
    def test_unknown_button_type_warns(self):
        self.assertWarning(
            '<form><button type="bogus" title="Bogus"/></form>',
            expected_message="Unknown button type 'bogus'",
        )

    def test_kanban_client_button_types_accepted(self):
        view = self.assertValid(
            """
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="name"/>
                        <button type="delete" title="Delete"/>
                    </t>
                </templates>
            </kanban>
        """
        )
        self.assertTrue(view)

    def test_button_without_name_still_gets_icon_check(self):
        self.assertWarning(
            '<form><button type="object" icon="fa-solid fa-trash"/></form>',
            expected_message=(
                "A button with icon attribute (fa-solid fa-trash) must have "
                "title in its tag, parents, descendants or have text"
            ),
        )


class TestViewCacheInvalidation(ViewCase):
    def test_empty_create_unlink_do_not_clear_templates_cache(self):
        registry_class = type(self.env.registry)
        calls = []
        original = registry_class.clear_cache

        def counting(reg, *cache_names):
            calls.append(cache_names)
            return original(reg, *cache_names)

        with patch.object(registry_class, "clear_cache", counting):
            self.assertFalse(self.View.create([]))
            self.assertTrue(self.View.browse().unlink())
        self.assertEqual(calls, [])


class TestValidationTools(common.BaseCase):
    def test_get_expression_identities(self):
        self.assertEqual(
            view_validation.get_expression_field_names(
                "context_today().strftime('%Y-%m-%d')"
            ),
            set(),
        )
        self.assertEqual(
            view_validation.get_expression_field_names(
                "field and field[0] or not field2"
            ),
            {"field", "field2"},
        )
        self.assertEqual(
            view_validation.get_expression_field_names(
                "context_today().strftime('%Y-%m-%d') or field"
            ),
            {"field"},
        )
        self.assertEqual(
            view_validation.get_expression_field_names(
                "(datetime.datetime.combine(context_today(), datetime.time(x,y,z)).to_utc()).strftime('%Y-%m-%d %H:%M:%S')"
            ),
            {"x", "y", "z"},
        )
        self.assertEqual(
            view_validation.get_expression_field_names(
                "set(field).intersection([1, 2])"
            ),
            {"field"},
        )


class TestAccessibilityChecks(common.BaseCase):
    def test_dropdown_menu(self):
        self.assertEqual(
            view_validation.get_dropdown_menu_warnings(
                E.div({"class": "dropdown-menu"})
            ),
            ["dropdown-menu class must have menu role"],
        )
        self.assertEqual(
            view_validation.get_dropdown_menu_warnings(
                E.div({"class": "dropdown-menu", "role": "menu"})
            ),
            [],
        )
        self.assertEqual(view_validation.get_dropdown_menu_warnings(E.div()), [])
        self.assertEqual(
            view_validation.get_dropdown_menu_warnings(
                E.div({"t-attf-class": "dropdown-menu #{x}"})
            ),
            ["dropdown-menu class must have menu role"],
        )

    def test_progress_bar(self):
        warnings = view_validation.get_progress_bar_warnings(
            E.div({"class": "o_progressbar"})
        )
        self.assertEqual(
            warnings,
            [
                "o_progressbar class must have progressbar role",
                "o_progressbar class must have aria-valuenow attribute",
                "o_progressbar class must have aria-valuemin attribute",
                "o_progressbar class must have aria-valuemax attribute",
            ],
        )
        fully_specified = E.div(
            {
                "class": "o_progressbar",
                "role": "progressbar",
                "aria-valuenow": "1",
                "aria-valuemin": "0",
                "aria-valuemax": "2",
            }
        )
        self.assertEqual(view_validation.get_progress_bar_warnings(fully_specified), [])

    def test_class_accessibility_modal_and_button(self):
        self.assertEqual(
            view_validation.get_class_accessibility_warnings(
                E.div({"class": "modal"}), "modal"
            ),
            ['"modal" class should only be used with "dialog" role'],
        )
        self.assertEqual(
            len(
                view_validation.get_class_accessibility_warnings(
                    E.div({"class": "btn"}), "btn"
                )
            ),
            1,
        )
        self.assertEqual(
            view_validation.get_class_accessibility_warnings(
                E.button({"class": "btn"}), "btn"
            ),
            [],
        )

    def test_fa_accessibility(self):
        parent = E.div(E.i({"class": "fa-star"}))
        warnings = view_validation.get_class_accessibility_warnings(
            parent[0], "fa-star"
        )
        self.assertEqual(len(warnings), 1)
        self.assertIn("must have title", warnings[0])
        self.assertEqual(
            view_validation.get_fa_class_accessibility_warnings(
                E.div(E.i({"class": "fa-star", "aria-label": "Star"}))[0], "desc"
            ),
            [],
        )
        self.assertEqual(
            view_validation.get_fa_class_accessibility_warnings(
                E.div(E.i({"class": "fa-star"}), "  labelled  ")[0], "desc"
            ),
            [],
        )


class TestAccessRights(TransactionCaseWithUserDemo):
    @common.users("demo")
    def test_access(self):
        with self.assertRaises(AccessError):
            self.env["ir.ui.view"].search(
                [("model", "=", "res.partner"), ("type", "=", "form")]
            )

        self.env["res.partner"].get_view(view_type="form")

        with self.assertRaises(AccessError):
            self.env["ir.ui.view"].get_view(view_type="form")

    def test_view_custom_per_user_isolation(self):
        system_group = self.env.ref("base.group_system")
        user_a = self.env["res.users"].create(
            {
                "name": "Custom Owner A",
                "login": "custom_owner_a",
                "group_ids": [(4, system_group.id)],
            }
        )
        user_b = self.env["res.users"].create(
            {
                "name": "Custom Owner B",
                "login": "custom_owner_b",
                "group_ids": [(4, system_group.id)],
            }
        )
        ref_view = self.env.ref("base.view_company_form")
        custom_a = self.env["ir.ui.view.custom"].create(
            {
                "ref_id": ref_view.id,
                "user_id": user_a.id,
                "arch": "<form/>",
            }
        )

        Custom = self.env["ir.ui.view.custom"]
        self.assertIn(
            custom_a, Custom.with_user(user_a).search([("ref_id", "=", ref_view.id)])
        )
        self.assertNotIn(
            custom_a, Custom.with_user(user_b).search([("ref_id", "=", ref_view.id)])
        )
        with self.assertRaises(AccessError):
            Custom.with_user(user_b).browse(custom_a.id).read(["arch"])


@common.tagged("post_install", "-at_install", "-standard", "migration")
class TestAllViews(common.TransactionCase):
    def test_views(self):
        views = self.env["ir.ui.view"].with_context(lang=None).search([])
        for index, view in enumerate(views):
            if index % 500 == 0:
                _logger.info("checked %s/%s views", index, len(views))
            with self.subTest(name=view.name):
                view._check_xml()


@common.tagged("post_install", "-at_install", "-standard", "render_all_views")
class TestRenderAllViews(TransactionCaseWithUserDemo):
    @common.users("demo", "admin")
    def test_render_all_views(self):
        env = self.env(context={"lang": "en_US"})
        count = 0
        elapsed = 0
        for model in env.values():
            if not model._abstract and model.has_access("read"):
                with self.subTest(model=model):
                    times = []
                    for _ in range(5):
                        env.invalidate_all()
                        before = time.perf_counter()
                        model.get_view()
                        times.append(time.perf_counter() - before)
                    count += 1
                    elapsed += min(times)

        _logger.info(
            "Rendered %d views as %s using (best of 5) %ss",
            count,
            self.env.user.name,
            elapsed,
        )
        self.assertGreater(count, 0, "no model was readable, so nothing was rendered")


@common.tagged("post_install", "-at_install", "post_install_l10n")
class TestInvisibleField(TransactionCaseWithUserDemo):
    def test_uncommented_invisible_field(self):
        only_log_modules = (
            "account",
            "account_3way_match",
            "account_accountant",
            "account_accountant_batch_payment",
            "account_asset_fleet",
            "account_auto_transfer",
            "account_avatax",
            "account_avatax_geolocalize",
            "account_avatax_sale",
            "account_base_import",
            "account_batch_payment",
            "account_budget",
            "account_check_printing",
            "account_consolidation",
            "account_debit_note",
            "account_depreciation",
            "account_disallowed_expenses",
            "account_edi",
            "account_edi_proxy_client",
            "account_edi_ubl_cii",
            "account_external_tax",
            "account_fleet",
            "account_followup",
            "account_intrastat",
            "account_online_synchronization",
            "account_payment_provider",
            "account_peppol",
            "account_qr_code_emv",
            "account_saft_import",
            "account_sepa",
            "account_sepa_direct_debit",
            "account_vat",
            "account_winbooks_import",
            "analytic",
            "appointment",
            "auth_signup",
            "auth_totp",
            "automation",
            "barcodes_gs1_nomenclature",
            "base_import_module",
            "base_install_request",
            "calendar",
            "crm",
            "crm_helpdesk",
            "crm_iap_enrich",
            "crm_iap_mine",
            "data_cleaning",
            "data_merge",
            "data_recycle",
            "delivery",
            "delivery_dhl",
            "delivery_easypost",
            "delivery_fedex",
            "delivery_iot",
            "delivery_mondialrelay",
            "delivery_sendcloud",
            "delivery_shiprocket",
            "delivery_starshipit",
            "delivery_ups",
            "delivery_ups_rest",
            "delivery_usps",
            "digest",
            "document",
            "document_account",
            "document_fleet",
            "document_l10n_be_hr_payroll",
            "document_project",
            "document_project_sale",
            "document_spreadsheet",
            "event",
            "event_booth",
            "event_booth_sale",
            "event_crm",
            "event_sale",
            "fleet",
            "frontdesk",
            "gamification",
            "geocoding",
            "helpdesk",
            "helpdesk_account",
            "helpdesk_fsm",
            "helpdesk_fsm_report",
            "helpdesk_repair",
            "helpdesk_sale",
            "helpdesk_sale_loyalty",
            "helpdesk_sale_timesheet",
            "helpdesk_stock",
            "helpdesk_stock_account",
            "helpdesk_timesheet",
            "hr",
            "hr_appraisal",
            "hr_appraisal_skills",
            "hr_appraisal_survey",
            "hr_attendance",
            "hr_contract",
            "hr_contract_salary",
            "hr_contract_salary_holidays",
            "hr_expense",
            "hr_fleet",
            "hr_gamification",
            "hr_holidays",
            "hr_holidays_attendance",
            "hr_payroll",
            "hr_payroll_account",
            "hr_payroll_expense",
            "hr_recruitment",
            "hr_recruitment_sign",
            "hr_recruitment_skills",
            "hr_recruitment_survey",
            "hr_referral",
            "hr_sign",
            "hr_skills",
            "hr_skills_slides",
            "hr_skills_survey",
            "hr_timesheet",
            "hr_work_entry",
            "hr_work_entry_holidays_enterprise",
            "iap",
            "im_livechat",
            "industry_fsm",
            "industry_fsm_report",
            "industry_fsm_sale",
            "industry_fsm_sale_report",
            "industry_fsm_stock",
            "iot",
            "knowledge",
            "l10n_ae_hr_payroll",
            "l10n_ar",
            "l10n_ar_edi",
            "l10n_ar_withholding",
            "l10n_au_hr_payroll",
            "l10n_au_hr_payroll_account",
            "l10n_be_codabox",
            "l10n_be_hr_contract_salary",
            "l10n_be_hr_payroll",
            "l10n_be_hr_payroll_dimona",
            "l10n_be_hr_payroll_fleet",
            "l10n_be_hr_payroll_sd_worx",
            "l10n_be_reports",
            "l10n_be_soda",
            "l10n_br",
            "l10n_br_avatax",
            "l10n_br_edi",
            "l10n_br_edi_stock",
            "l10n_ch_hr_payroll",
            "l10n_cl",
            "l10n_cl_edi",
            "l10n_cl_edi_exports",
            "l10n_cl_edi_stock",
            "l10n_cn",
            "l10n_co_dian",
            "l10n_co_edi",
            "l10n_cz_reports",
            "l10n_de_pos_cert",
            "l10n_ec",
            "l10n_ec_edi",
            "l10n_ec_edi_pos",
            "l10n_ec_edi_stock",
            "l10n_ec_sale",
            "l10n_eg_edi_eta",
            "l10n_eg_hr_payroll",
            "l10n_employment_hero",
            "l10n_es_edi_facturae",
            "l10n_es_edi_sii",
            "l10n_es_edi_tbai",
            "l10n_es_edi_tbai_pos",
            "l10n_es_reports",
            "l10n_eu_oss_reports",
            "l10n_fr_hr_holidays",
            "l10n_fr_hr_payroll",
            "l10n_fr_intrastat",
            "l10n_fr_pos_cert",
            "l10n_fr_reports",
            "l10n_gr_edi",
            "l10n_hk_hr_payroll",
            "l10n_hu_edi",
            "l10n_id_efaktur",
            "l10n_id_efaktur_coretax",
            "l10n_in_hr_payroll",
            "l10n_it_edi",
            "l10n_it_edi_doi",
            "l10n_it_edi_sale",
            "l10n_it_stock_ddt",
            "l10n_jo_edi",
            "l10n_jo_hr_payroll",
            "l10n_jp_zengin",
            "l10n_ke_edi_oscu",
            "l10n_ke_edi_oscu_mrp",
            "l10n_ke_edi_oscu_pos",
            "l10n_ke_edi_oscu_stock",
            "l10n_ke_edi_tremol",
            "l10n_ke_hr_payroll",
            "l10n_latam_check",
            "l10n_latam_invoice_document",
            "l10n_lu_hr_payroll",
            "l10n_lu_reports",
            "l10n_ma_hr_payroll",
            "l10n_mx",
            "l10n_mx_edi",
            "l10n_mx_edi_extended",
            "l10n_mx_edi_landing",
            "l10n_mx_edi_pos",
            "l10n_mx_edi_stock",
            "l10n_mx_hr_payroll",
            "l10n_mx_reports",
            "l10n_mx_xml_polizas",
            "l10n_my_edi",
            "l10n_my_edi_pos",
            "l10n_nl_reports",
            "l10n_nz_eft",
            "l10n_pe",
            "l10n_pe_edi",
            "l10n_pe_edi_stock",
            "l10n_pe_reports",
            "l10n_pe_reports_stock",
            "l10n_ph",
            "l10n_ph_check_printing",
            "l10n_pl_reports",
            "l10n_ro_edi_stock",
            "l10n_ro_edi_stock_batch",
            "l10n_ro_saft",
            "l10n_sa_edi",
            "l10n_sa_hr_payroll",
            "l10n_se",
            "l10n_se_sie4_import",
            "l10n_tr_nilvera_edispatch",
            "l10n_uk_bacs",
            "l10n_uk_reports",
            "l10n_uk_reports_cis",
            "l10n_us_hr_payroll",
            "l10n_us_hr_payroll_adp",
            "l10n_uy_edi",
            "loyalty",
            "lunch",
            "mail",
            "mail_bot_hr",
            "mail_group",
            "maintenance",
            "maintenance_worksheet",
            "marketing_automation",
            "marketing_automation_sms",
            "mass_mailing",
            "mass_mailing_crm",
            "mass_mailing_event",
            "mass_mailing_slides",
            "mass_mailing_sms",
            "membership",
            "mrp",
            "mrp_account",
            "mrp_account_enterprise",
            "mrp_landed_costs",
            "mrp_maintenance",
            "mrp_mps",
            "mrp_plm",
            "mrp_product_expiry",
            "mrp_subcontracting",
            "mrp_subcontracting_dropshipping",
            "mrp_workorder",
            "mrp_workorder_expiry",
            "mrp_workorder_iot",
            "onboarding",
            "partner_address_extended",
            "partner_autocomplete",
            "partner_commission",
            "payment",
            "payment_adyen",
            "payment_authorize",
            "payment_custom",
            "payment_demo",
            "planning",
            "point_of_sale",
            "portal",
            "pos_enterprise",
            "pos_hr",
            "pos_iot",
            "pos_online_payment",
            "pos_restaurant",
            "pos_restaurant_appointment",
            "pos_self_order",
            "privacy_lookup",
            "product",
            "product_email_template",
            "product_expiry",
            "product_margin",
            "project",
            "project_timesheet_forecast",
            "project_timesheet_holidays",
            "project_todo",
            "purchase",
            "purchase_product_matrix",
            "purchase_requisition",
            "purchase_stock",
            "quality",
            "quality_control",
            "quality_control_iot",
            "quality_control_picking_batch",
            "quality_control_worksheet",
            "quality_iot",
            "quality_mrp",
            "quality_mrp_workorder",
            "rating",
            "repair",
            "resource",
            "room",
            "sale",
            "sale_amazon",
            "sale_crm",
            "sale_expense",
            "sale_external_tax",
            "sale_loyalty",
            "sale_margin",
            "sale_pdf_quote_builder",
            "sale_planning",
            "sale_product_matrix",
            "sale_project",
            "sale_purchase",
            "sale_renting",
            "sale_renting_crm",
            "sale_stock",
            "sale_stock_renting",
            "sale_subscription",
            "sale_team",
            "sale_timesheet",
            "sale_timesheet_enterprise",
            "sign",
            "sms",
            "snailmail",
            "snailmail_account",
            "social",
            "social_crm",
            "social_facebook",
            "social_instagram",
            "social_linkedin",
            "social_push_notifications",
            "social_twitter",
            "social_youtube",
            "spreadsheet_dashboard_edition",
            "spreadsheet_dashboard_sale_subscription",
            "stock",
            "stock_account",
            "stock_barcode",
            "stock_barcode_mrp",
            "stock_barcode_picking_batch",
            "stock_barcode_product_expiry",
            "stock_delivery",
            "stock_enterprise",
            "stock_intrastat",
            "stock_landed_costs",
            "stock_picking_batch",
            "survey",
            "test_testing_utilities",
            "timesheet_grid",
            "uom",
            "utm",
            "voip",
            "web",
            "web_studio",
            "website",
            "website_appointment",
            "website_blog",
            "website_crm_iap_reveal",
            "website_crm_partner_assign",
            "website_customer",
            "website_delivery_sendcloud",
            "website_event",
            "website_event_booth_exhibitor",
            "website_event_exhibitor",
            "website_event_social",
            "website_event_track",
            "website_event_track_gantt",
            "website_event_track_quiz",
            "website_event_track_social",
            "website_event_twitter_wall",
            "website_forum",
            "website_helpdesk_forum",
            "website_hr_recruitment",
            "website_knowledge",
            "website_livechat",
            "website_payment",
            "website_sale",
            "website_sale_loyalty",
            "website_sale_slides",
            "website_sale_stock",
            "website_slides",
            "website_slides_survey",
            "website_sms",
            "website_studio",
            "website_twitter_wall",
            "whatsapp",
            "whatsapp_payment",
            "worksheet",
        )

        modules_without_error = set(
            self.env["ir.module.module"]
            .search([("state", "=", "installed"), ("name", "in", only_log_modules)])
            .mapped("name")
        )
        module_log_views = defaultdict(list)
        module_error_views = defaultdict(lambda: defaultdict(list))
        uncommented_regexp = (
            r"""(<field [^>]*invisible=['"](True|1)['"][^>]*>)[\s\t\n ]*(.*)"""
        )
        views = self.env["ir.ui.view"].search(
            [
                ("type", "in", ("list", "form")),
                "|",
                ("arch_db", "like", "invisible=_True_"),
                ("arch_db", "like", "invisible=_1_"),
            ]
        )
        for view in views.filtered("model_data_id"):
            module_name = view.model_data_id.module
            view_name = view.model_data_id.name
            for field, _val, comment in re.findall(uncommented_regexp, view.arch_db):
                if not comment or not comment.startswith("<!--"):
                    if module_name in only_log_modules:
                        modules_without_error.discard(module_name)
                        module_log_views[module_name].append(view_name)
                        break
                    module_error_views[module_name][view_name].append(field)

        msg = "Please indicate why the always invisible fields are present in the view, or remove the field tag."

        if module_log_views:
            msg_info = "\n".join(
                f"Addons: {module!r}   Views: {names}"
                for module, names in module_log_views.items()
            )
            _logger.info("%s\n%s", msg, msg_info)

        if module_error_views:
            error_lines = []
            for module, view_errors in module_error_views.items():
                error_lines.append(f"Addon: {module!r}")
                for view, fields in view_errors.items():
                    error_lines.extend([f"{' ' * 3}View: {view}\n{' ' * 6}Fields:"])
                    error_lines.extend(
                        ["\n".join(f"{' ' * 9}{field}" for field in fields)]
                    )
            _logger.error("%s\n%s", msg, "\n".join(error_lines))

        if modules_without_error:
            _logger.error(
                "Please remove this module names from the white list of this current test: %r",
                sorted(modules_without_error),
            )


class CompRegexTest(common.TransactionCase):
    def test_comp_regex(self):
        regex = ir_ui_view_arch.COMP_REGEX
        for expr in ("", "__comp__2", "__comp___that", "a__comp__"):
            self.assertIsNone(re.search(regex, expr), expr)
        for expr in (
            "__comp__",
            "__comp__ ",
            " __comp__ ",
            "__comp__.props",
            "__comp__ .props",
            "__comp__['props']",
            "__comp__ ['props']",
            '__comp__["props"]',
            '__comp__ ["props"]',
            '    __comp__     ["props"]    ',
            "record ? __comp__ : false",
            "!__comp__.props.resId",
            "{{ __comp__ }}",
        ):
            self.assertIsNotNone(re.search(regex, expr), expr)


@common.tagged("at_install", "modifiers")
class ViewModifiers(ViewCase):
    @mute_logger("odoo.addons.base.models.ir_ui_view")
    def test_01_modifiers(self):
        def _test_modifiers(what, expected_vnames):
            if isinstance(what, dict):
                node = etree.Element("field", {k: str(v) for k, v in what.items()})
            else:
                node = etree.fromstring(what) if isinstance(what, str) else what
            modifiers = {
                attr: node.attrib[attr]
                for attr in node.attrib
                if attr in ir_ui_view.VIEW_MODIFIERS
            }
            vnames = set()
            for expr in modifiers.values():
                vnames |= view_validation.get_expression_field_names(expr) - {"id"}
            assert vnames == expected_vnames, f"{vnames!r} != {expected_vnames!r}"

        str_true = "True"

        _test_modifiers('<field name="a"/>', set())
        _test_modifiers('<field name="a" invisible="1"/>', set())
        _test_modifiers('<field name="a" readonly="1"/>', set())
        _test_modifiers('<field name="a" required="1"/>', set())
        _test_modifiers('<field name="a" invisible="0"/>', set())
        _test_modifiers('<field name="a" readonly="0"/>', set())
        _test_modifiers('<field name="a" required="0"/>', set())
        _test_modifiers(
            '<field name="a" invisible="1" required="1"/>',
            set(),
        )
        _test_modifiers(
            '<field name="a" invisible="1" required="0"/>',
            set(),
        )
        _test_modifiers(
            '<field name="a" invisible="0" required="1"/>',
            set(),
        )
        _test_modifiers(
            """<field name="a" invisible="b == 'c'"/>""",
            {"b"},
        )
        _test_modifiers(
            """<field name="a" invisible="b == 'c'"/>""",
            {"b"},
        )
        _test_modifiers(
            """<field name="a" invisible="b == 'c'"/>""",
            {"b"},
        )
        _test_modifiers(
            """<field name="a" invisible="(b == 'c' or e == 'f')"/>""",
            {"b", "e"},
        )
        _test_modifiers(
            """<field name="a" invisible="b == 'c'"/>""",
            {"b"},
        )
        _test_modifiers(
            """<field name="a" invisible="user_id == uid"/>""",
            {"user_id"},
        )
        _test_modifiers(
            """<field name="a" invisible="(user_id == other_field)"/>""",
            {"user_id", "other_field"},
        )
        _test_modifiers(
            """<field name="a" invisible="a == parent.b"/>""",
            {"a", "parent.b"},
        )
        _test_modifiers(
            """<field name="a" invisible="a == context.get('b')"/>""",
            {"a"},
        )
        _test_modifiers(
            """<field name="a" invisible="a == context['b']"/>""",
            {"a"},
        )
        _test_modifiers(
            """<field name="a" invisible="company_id == allowed_company_ids[0]"/>""",
            {"company_id"},
        )
        _test_modifiers(
            """<field name="a" invisible="company_id == (field_1 or False)"/>""",
            {"company_id", "field_1"},
        )

        tree = etree.fromstring("""
            <list>
                <header>
                    <button name="a" invisible="1"/>
                </header>
                <field name="a"/>
                <field name="a" invisible="0"/>
                <field name="a" column_invisible="1"/>
                <field name="a" invisible="b == 'c'"/>
                <field name="a" invisible="(b == 'c')"/>
            </list>
        """)
        _test_modifiers(tree[0][0], set())
        _test_modifiers(tree[1], set())
        _test_modifiers(tree[2], set())
        _test_modifiers(tree[3], set())
        _test_modifiers(tree[4], {"b"})
        _test_modifiers(tree[5], {"b"})

        _test_modifiers({}, set())
        _test_modifiers({"invisible": str_true}, set())
        _test_modifiers({"invisible": False}, set())

    @mute_logger("odoo.addons.base.models.ir_ui_view")
    def test_03_modifier_attribute_is_boolean(self):
        arch = """
            <form string="View">
                <field name="model"/>
                <field name="name" readonly="%s"/>
            </form>
        """
        self.assertValid(arch % "1")
        self.assertValid(arch % "0")
        self.assertValid(arch % "True")
        self.assertValid(arch % "[('model', '=', '1')]")

    def test_04_modifier_attribute_using_context(self):
        view = self.assertValid("""
            <form string="View">
                <field name="name"
                    invisible="context.get('foo')"
                    readonly="context.get('bar')"
                    required="context.get('baz')"
                />
            </form>
        """)
        arch = self.View.with_context(foo=True).get_view(view.id)["arch"]
        field_node = etree.fromstring(arch).xpath('//field[@name="name"]')[0]
        self.assertEqual(field_node.get("invisible"), "context.get('foo')")
        self.assertEqual(field_node.get("readonly"), "context.get('bar')")
        self.assertEqual(field_node.get("required"), "context.get('baz')")

    def test_05_modifier_attribute_priority(self):
        view = self.assertValid("""
            <form string="View">
                <field name="type" invisible="1"/>
                <field name="name" invisible="context.get('foo') and type == 'list'"/>
            </form>
        """)
        for type_value, context, expected in [
            ("list", {}, False),
            ("form", {}, False),
            ("list", {"foo": True}, True),
            ("form", {"foo": True}, False),
        ]:
            arch = self.View.with_context(**context).get_view(view.id)["arch"]
            field_node = etree.fromstring(arch).xpath('//field[@name="name"]')[0]
            result = field_node.get("invisible")
            result = safe_eval.safe_eval(
                result, {"context": context, "type": type_value}
            )
            self.assertEqual(bool(result), expected, f"With context: {context}")

    @mute_logger("odoo.addons.base.models.ir_ui_view")
    def test_10_raise_for_old_attributes(self):
        arch = """
            <form string="View">
                <field name="name"/>
                <field name="model"/>
                <field name="inherit_id" attrs="{'readonly': [('model', '=', 'ir.ui.view')]"/>
            </form>
        """
        self.assertInvalid(arch, """no longer used""")

        arch = """
            <form string="View">
                <field name="name"/>
                <field name="model"/>
                <field name="inherit_id" states="draft,done"/>
            </form>
        """
        self.assertInvalid(arch, """no longer used""")

    @mute_logger("odoo.addons.base.models.ir_ui_view")
    def test_11_attrs_field(self):
        arch = """
            <form string="View">
                <field name="name"/>%s
                <field name="inherit_id"
                       readonly="model == 'ir.ui.view'"/>
            </form>
        """
        view = self.assertValid(arch % '<field name="model"/>')
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )

        view = self.assertValid(arch % "")
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )

    @mute_logger("odoo.addons.base.models.ir_ui_view")
    def test_12_invalid_syntax(self):
        arch = """
            <form string="View">
                <field name="name"/>
                <field name="model"/>
                <field name="inherit_id"
                       readonly="model 'ir.ui.view'"/>
            </form>
        """
        self.assertInvalid(
            arch,
            """Invalid modifier 'readonly'""",
        )

        arch = """
            <form string="View">
                <field name="name"/>
                <field name="model"/>
                <field name="inherit_id"
                       readonly="bidule.get('truc') === 1 or context.get('truc')"/>
            </form>
        """
        self.assertInvalid(
            arch,
            """Invalid modifier 'readonly'""",
        )

    @mute_logger("odoo.addons.base.models.ir_ui_view")
    def test_13_attrs_states_invisible_to_modifier(self):
        view = self.View.create(
            {
                "name": "foo",
                "model": "ir.module.module",
                "arch": """
                <form string="View">
                    <group invisible="state != 'finished'">
                        <field name="category_id" invisible="not state" />
                        <field name="state" invisible="name not in ['qweb-pdf', 'qweb-html', 'qweb-text']"/>
                        <field name="name" invisible="name != 'bidule' and category_id != uid and state not in ('draf', 'finished')"/>
                    </group>
                </form>
            """,
            }
        )
        arch = self.env["ir.module.module"].get_view(view_id=view.id)["arch"]
        tree = etree.fromstring(arch)

        invisible = tree.xpath("//group")[0].get("invisible")
        self.assertEqual(invisible, "state != 'finished'")

        invisible = tree.xpath('//field[@name="category_id"]')[0].get("invisible")
        self.assertEqual(invisible, "not state")

        invisible = tree.xpath('//field[@name="state"]')[0].get("invisible")
        self.assertEqual(
            invisible, "name not in ['qweb-pdf', 'qweb-html', 'qweb-text']"
        )

        invisible = tree.xpath('//field[@name="name"]')[0].get("invisible")
        self.assertEqual(
            invisible,
            "name != 'bidule' and category_id != uid and state not in ('draf', 'finished')",
        )

    @mute_logger("odoo.addons.base.models.ir_ui_view")
    def test_14_attrs_subfield(self):
        arch = """
            <form string="View">
                <field name="name"/>%s
                <field name="inherit_children_ids">
                    <form string="Children">
                        <field name="name"/>%s
                        <field name="inherit_id"
                               readonly="model == 'ir.ui.view'"/>
                    </form>
                </field>
            </form>
        """
        view = self.assertValid(arch % ("", '<field name="model"/>'))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )

        view = self.assertValid(arch % ("", ""))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )

        view = self.assertValid(arch % ('<field name="model"/>', ""))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )

    @mute_logger("odoo.addons.base.models.ir_ui_view")
    def test_15_attrs_subfield_with_parent(self):
        arch = """
            <form string="View">
                <field name="name"/>%s
                <field name="inherit_children_ids">
                    <form string="Children">
                        <field name="name"/>%s
                        <field name="inherit_id"
                               readonly="parent.model == 'ir.ui.view'"/>
                    </form>
                </field>
            </form>
        """
        view = self.assertValid(arch % ('<field name="model"/>', ""))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )

        view = self.assertValid(arch % ("", ""))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field/form/field[@name="model"][@invisible][@readonly]'
            )
        )

        view = self.assertValid(arch % ("", '<field name="model"/>'))
        view_arch = view.get_views([(view.id, "form")])["views"]["form"]["arch"]
        self.assertTrue(
            etree.fromstring(view_arch).xpath(
                '//field[@name="model"][@invisible][@readonly]'
            )
        )
        self.assertFalse(
            etree.fromstring(view_arch).xpath(
                '//field/form/field[@name="model"][@invisible][@readonly]'
            )
        )

    def test_16_attrs_groups_behavior(self):
        view = self.View.create(
            {
                "name": "foo",
                "model": "res.partner",
                "arch": """
                <form>
                    <field name="name"/>
                    <field name="company_id" groups="base.group_system"/>
                    <div id="foo"/>
                    <div id="bar" groups="base.group_system"/>
                </form>
            """,
            }
        )
        user_demo = self.user_demo
        self.assertFalse(user_demo.has_group("base.group_system"))
        arch = (
            self.env["res.partner"]
            .with_user(user_demo)
            .get_view(view_id=view.id)["arch"]
        )
        tree = etree.fromstring(arch)
        self.assertTrue(tree.xpath('//field[@name="name"]'))
        self.assertFalse(tree.xpath('//field[@name="company_id"]'))
        self.assertTrue(tree.xpath('//div[@id="foo"]'))
        self.assertFalse(tree.xpath('//div[@id="bar"]'))

        user_admin = self.env.ref("base.user_admin")
        self.assertTrue(user_admin.has_group("base.group_system"))
        arch = (
            self.env["res.partner"]
            .with_user(user_admin)
            .get_view(view_id=view.id)["arch"]
        )
        tree = etree.fromstring(arch)
        self.assertTrue(tree.xpath('//field[@name="name"]'))
        self.assertTrue(tree.xpath('//field[@name="company_id"]'))
        self.assertTrue(tree.xpath('//div[@id="foo"]'))
        self.assertTrue(tree.xpath('//div[@id="bar"]'))

    @mute_logger("odoo.addons.base.models.ir_ui_view")
    def test_17_attrs_groups_validation(self):
        IrModelAccess = type(self.env["ir.model.access"])
        system_only = (
            self.env["res.groups"]._get_group_definitions().parse("base.group_system")
        )
        self.patch(
            IrModelAccess,
            "_get_groups_with_access",
            lambda _self, _model_name, access_mode="read": system_only,
        )
        test_group = self.env["res.groups"].create({"name": "test_group"})
        self.env["ir.model.data"].create(
            {
                "module": "base",
                "name": "test_group",
                "model": "res.groups",
                "res_id": test_group.id,
            }
        )

        def validate(
            arch, add_field_with_groups=False, parent=False, model="ir.ui.view"
        ):
            parent = "parent." if parent else ""
            view = self.assertValid(
                arch % {"attrs": f"""decoration-info="{parent}name == 'foo'" """},
                model=model,
            )
            result = self.env[model]._get_view_cache(view_id=view.id)
            tree = etree.fromstring(result["arch"])
            group_definitions = self.env["res.groups"]._get_group_definitions()

            if add_field_with_groups is False:
                nodes = tree.xpath('//field[@name="name"][@invisible][@readonly]')
                self.assertEqual(len(nodes), 0, arch)
            else:
                nodes = tree.xpath(
                    "//field[@name='name'][@invisible='True'][@readonly='True']"
                )
                self.assertEqual(len(nodes), 1, arch)
                groups_key = nodes[0].get("__groups_key__")
                group_repr = (
                    str(group_definitions.from_key(groups_key)) if groups_key else ""
                )
                self.assertEqual(group_repr, add_field_with_groups, arch)

        arch = """
            <form string="View">
                <field name="name"/>
                <field name="inherit_id" %(attrs)s/>
            </form>
        """
        self.assertValid(arch % {"attrs": """invisible="name == 'foo'" """})
        self.assertValid(arch % {"attrs": """domain="[('name', '!=', name)]" """})
        self.assertValid(arch % {"attrs": """context="{'default_name': name}" """})
        self.assertValid(arch % {"attrs": """decoration-info="name == 'foo'" """})

        validate(
            """
            <form string="View">
                <field name="name"/>
                <field name="inherit_id" %(attrs)s/>
            </form>
        """,
            add_field_with_groups=False,
        )

        validate(
            """
            <form string="View">
                <field name="inherit_id" %(attrs)s/>
            </form>
        """,
            add_field_with_groups="",
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.group_public"/>
                <field name="inherit_id" %(attrs)s/>
            </form>
        """,
            add_field_with_groups="",
        )

        validate(
            """
            <form string="View">
                <group groups="base.group_user">
                    <field name="name" groups="base.group_public"/>
                    <field name="inherit_id" groups="base.group_portal" %(attrs)s/>
                </group>
            </form>
        """,
            add_field_with_groups=False,
        )

        validate(
            """
            <form string="View">
                <field name="inherit_id" groups="base.test_group" %(attrs)s/>
            </form>
        """,
            add_field_with_groups="'base.test_group'",
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.test_group"/>
                <field name="inherit_id" %(attrs)s/>
            </form>
        """,
            add_field_with_groups="",
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.test_group"/>
                <field name="inherit_children_ids">
                    <list editable="bottom">
                        <field name="inherit_id" %(attrs)s/>
                    </list>
                </field>
            </form>
        """,
            add_field_with_groups="",
            parent=True,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.test_group"/>
                <field name="inherit_children_ids">
                    <list editable="bottom">
                        <field name="inherit_id" groups="base.test_group" %(attrs)s/>
                    </list>
                </field>
            </form>
        """,
            add_field_with_groups=False,
            parent=True,
        )

        validate(
            """
            <form string="View">
                <field name="name"/>
                <field name="inherit_children_ids">
                    <list editable="bottom">
                        <field name="inherit_id" groups="base.test_group" %(attrs)s/>
                    </list>
                </field>
            </form>
        """,
            add_field_with_groups=False,
            parent=True,
        )

        validate(
            """
            <form string="View">
                <field name="name"/>
                <field name="inherit_id" %(attrs)s groups="base.test_group"/>
            </form>
        """,
            add_field_with_groups=False,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.test_group"/>
                <field name="inherit_id" groups="base.test_group" %(attrs)s/>
            </form>
        """,
            add_field_with_groups=False,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.group_portal"/>
                <field name="name" groups="base.test_group"/>
                <field name="inherit_id" groups="base.test_group" %(attrs)s/>
            </form>
        """,
            add_field_with_groups=False,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.test_group"/>
                <field name="inherit_id" groups="base.test_group" %(attrs)s/>
                <field name="inherit_id" groups="base.group_multi_company" %(attrs)s/>
            </form>
        """,
            add_field_with_groups="'base.group_multi_company'",
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.test_group"/>
                <field name="name" groups="base.group_portal"/>
                <field name="inherit_id" groups="base.test_group" %(attrs)s/>
                <field name="inherit_id" groups="base.group_portal" %(attrs)s/>
            </form>
        """,
            add_field_with_groups=False,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.group_portal,base.test_group"/>
                <field name="inherit_id" groups="base.test_group" %(attrs)s/>
            </form>
        """,
            add_field_with_groups=False,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.test_group"/>
                <field name="inherit_id" groups="base.group_multi_company,base.test_group" %(attrs)s/>
            </form>
        """,
            add_field_with_groups="'base.group_multi_company' | 'base.test_group'",
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.test_group"/>
                <div groups="base.group_multi_company,base.group_system">
                    <field name="inherit_id" groups="base.test_group" %(attrs)s/>
                </div>
            </form>
        """,
            add_field_with_groups=False,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="inherit_id" groups="base.group_erp_manager" %(attrs)s/>
            </form>
        """,
            add_field_with_groups=False,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.group_erp_manager"/>
                <field name="inherit_children_ids">
                    <list editable="bottom">
                        <field name="inherit_id" groups="base.group_multi_company" %(attrs)s/>
                    </list>
                </field>
            </form>
        """,
            add_field_with_groups=False,
            parent=True,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.test_group"/>
                <field name="inherit_id" groups="base.group_multi_company" %(attrs)s/>
            </form>
        """,
            add_field_with_groups="'base.group_multi_company'",
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.test_group"/>
                <field name="inherit_children_ids">
                    <list editable="bottom">
                        <field name="inherit_id" groups="base.group_multi_company" %(attrs)s/>
                    </list>
                </field>
            </form>
        """,
            add_field_with_groups="'base.group_multi_company'",
            parent=True,
        )

        validate(
            """
            <form string="View">
                <group groups="base.test_group">
                    <field name="name"/>
                </group>
                <field name="inherit_id" %(attrs)s/>
            </form>
        """,
            add_field_with_groups="",
        )

        validate(
            """
            <form string="View">
                <group groups="base.test_group">
                    <field name="name"/>
                    <field name="inherit_id" %(attrs)s/>
                </group>
            </form>
        """,
            add_field_with_groups=False,
        )

        validate(
            """
            <form string="View">
                <group groups="base.test_group">
                    <field name="name"/>
                    <field name="inherit_id" %(attrs)s groups="base.group_multi_currency,base.group_multi_company"/>
                </group>
            </form>
        """,
            add_field_with_groups=False,
        )

        validate(
            """
            <form string="View">
                <group groups="base.test_group">
                    <field name="name"/>
                </group>
                <group groups="base.test_group">
                    <field name="inherit_id" %(attrs)s/>
                </group>
            </form>
        """,
            add_field_with_groups=False,
        )

        validate(
            """
            <form string="View">
                <group groups="base.group_erp_manager">
                    <field name="name"/>
                </group>
                <group groups="base.test_group">
                    <field name="inherit_id" %(attrs)s/>
                </group>
            </form>
        """,
            add_field_with_groups=False,
        )

        validate(
            """
            <form string="View">
                <group groups="base.test_group">
                    <field name="name"/>
                </group>
                <group groups="base.group_multi_company">
                    <field name="inherit_id" %(attrs)s/>
                </group>
            </form>
        """,
            add_field_with_groups="'base.group_multi_company'",
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.test_group"/>
                <field name="inherit_children_ids" groups="base.test_group">
                    <list editable="bottom">
                        <field name="inherit_id" %(attrs)s/>
                    </list>
                </field>
            </form>
        """,
            add_field_with_groups=False,
            parent=True,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.group_erp_manager"/>
                <field name="inherit_children_ids" groups="base.test_group">
                    <list editable="bottom">
                        <field name="inherit_id" %(attrs)s/>
                    </list>
                </field>
            </form>
        """,
            add_field_with_groups=False,
            parent=True,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.test_group"/>
                <field name="inherit_children_ids" groups="base.group_multi_company">
                    <list editable="bottom">
                        <field name="inherit_id" %(attrs)s/>
                    </list>
                </field>
            </form>
        """,
            add_field_with_groups="'base.group_multi_company'",
            parent=True,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="!base.test_group"/>
                <field name="inherit_id" %(attrs)s/>
            </form>
        """,
            add_field_with_groups="",
        )

        validate(
            """
            <form string="View">
                <field name="name"/>
                <field name="inherit_id" groups="!base.test_group" %(attrs)s/>
            </form>
        """,
            add_field_with_groups=False,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="!base.test_group"/>
                <field name="name" groups="base.test_group"/>
                <field name="inherit_id" groups="base.test_group" %(attrs)s/>
            </form>
        """,
            add_field_with_groups=False,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="!base.test_group"/>
                <field name="name" groups="base.test_group"/>
                <field name="inherit_id" groups="!base.test_group" %(attrs)s/>
            </form>
        """,
            add_field_with_groups=False,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="!base.test_group"/>
                <field name="name" groups="base.test_group"/>
                <field name="inherit_id" groups="base.group_portal" %(attrs)s/>
            </form>
        """,
            add_field_with_groups=False,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="!base.group_multi_company,!base.test_group"/>
                <field name="inherit_id" groups="!base.group_multi_company" %(attrs)s/>
            </form>
        """,
            add_field_with_groups="~'base.group_multi_company'",
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="!base.group_multi_company"/>
                <field name="inherit_id" groups="!base.group_multi_company,!base.test_group" %(attrs)s/>
            </form>
        """,
            add_field_with_groups=False,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="!base.group_user"/>
                <field name="inherit_id" groups="!base.group_multi_company" %(attrs)s/>
            </form>
        """,
            add_field_with_groups="~'base.group_multi_company'",
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="!base.test_group"/>
                <field name="inherit_id" groups="!base.group_user" %(attrs)s/>
            </form>
        """,
            add_field_with_groups=False,
        )

        validate(
            """
            <form string="View">
                <group groups="base.group_multi_company">
                    <field name="name" groups="!base.test_group"/>
                </group>
                <group groups="base.group_multi_company">
                    <field name="inherit_id" %(attrs)s/>
                </group>
            </form>
        """,
            add_field_with_groups="'base.group_multi_company'",
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.group_multi_company"/>
                <field name="inherit_id" groups="!base.group_multi_company" %(attrs)s/>
            </form>
        """,
            add_field_with_groups="~'base.group_multi_company'",
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="!base.group_multi_company"/>
                <field name="name" groups="base.group_multi_company"/>
                <field name="name" groups="!base.group_portal"/>
                <field name="name" groups="base.group_portal"/>
                <field name="inherit_id" %(attrs)s groups="base.group_multi_company"/>
                <field name="inherit_id" %(attrs)s groups="!base.group_multi_company"/>
                <field name="inherit_id" %(attrs)s groups="base.group_portal"/>
                <field name="inherit_id" %(attrs)s groups="!base.group_portal"/>
                <field name="inherit_id" %(attrs)s/>
            </form>
        """,
            add_field_with_groups=False,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="!base.test_group"/>
                <field name="name" groups="base.test_group"/>
                <field name="inherit_id" %(attrs)s groups="base.group_multi_company"/>
            </form>
        """,
            add_field_with_groups=False,
        )

        validate(
            """
            <form string="View">
                <field name="name" groups="base.group_multi_company"/>
                <field name="name" groups="!base.test_group"/>
                <field name="name" groups="base.test_group"/>
                <field name="inherit_id" %(attrs)s groups="base.group_multi_company"/>
                <field name="inherit_id" %(attrs)s groups="base.test_group"/>
                <field name="inherit_id" %(attrs)s groups="!base.test_group"/>
                <field name="inherit_id" %(attrs)s groups="base.group_public"/>
            </form>
        """,
            add_field_with_groups=False,
        )

    def test_18_test_missing_group(self):
        group_a = self.env["res.groups"].create({"name": "test_a"})
        data = self.env["ir.model.data"].create(
            {
                "module": "base",
                "name": "group_test_a",
                "model": "res.groups",
                "res_id": group_a.id,
            }
        )

        view = self.View.create(
            {
                "name": "foo",
                "model": "res.partner",
                "arch": """
                <form>
                    <group groups="base.group_user,base.group_test_a">
                        <group groups="!base.group_system">
                            <div id="foo"/>
                        </group>
                        <group groups="!base.group_test_a">
                            <div id="bar"/>
                        </group>
                    </group>
                    <group groups="base.group_test_a">
                        <div id="stuff"/>
                    </group>
                </form>
            """,
            }
        )

        data.unlink()
        group_a.unlink()

        user_demo = self.user_demo
        self.assertFalse(user_demo.has_group("base.group_system"))
        arch = (
            self.env["res.partner"]
            .with_user(user_demo)
            .get_view(view_id=view.id)["arch"]
        )
        tree = etree.fromstring(arch)
        self.assertTrue(tree.xpath('//div[@id="foo"]'))
        self.assertTrue(tree.xpath('//div[@id="bar"]'))
        self.assertFalse(tree.xpath('//div[@id="stuff"]'))

        user_admin = self.env.ref("base.user_admin")
        self.assertTrue(user_admin.has_group("base.group_system"))
        arch = (
            self.env["res.partner"]
            .with_user(user_admin)
            .get_view(view_id=view.id)["arch"]
        )
        tree = etree.fromstring(arch)
        self.assertFalse(tree.xpath('//div[@id="foo"]'))
        self.assertTrue(tree.xpath('//div[@id="bar"]'))
        self.assertFalse(tree.xpath('//div[@id="stuff"]'))


@tagged("post_install", "-at_install")
class TestViewArchRecovery(ViewCase):
    def _translated_view(self):
        view = self.assertValid(
            '<form string="Partners"><field name="name"/></form>',
            name="translated view",
            model="res.partner",
        )
        self.env["res.lang"]._activate_lang("fr_FR")
        view._update_field_translations(
            "arch_db", {"fr_FR": {"Partners": "Partenaires"}}
        )
        view.invalidate_recordset()
        return view

    def test_arch_prev_is_language_neutral(self):
        for field in ("arch", "arch_base", "arch_db"):
            with self.subTest(field=field):
                view = self._translated_view()
                view.with_context(lang="fr_FR").write(
                    {
                        field: '<form string="Partenaires">'
                        '<field name="name"/><field name="function"/></form>'
                    }
                )
                view.invalidate_recordset()
                self.assertIn("Partners", view.arch_prev)
                self.assertNotIn("Partenaires", view.arch_prev)

    def test_soft_reset_preserves_source_and_translation(self):
        view = self._translated_view()
        view.with_context(lang="fr_FR").write(
            {
                "arch": '<form string="Partenaires">'
                '<field name="name"/><field name="function"/></form>'
            }
        )
        view.invalidate_recordset()

        view.reset_arch(mode="soft")
        view.invalidate_recordset()

        self.assertIn(
            "Partners", view.with_context(lang="en_US").arch_db, "source arch corrupted"
        )
        self.assertIn(
            "Partenaires",
            view.with_context(lang="fr_FR").arch_db,
            "translation destroyed",
        )

    def test_hard_reset_without_resolvable_file_is_a_true_noop(self):
        view = self.assertValid(
            '<form string="Original"><field name="name"/></form>', name="unresolvable"
        )
        view.write({"arch_fs": "base/views/does_not_exist.xml"})
        view.write({"arch": '<form string="Edited"><field name="name"/></form>'})
        view.invalidate_recordset()
        before = (view.arch_db, view.arch_prev, view.arch_updated)
        self.assertTrue(before[1])

        with mute_logger("odoo.addons.base.models.ir_ui_view"):
            self.assertFalse(view.reset_arch(mode="hard"))
        view.invalidate_recordset()

        self.assertEqual((view.arch_db, view.arch_prev, view.arch_updated), before)

    def test_hard_reset_from_file_still_works(self):
        view = self.env.ref("base.view_res_partner_filter")
        inheriting = self.env["ir.ui.view"].search_count([("inherit_id", "=", view.id)])
        if inheriting:
            self.skipTest(
                f"{inheriting} installed view(s) inherit base.view_res_partner_filter; "
                "hard-reset validity requires a database where nothing does"
            )
        original = view.arch_db
        view.write({"arch": '<search><field name="name"/></search>'})
        view.invalidate_recordset()
        self.assertNotEqual(view.arch_db, original)

        self.assertEqual(view.reset_arch(mode="hard"), view)
        view.invalidate_recordset()
        self.assertEqual(view.arch_db.strip(), original.strip())
        self.assertFalse(view.arch_updated)

    def test_get_arch_from_file_reports_unresolvable_as_none(self):
        view = self.assertValid('<form><field name="name"/></form>', name="no arch_fs")
        self.assertIsNone(view._get_arch_from_file())


@tagged("post_install", "-at_install")
class TestViewRevalidation(ViewCase):
    def _tree(self):
        parent = self.assertValid(
            '<form><field name="name"/></form>', name="p", model="res.partner"
        )
        first = self.assertValid(
            '<field name="name" position="after"><field name="function"/></field>',
            name="c1",
            inherit_id=parent.id,
            model="res.partner",
        )
        second = self.assertValid(
            '<field name="function" position="after"><field name="lang"/></field>',
            name="c2",
            inherit_id=parent.id,
            model="res.partner",
        )
        first.write({"priority": 10})
        second.write({"priority": 20})
        return parent, first, second

    def test_reordering_by_priority_is_rejected(self):
        _parent, _first, second = self._tree()
        with mute_logger("odoo.addons.base.models.ir_ui_view"):
            with self.assertRaises(ValidationError):
                second.write({"priority": 5})

    def test_changing_mode_to_primary_is_validated(self):
        _parent, first, _second = self._tree()
        with mute_logger("odoo.addons.base.models.ir_ui_view"):
            with self.assertRaises(ValidationError):
                first.write({"mode": "primary"})

    def test_a_harmless_mode_change_is_still_allowed(self):
        parent = self.assertValid(
            '<form><field name="name"/></form>', name="lonely p", model="res.partner"
        )
        child = self.assertValid(
            '<field name="name" position="after"><field name="function"/></field>',
            name="lonely c",
            inherit_id=parent.id,
            model="res.partner",
        )
        child.write({"mode": "primary"})
        self.assertEqual(child.mode, "primary")

    def test_rewriting_the_same_value_does_not_revalidate(self):
        _parent, first, _second = self._tree()
        with patch.object(
            type(self.View), "_check_xml", autospec=True, return_value=True
        ) as checked:
            first.write({"priority": 10, "mode": "extension"})
        self.assertFalse(checked.called)

    def test_record_loading_warns_instead_of_aborting(self):
        _parent, _first, second = self._tree()
        with self.assertLogs(
            "odoo.addons.base.models.ir_ui_view", level="WARNING"
        ) as log_catcher:
            second.with_context(ir_ui_view_loading_records=True).write({"priority": 5})
        self.assertTrue(any("unable to combine" in line for line in log_catcher.output))

    def test_a_refused_recombination_writes_nothing(self):
        _parent, _first, second = self._tree()
        with mute_logger("odoo.addons.base.models.ir_ui_view"):
            try:
                second.write({"priority": 5})
            except ValidationError:
                pass
            else:
                self.fail("the reordering was not refused")
        self.assertEqual(second.priority, 20)
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT priority FROM ir_ui_view WHERE id = %s", [second.id]
        )
        self.assertEqual(self.env.cr.fetchone()[0], 20)

    def test_an_already_broken_tree_stays_writable(self):
        _parent, _first, second = self._tree()
        with mute_logger("odoo.addons.base.models.ir_ui_view"):
            second.with_context(ir_ui_view_loading_records=True).write({"priority": 5})
        second.write({"priority": 4})
        self.assertEqual(second.priority, 4)

    def test_changing_the_value_revalidates(self):
        _parent, first, _second = self._tree()
        with patch.object(
            type(self.View), "_check_xml", autospec=True, return_value=True
        ) as checked:
            first.write({"priority": 11})
        self.assertTrue(checked.called)


@tagged("post_install", "-at_install")
class TestViewWriteContract(ViewCase):
    def test_write_leaves_the_callers_dict_alone(self):
        primary = self.assertValid(
            '<form><field name="name"/></form>', name="wc p", model="res.partner"
        )
        other = self.assertValid(
            '<form><field name="name"/></form>', name="wc o", model="res.partner"
        )
        # the form arch reads as a spec on the other's form, so it stays
        vals = {"inherit_id": other.id}
        primary.write(vals)
        self.assertEqual(vals, {"inherit_id": other.id})
        self.assertEqual(primary.mode, "extension")
        vals = {"inherit_id": False}
        primary.write(vals)
        self.assertEqual(vals, {"inherit_id": False})
        self.assertEqual(primary.mode, "primary")

    def test_create_through_arch_base_keeps_the_arch_as_previous(self):
        arch = '<form><field name="name"/></form>'
        view = self.View.create(
            {"name": "ab", "model": "res.partner", "arch_base": arch}
        )
        self.assertEqual(view.arch_prev, arch)
        self.assertEqual(view.arch_db, arch)
        # and a later write still saves what it overwrites
        view.write({"arch_base": '<form><field name="email"/></form>'})
        self.assertEqual(view.arch_prev, arch)

    def test_an_overlay_replacing_the_root_is_validated_whole(self):
        primary = self.assertValid(
            '<form><field name="name"/></form>', name="rr p", model="res.partner"
        )
        self.assertInvalid(
            """
            <xpath expr="/form" position="replace">
                <form><field name="name" invisible="not_a_field"/></form>
            </xpath>
            """,
            "not_a_field",
            inherit_id=primary.id,
            model="res.partner",
        )

    def test_a_customization_made_while_loading_is_still_dropped(self):
        Custom = self.env["ir.ui.view.custom"]
        with self.env.registry.loading_window():
            view = self.assertValid(
                '<form><field name="name"/></form>', name="cl", model="res.partner"
            )
            view.write({"priority": 5})  # takes the snapshot
            custom = Custom.create(
                {
                    "ref_id": view.id,
                    "user_id": self.env.uid,
                    "arch": '<form><field name="name"/></form>',
                }
            )
            view.write({"arch": '<form><field name="email"/></form>'})
            self.assertFalse(custom.exists())

    def test_an_overlay_replacing_the_root_with_text_is_refused(self):
        # the XML combine used to hand back None here, a crash for every
        # reader of the result; a replace of the root needs one element
        primary = self.assertValid(
            '<form><field name="name"/></form>', name="rt p", model="res.partner"
        )
        self.assertInvalid(
            '<xpath expr="/form" position="replace">just text</xpath>',
            "needs an element",
            inherit_id=primary.id,
            model="res.partner",
        )

    def test_two_overlays_setting_one_attribute_report_a_conflict(self):
        primary = self.assertValid(
            '<form><field name="name"/></form>', name="cf p", model="res.partner"
        )
        for index in range(2):
            self.assertValid(
                f"""
                <field name="name" position="attributes">
                    <attribute name="string">Label {index}</attribute>
                </field>
                """,
                name=f"cf {index}",
                inherit_id=primary.id,
                model="res.partner",
            )
        with self.assertLogs(
            "odoo.debug.logic.base.ir_ui_view", level="DEBUG"
        ) as log_catcher:
            arch = primary.get_combined_arch()
        self.assertIn('string="Label 1"', arch)
        conflicts = [
            line
            for line in log_catcher.output
            if "event=combine.attribute_conflicts" in line
        ]
        self.assertEqual(len(conflicts), 1, log_catcher.output)
        self.assertIn("attributes=['string']", conflicts[0])
        self.assertIn("targets=['field:name']", conflicts[0])


@tagged("post_install", "-at_install")
class TestPreloadViews(ViewCase):
    def test_a_digit_int_refuses_is_a_missing_template_not_a_crash(self):
        preload = self.View._preload_views(["²", "999999999", "no.such_template"])
        self.assertIsInstance(preload["²"]["error"], MissingError)
        self.assertIsInstance(preload["no.such_template"]["error"], MissingError)
        self.assertIsInstance(preload[999999999]["error"], MissingError)


@tagged("post_install", "-at_install")
class TestAttributeConflicts(ViewCase):
    def _conflicts(self, view):
        # assertLogs fails on silence, and no conflict is the point here
        records = []
        handler = logging.Handler()
        handler.emit = records.append
        logger = logging.getLogger("odoo.debug.logic.base.ir_ui_view")
        level = logger.level
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        try:
            view.get_combined_arch()
        finally:
            logger.removeHandler(handler)
            logger.setLevel(level)
        return [
            record.getMessage()
            for record in records
            if "event=combine.attribute_conflicts" in record.getMessage()
        ]

    def _set_string(self, name, inherit_id, mode, label, priority=16):
        return self.View.create(
            {
                "name": name,
                "model": "res.partner",
                "inherit_id": inherit_id,
                "mode": mode,
                "priority": priority,
                "arch": f"""<field name="name" position="attributes">
                    <attribute name="string">{label}</attribute></field>""",
            }
        )

    def test_a_primary_child_overriding_its_base_is_no_conflict(self):
        primary = self.assertValid(
            '<form><field name="name"/></form>', name="ac p", model="res.partner"
        )
        self._set_string("ac ext", primary.id, "extension", "Base label")
        child = self._set_string("ac child", primary.id, "primary", "Child label")
        self.assertEqual(self._conflicts(child), [])
        self.assertIn('string="Child label"', child.get_combined_arch())

    def test_an_extension_over_a_primary_child_setting_is_a_conflict(self):
        primary = self.assertValid(
            '<form><field name="name"/></form>', name="ac p2", model="res.partner"
        )
        child = self._set_string("ac child2", primary.id, "primary", "Child label")
        self._set_string("ac child ext", child.id, "extension", "Extension label")
        conflicts = self._conflicts(child)
        self.assertEqual(len(conflicts), 1, conflicts)
        self.assertIn("attributes=['string']", conflicts[0])


@tagged("post_install", "-at_install")
class TestCombineBatching(ViewCase):
    def _tree(self, size):
        root = self.assertValid(
            '<form><field name="name"/></form>', name="cb root", model="res.partner"
        )
        extensions = self.View.browse()
        for index in range(size):
            extensions += self.assertValid(
                f"""<field name="name" position="attributes">
                    <attribute name="x{index}">1</attribute></field>""",
                name=f"cb {index}",
                inherit_id=root.id,
                model="res.partner",
            )
        return root, extensions

    def _combines(self, fn):
        with self.assertLogs(
            "odoo.debug.pipeline.base.ir_ui_view", level="DEBUG"
        ) as log_catcher:
            fn()
        return sum("event=combine " in line for line in log_catcher.output)

    def test_views_under_one_root_are_combined_once_per_check(self):
        _root, extensions = self._tree(6)
        self.assertEqual(self._combines(extensions._check_xml), 1)

    def _cache_work(self, fn):
        clears = []
        searches = []
        Custom = type(self.env["ir.ui.view.custom"])
        original_search = Custom.search

        def counting_search(model, *args, **kwargs):
            searches.append(args)
            return original_search(model, *args, **kwargs)

        with (
            patch.object(
                type(self.env.registry),
                "clear_cache",
                lambda registry, *names: clears.append(names),
            ),
            patch.object(Custom, "search", counting_search),
        ):
            fn()
        return len(clears), len(searches)

    def test_an_arch_write_on_many_views_validates_the_tree_once(self):
        _root, extensions = self._tree(6)
        self.assertEqual(
            self._combines(lambda: extensions.write({"arch": "<data/>"})), 1
        )
        self.assertEqual(set(extensions.mapped("arch")), {"<data/>"})
        # and it still validates: a broken arch is refused
        with mute_logger("odoo.addons.base.models.ir_ui_view"):
            with self.assertRaises(ValidationError):
                extensions.write(
                    {"arch": '<field name="nope" position="after"><div/></field>'}
                )

    def test_an_arch_write_clears_the_cache_and_drops_customizations_once(self):
        _root, extensions = self._tree(6)
        self.assertEqual(
            self._cache_work(lambda: extensions.write({"arch": "<data/>"})), (1, 1)
        )

    def test_an_arch_base_write_on_many_views_validates_the_tree_once(self):
        _root, extensions = self._tree(6)
        self.assertEqual(
            self._combines(lambda: extensions.write({"arch_base": "<data/>"})), 1
        )
        self.assertEqual(set(extensions.mapped("arch_base")), {"<data/>"})
        self.assertEqual(
            self._cache_work(lambda: extensions.write({"arch_base": "<data/>"})),
            (1, 1),
        )
        with mute_logger("odoo.addons.base.models.ir_ui_view"):
            with self.assertRaises(ValidationError):
                extensions.write(
                    {"arch_base": '<field name="nope" position="after"><div/></field>'}
                )


@tagged("post_install", "-at_install")
class TestSiblingPrimaryCheck(ViewCase):
    """While loading, the check keeps only loaded siblings; these trees
    carry no xmlid, so they are what the check sees once the registry is
    ready."""

    def _tree(self, depth, extensions_per_level=1, primaries=2):
        root = self.assertValid(
            '<form><field name="name"/><group name="g0"/></form>',
            name="sp root",
            model="res.partner",
        )
        parent = root
        extensions = self.View.browse()
        for level in range(depth):
            chain = self.assertValid(
                f'<group name="g{level}" position="inside">'
                f'<group name="g{level + 1}"/></group>',
                name=f"sp ext {level}",
                inherit_id=parent.id,
                model="res.partner",
            )
            extensions += chain
            for index in range(1, extensions_per_level):
                extensions += self.assertValid(
                    f'<group name="g{level}" position="attributes">'
                    f'<attribute name="col">{index + 1}</attribute></group>',
                    name=f"sp ext {level}.{index}",
                    inherit_id=parent.id,
                    model="res.partner",
                )
            parent = chain
        for index in range(primaries):
            self.View.create(
                {
                    "name": f"sp primary {index}",
                    "model": "res.partner",
                    "mode": "primary",
                    "inherit_id": extensions[index % depth].id,
                    "arch": '<field name="name" position="attributes">'
                    '<attribute name="readonly">1</attribute></field>',
                }
            )
        return root, extensions

    def _sibling_checks(self, fn):
        with self.assertLogs(
            "odoo.debug.pipeline.base.ir_ui_view", level="DEBUG"
        ) as log_catcher:
            fn()
        return [
            line
            for line in log_catcher.output
            if "event=sibling_primary_views_checked" in line
        ]

    def test_the_siblings_of_one_root_are_checked_once_per_batch(self):
        _root, extensions = self._tree(depth=3, extensions_per_level=2)
        checks = self._sibling_checks(extensions._check_xml)
        self.assertEqual(len(checks), 1, checks)
        self.assertIn("siblings=2", checks[0])

    def test_the_check_finds_primaries_hanging_off_deep_extensions(self):
        _root, extensions = self._tree(depth=3)
        checks = self._sibling_checks(extensions[-1]._check_xml)
        self.assertIn("siblings=2", checks[0])
        # a broken sibling is what the check is for
        extensions[-1].write({"arch": '<group name="g2" position="replace"/>'})
        with mute_logger("odoo.addons.base.models.ir_ui_view"):
            with self.assertRaises(ValidationError):
                extensions[0].write({"arch": '<field name="name" position="replace"/>'})


@tagged("post_install", "-at_install")
class TestCustomViews(ViewCase):
    def test_each_model_under_a_root_keeps_its_latest_custom_view(self):
        root = self.env.ref("base.view_partner_form")
        older = self.assertValid(
            "<data/>", name="c A0", inherit_id=root.id, model="res.partner"
        )
        newer = self.assertValid(
            "<data/>", name="c A1", inherit_id=root.id, model="res.partner"
        )
        other_model = self.View.create(
            {
                "name": "c B",
                "model": "res.users",
                "inherit_id": root.id,
                "mode": "primary",
                "arch": "<data/>",
            }
        )
        custom = self.View._get_custom_views()
        self.assertIn(newer, custom)
        self.assertIn(other_model, custom)
        self.assertNotIn(older, custom)
        self.assertEqual(custom & (older + newer + other_model), newer + other_model)
        self.assertEqual(
            self.View._get_custom_views(["res.partner"])
            & (older + newer + other_model),
            newer,
        )

    def test_a_view_of_a_module_the_database_knows_is_shipped(self):
        root = self.env.ref("base.view_partner_form")
        shipped = self.assertValid(
            "<data/>", name="s", inherit_id=root.id, model="res.partner"
        )
        self.env["ir.model.data"].create(
            {
                "module": "base",
                "name": "probe_shipped",
                "model": "ir.ui.view",
                "res_id": shipped.id,
            }
        )
        unknown = self.assertValid(
            "<data/>", name="u", inherit_id=root.id, model="res.partner"
        )
        self.env["ir.model.data"].create(
            {
                "module": "no_such_module",
                "name": "probe_unknown",
                "model": "ir.ui.view",
                "res_id": unknown.id,
            }
        )
        custom = self.View._get_custom_views(["res.partner"])
        self.assertNotIn(shipped, custom)
        self.assertIn(unknown, custom)


@tagged("post_install", "-at_install")
class TestViewGroupsPostprocessing(ViewCase):
    def test_groups_on_the_root_node_is_rejected(self):
        self.assertInvalid(
            '<form groups="base.group_system"><field name="name"/></form>',
            "The root node of a view cannot carry a 'groups' attribute",
            model="res.partner",
        )

    def test_unwrapping_a_t_groups_block_keeps_its_text(self):
        group_key = self.env["res.groups"]._get_group_definitions().universe.key
        node = etree.fromstring(
            '<form><group><t __groups_key__="%s">HELLO<field name="name"/></t>'
            'WORLD<field name="function"/></group></form>' % group_key
        )
        self.View._postprocess_access_rights(node)
        arch = etree.tostring(node, encoding="unicode")
        self.assertIn("HELLO", arch)
        self.assertIn("WORLD", arch)
        self.assertNotIn("<t", arch)

    def test_unwrapping_a_childless_t_keeps_its_text(self):
        group_key = self.env["res.groups"]._get_group_definitions().universe.key
        node = etree.fromstring(
            '<form><group><field name="name"/>'
            '<t __groups_key__="%s">ONLYTEXT</t>TAIL</group></form>' % group_key
        )
        self.View._postprocess_access_rights(node)
        arch = etree.tostring(node, encoding="unicode")
        self.assertIn("ONLYTEXT", arch)
        self.assertIn("TAIL", arch)


@tagged("post_install", "-at_install")
class TestViewArchSerialization(ViewCase):
    def test_indentation_tabs_are_stripped(self):
        view = self.assertValid(
            '<form>\n\t<field name="name"/>\n</form>',
            name="tabbed",
            model="res.partner",
        )
        arch = self.env["res.partner"].get_view(view.id, "form")["arch"]
        self.assertNotIn("\t", arch)

    def test_tabs_inside_real_text_survive(self):
        view = self.assertValid(
            '<form><div>a\tb</div><field name="name"/></form>',
            name="tab in text",
            model="res.partner",
        )
        arch = self.env["res.partner"].get_view(view.id, "form")["arch"]
        self.assertIn("a\tb", arch)


@tagged("post_install", "-at_install")
class TestViewCreateRobustness(ViewCase):
    def test_unparseable_arch_without_name_reports_the_arch(self):
        with mute_logger("odoo.addons.base.models.ir_ui_view"):
            with self.assertRaises(ValidationError):
                self.View.create({"model": "res.partner", "arch": "<form>"})

    def test_non_string_arch_is_reported_as_a_view_error(self):
        arch = etree.Element("form")
        arch.append(etree.Element("field", name="name"))
        with mute_logger("odoo.addons.base.models.ir_ui_view"):
            with self.assertRaises((ValidationError, UserError)):
                self.View.create({"model": "res.partner", "arch": arch})

    def test_encoding_declaration_is_rejected_on_every_arch_field(self):
        declared = (
            "<?xml version='1.0' encoding='utf-8'?><form><field name=\"name\"/></form>"
        )
        for field in ("arch", "arch_base", "arch_db"):
            with self.subTest(field=field, op="create"):
                with self.assertRaises(UserError):
                    self.View.create(
                        {"name": "enc", "model": "res.partner", field: declared}
                    )
        view = self.assertValid(
            '<form><field name="name"/></form>',
            name="enc target",
            model="res.partner",
        )
        for field in ("arch", "arch_base", "arch_db"):
            with self.subTest(field=field, op="write"):
                with self.assertRaises(UserError):
                    view.write({field: declared})


@tagged("post_install", "-at_install")
class TestTemplateKeyCollision(ViewCase):
    def _pair(self, key):
        generic = self.View.create(
            {
                "name": "generic",
                "type": "qweb",
                "key": key,
                "priority": 50,
                "arch": '<t t-name="%s">GENERIC</t>' % key,
            }
        )
        specific = self.View.create(
            {
                "name": "specific",
                "type": "qweb",
                "key": key,
                "priority": 1,
                "arch": '<t t-name="%s">SPECIFIC</t>' % key,
            }
        )
        self.env.registry.clear_cache("templates")
        self.env.cr.cache.pop("_compile_batch_", None)
        return generic, specific

    def test_a_view_sharing_a_key_stays_reachable_by_id(self):
        generic, specific = self._pair("base.collision_tpl")
        fetched = self.View._get_views_by_ref([generic.id, "base.collision_tpl"])
        self.assertEqual(fetched[generic.id], generic)
        self.assertEqual(fetched["base.collision_tpl"], specific)

    def test_the_key_still_resolves_by_priority(self):
        generic, specific = self._pair("base.collision_tpl2")
        self.assertEqual(self.View._get_template_view("base.collision_tpl2"), specific)
        self.assertEqual(self.View._get_template_view(generic.id), generic)

    def test_a_mixed_batch_does_not_cache_an_existing_view_as_missing(self):
        generic, _specific = self._pair("base.collision_tpl3")
        self.View._preload_views([generic.id, "base.collision_tpl3"])
        self.assertEqual(self.env["ir.qweb"]._render(generic.id, {}), Markup("GENERIC"))


@tagged("post_install", "-at_install")
class TestViewErrorReporting(ViewCase):
    def test_error_quotes_the_offending_line(self):
        arch = (
            "<form>\n"
            + "".join("<div>%s</div>\n" % i for i in range(30))
            + '<field name="function" context="{a b}"/>\n</form>'
        )
        with mute_logger("odoo.addons.base.models.ir_ui_view"):
            with self.assertRaises(ValidationError) as catcher:
                self.View.create({"name": "ctx", "model": "res.partner", "arch": arch})
        self.assertIn('context="{a b}"', str(catcher.exception.args[0]))

    def test_error_shows_the_arch_before_validation_mutated_it(self):
        with mute_logger("odoo.addons.base.models.ir_ui_view"):
            with self.assertRaises(ValidationError) as catcher:
                self.View.create(
                    {
                        "name": "sub",
                        "model": "res.partner",
                        "arch": '<form><field name="child_ids">'
                        "<list><notebook/></list></field></form>",
                    }
                )
        self.assertIn("notebook", str(catcher.exception.args[0]))

    def test_untyped_view_reports_the_real_problem(self):
        with mute_logger("odoo.addons.base.models.ir_ui_view"):
            with self.assertRaises(ValidationError) as catcher:
                self.View.create({"model": "res.partner", "arch": "<form>"})
        self.assertIn(
            "view type could not be determined", str(catcher.exception.args[0])
        )

    def test_private_view_error_names_the_view(self):
        view = self.assertValid(
            '<form><field name="name"/></form>',
            name="private view",
            model="res.partner",
        )
        with self.assertRaises(AccessError) as catcher:
            view._check_view_access()
        self.assertIn("private view", str(catcher.exception.args[0]))

    def test_check_view_access_requires_a_single_view(self):
        views = self.View.search([], limit=2)
        with self.assertRaises(ValueError):
            views._check_view_access()


@tagged("post_install", "-at_install")
class TestInheritingViewsQuery(ViewCase):
    def test_cte_skips_columns_no_combination_step_reads(self):
        fields = self.View._get_fields_inheriting_views()
        for required in ("arch_db", "inherit_id", "mode", "priority", "model"):
            self.assertIn(required, fields)
        for excluded in ("arch_prev", "create_uid", "write_date"):
            self.assertNotIn(excluded, fields)

    def test_a_joining_domain_is_reported_against_the_hook(self):
        view = self.env.ref("base.view_res_partner_filter")
        with patch.object(
            type(self.View),
            "_get_domain_inheriting_views",
            return_value=Domain("inherit_id.name", "!=", "zzz"),
        ):
            with self.assertRaises(ValueError) as catcher:
                view._get_views_inheriting()
        self.assertIn("_get_domain_inheriting_views", str(catcher.exception))


class TestViewArchFileResolution(common.TransactionCase):
    def test_a_qualified_xmlid_wins_over_a_bare_one(self):
        source = (
            "<odoo>\n"
            '  <record id="dup" model="ir.ui.view">'
            '<field name="arch" type="xml"><form>SHORT</form></field></record>\n'
            '  <record id="base.dup" model="ir.ui.view">'
            '<field name="arch" type="xml"><form>QUALIFIED</form></field></record>\n'
            "</odoo>"
        )
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".xml", delete=False
        ) as handle:
            handle.write(source)
            path = handle.name
        self.addCleanup(os.unlink, path)

        self.assertIn("QUALIFIED", ir_ui_view.get_view_arch_from_file(path, "base.dup"))
        self.assertIn("SHORT", ir_ui_view.get_view_arch_from_file(path, "other.dup"))

    def test_a_rewritten_file_is_read_again_and_the_tree_is_not_edited(self):
        def record(text):
            return (
                '<odoo><record id="v" model="ir.ui.view">'
                f'<field name="arch" type="xml"><form>{text}</form></field>'
                "</record></odoo>"
            )

        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".xml", delete=False
        ) as handle:
            handle.write(record("FIRST"))
            path = handle.name
        self.addCleanup(os.unlink, path)
        self.assertIn("FIRST", ir_ui_view.get_view_arch_from_file(path, "base.v"))
        # the same parse serves the second read
        with patch.object(
            ir_ui_view.etree, "parse", wraps=ir_ui_view.etree.parse
        ) as parse:
            self.assertIn("FIRST", ir_ui_view.get_view_arch_from_file(path, "base.v"))
        parse.assert_not_called()
        # a new version of the file is parsed again
        time.sleep(0.01)
        pathlib.Path(path).write_text(record("SECOND"), encoding="utf-8")
        self.assertIn("SECOND", ir_ui_view.get_view_arch_from_file(path, "base.v"))


class TestGroupbyPostprocessTermination(ViewCase):
    def test_a_self_referencing_groupby_does_not_recurse(self):
        view = self.View.create(
            {
                "name": "self-referencing groupby",
                "model": "res.partner",
                "type": "list",
                "arch": """<list>
                    <field name="name"/>
                    <groupby name="parent_id">
                        <field name="display_name"/>
                    </groupby>
                </list>""",
            }
        )
        result = self.env["res.partner"].get_view(view_id=view.id, view_type="list")
        self.assertIn("groupby", result["arch"])

    def test_the_groupby_contents_are_still_processed_against_the_comodel(self):
        view = self.View.create(
            {
                "name": "groupby comodel",
                "model": "res.partner",
                "type": "list",
                "arch": """<list>
                    <field name="name"/>
                    <groupby name="parent_id">
                        <field name="display_name"/>
                    </groupby>
                </list>""",
            }
        )
        arch = etree.fromstring(
            self.env["res.partner"].get_view(view_id=view.id, view_type="list")["arch"]
        )
        groupby = arch.find("groupby")
        self.assertIsNotNone(groupby, "the node survives the detached-scope pass")
        self.assertEqual(
            [child.get("name") for child in groupby.iter("field")],
            ["display_name"],
            "its children come back, and come back processed",
        )


class TestFilterDefaultPeriodChildren(ViewCase):
    def _search_view(self, child):
        return self.View.create(
            {
                "name": "filter children",
                "model": "res.partner",
                "type": "search",
                "arch": f"""<search>
                    <filter name="f" date="create_date"
                            default_period="month" domain="[]">{child}</filter>
                </search>""",
            }
        )

    def test_a_comment_child_does_not_raise_a_bare_keyerror(self):
        self.assertTrue(self._search_view("<!-- a note -->"))

    def test_an_unnamed_element_child_does_not_raise_a_bare_keyerror(self):
        self.assertTrue(self._search_view("<separator/>"))

    def test_a_named_child_still_registers_as_a_custom_period(self):
        view = self._search_view('<filter name="mine" domain="[]"/>')
        view.write({"arch": view.arch.replace('"month"', '"custom_mine"')})
        self.assertIn("custom_mine", view.arch)

    def test_an_unknown_default_period_is_still_rejected(self):
        with self.assertRaises(ValidationError):
            self._search_view("").write(
                {
                    "arch_db": """<search>
                    <filter name="f" date="create_date"
                            default_period="fortnight" domain="[]"/>
                </search>"""
                }
            )


class TestCopyRegeneratesTheKey(ViewCase):
    def _qweb(self):
        return self.View.create(
            {
                "name": "keyed template",
                "type": "qweb",
                "key": "base.copy_key_probe",
                "arch": "<t t-name='base.copy_key_probe'>x</t>",
            }
        )

    def test_a_plain_copy_gets_its_own_key(self):
        original = self._qweb()
        self.assertNotEqual(original.copy().key, original.key)

    def test_an_empty_default_is_the_same_request_as_no_default(self):
        original = self._qweb()
        self.assertNotEqual(original.copy({}).key, original.key)

    def test_an_explicit_key_is_honoured(self):
        original = self._qweb()
        self.assertEqual(original.copy({"key": "base.chosen"}).key, "base.chosen")

    def test_the_copy_is_not_a_cow_specific_view_of_its_original(self):
        original = self._qweb()
        copy = original.copy()
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertNotIn(copy.id, original._get_views_specific().ids)


@tagged("post_install", "-at_install")
class TestCombineIsBatched(ViewCase):
    def _forms(self, count):
        views = self.View.create(
            [
                {
                    "name": f"batched {index}",
                    "model": "res.partner",
                    "type": "form",
                    "arch": f'<form><field name="name"/><!--{index}--></form>',
                }
                for index in range(count)
            ]
        )
        self.env.flush_all()
        self.env.invalidate_all()
        return self.View.browse(views.ids)

    def _queries_to_validate(self, count):
        views = self._forms(count)
        before = self.env.cr.sql_statement_count
        views._check_xml()
        return self.env.cr.sql_statement_count - before

    def test_validating_many_views_costs_one_combine_not_one_each(self):
        small = self._queries_to_validate(2)
        large = self._queries_to_validate(20)
        self.assertLessEqual(
            large - small,
            2,
            f"validating 18 more views cost {large - small} more queries "
            f"({small} at N=2, {large} at N=20). _check_xml() is combining one "
            f"view at a time again; _get_combined_archs() does the whole set "
            f"in one recursive CTE.",
        )

    def test_the_batched_and_looped_combines_agree(self):
        root = self.View.create(
            {
                "name": "combine root",
                "model": "res.partner",
                "type": "form",
                "arch": '<form><field name="name"/></form>',
            }
        )
        extension = self.View.create(
            {
                "name": "combine extension",
                "model": "res.partner",
                "type": "form",
                "inherit_id": root.id,
                "arch": """<data>
                    <xpath expr="//field[@name='name']" position="after">
                        <field name="email"/>
                    </xpath>
                </data>""",
            }
        )
        self.env.flush_all()
        self.env.invalidate_all()
        pair = self.View.browse([root.id, extension.id])

        looped = [
            etree.tostring(view._get_combined_arch(), encoding="unicode")
            for view in pair
        ]
        self.env.invalidate_all()
        pair = self.View.browse([root.id, extension.id])
        batched = [
            etree.tostring(tree, encoding="unicode")
            for tree in pair._get_combined_archs()
        ]
        self.assertEqual(looped, batched)


class TestCombineBatchingAtInstall(ViewCase):
    def test_the_batch_resolves_each_view_as_if_alone_while_loading(self):
        self.assertFalse(self.env.registry.ready, "this must run at install")
        roots = self.View.create(
            [
                {
                    "name": f"batched {index}",
                    "model": "res.partner",
                    "type": "form",
                    "arch": f'<form><field name="name"/><!--{index}--></form>',
                }
                for index in range(3)
            ]
        )
        extensions = self.View.create(
            [
                {
                    "name": f"batched ext {index}",
                    "model": "res.partner",
                    "inherit_id": root.id,
                    "arch": f'<field name="name" position="after"><field name="function"/><!--e{index}--></field>',
                }
                for index, root in enumerate(roots)
            ]
        )
        views = roots + extensions
        batched = views._get_combined_archs_by_id()
        self.assertEqual(set(batched), set(views.ids))
        for view in views:
            self.assertEqual(
                etree.tostring(batched[view.id]),
                etree.tostring(view._get_combined_arch()),
                view.name,
            )


class TestResetArchRejectsAnUnknownMode(ViewCase):
    def test_an_unknown_mode_raises_rather_than_reporting_nothing_to_do(self):
        view = self.View.create(
            {
                "name": "reset mode",
                "model": "res.partner",
                "type": "form",
                "arch": '<form><field name="name"/></form>',
            }
        )
        with self.assertRaises(ValueError):
            view.reset_arch(mode="sideways")


class TestPreloadViewsIgnoresFalsyRefs(ViewCase):
    def test_a_none_ref_is_skipped_rather_than_crashing(self):
        self.assertIsInstance(self.View._preload_views([None]), dict)

    def test_an_empty_ref_is_skipped(self):
        self.assertIsInstance(self.View._preload_views([""]), dict)


class TestBothPhasesShareOneScope(ViewCase):
    ARCH = """<form>
        <field name="name"/>
        <group groups="base.group_system">
            <field name="model"/>
            <field name="type" readonly="1"/>
        </group>
        <notebook>
            <page string="p"><field name="arch_db"/></page>
        </notebook>
    </form>"""

    def _scopes(self, phase):
        seen = []
        View = type(self.View)
        original = View._iter_arch_nodes

        def traced(view, root, get_node_info):
            for node, info in original(view, root, get_node_info):
                seen.append((node.tag, info))
                yield node, info

        view = self.View.create(
            {
                "name": "shared scope",
                "model": "ir.ui.view",
                "type": "form",
                "arch": self.ARCH,
            }
        )
        tree = etree.fromstring(view.arch)
        View._iter_arch_nodes = traced
        try:
            if phase == "check":
                view._check_view(tree, "ir.ui.view")
            else:
                view._postprocess_view(tree, "ir.ui.view")
        finally:
            View._iter_arch_nodes = original
        return seen

    SHARED_KEYS = frozenset(
        {
            "view_type",
            "model_groups",
            "view_groups",
            "editable",
            "name_manager",
            "group_definitions",
        }
    )

    def test_both_phases_build_the_same_shared_keys(self):
        for phase in ("check", "post"):
            with self.subTest(phase=phase):
                for tag, info in self._scopes(phase):
                    self.assertLessEqual(
                        self.SHARED_KEYS,
                        set(info),
                        f"<{tag}> in the {phase} phase is missing shared scope keys",
                    )

    def test_only_the_phase_specific_keys_differ(self):
        check = {k for _tag, info in self._scopes("check") for k in info}
        post = {k for _tag, info in self._scopes("post") for k in info}
        self.assertEqual(
            check - post,
            {"validate"},
            "the check phase carries exactly one key of its own",
        )
        self.assertEqual(
            post - check,
            {"mobile"},
            "and the postprocess phase exactly one of its own",
        )

    def test_children_appears_only_where_a_handler_steers_the_walk(self):
        plain = {k for _tag, info in self._scopes("post") for k in info}
        self.assertNotIn("children", plain)

        view = self.View.create(
            {
                "name": "steered walk",
                "model": "ir.ui.view",
                "type": "search",
                "arch": """<search>
                    <field name="name"/>
                    <searchpanel><field name="type" select="one"/></searchpanel>
                </search>""",
            }
        )
        steered = []
        View = type(self.View)
        original = View._iter_arch_nodes

        def traced(v, root, get_node_info):
            for node, info in original(v, root, get_node_info):
                steered.append(info)
                yield node, info

        tree = etree.fromstring(view.arch)
        View._iter_arch_nodes = traced
        try:
            view._postprocess_view(tree, "ir.ui.view")
        finally:
            View._iter_arch_nodes = original
        self.assertTrue(
            any("children" in info for info in steered),
            "_postprocess_tag_search steers the walk past the searchpanel it "
            "has already processed, and does it through node_info",
        )

    def test_view_groups_narrows_identically_in_both_phases(self):
        by_phase = {}
        for phase in ("check", "post"):
            by_phase[phase] = [
                (tag, info["view_groups"].key)
                for tag, info in self._scopes(phase)
                if isinstance(tag, str)
            ]
        self.assertEqual(
            by_phase["check"],
            by_phase["post"],
            "the two phases disagree about which groups a node is scoped to",
        )

    def test_editable_narrows_identically_in_both_phases(self):
        by_phase = {}
        for phase in ("check", "post"):
            by_phase[phase] = [
                (tag, bool(info["editable"]))
                for tag, info in self._scopes(phase)
                if isinstance(tag, str)
            ]
        self.assertEqual(by_phase["check"], by_phase["post"])

    def test_a_groups_attribute_narrows_the_scope_below_it(self):
        for phase in ("check", "post"):
            with self.subTest(phase=phase):
                scopes = {
                    tag: info
                    for tag, info in self._scopes(phase)
                    if isinstance(tag, str)
                }
                self.assertNotEqual(
                    scopes["form"]["view_groups"].key,
                    scopes["group"]["view_groups"].key,
                    "a node carrying `groups` must narrow view_groups for its "
                    "subtree, in both phases",
                )

    def test_refine_runs_before_the_groups_narrowing(self):
        seen = []

        def refine(node, info):
            seen.append((node.tag, info["view_groups"].key))

        tree = etree.fromstring("<form><group groups='base.group_system'/></form>")
        _manager, get_node_info = self.View._get_arch_scope(
            tree, "ir.ui.view", None, translate=False, editable=True, refine=refine
        )
        root_info = get_node_info(tree, None)
        get_node_info(tree.find("group"), root_info)
        self.assertEqual(
            seen[1][1],
            seen[0][1],
            "refine saw the scope already narrowed by the node's own groups",
        )


class TestSteeringDoesNotHideASubtreeFromTheSchema(ViewCase):
    def _create(self, model, view_type, arch):
        return self.View.create(
            {"name": "steering", "model": model, "type": view_type, "arch": arch}
        )

    def test_a_searchpanel_body_the_schema_rejects_is_rejected(self):
        with self.assertRaises(ValidationError):
            self._create(
                "res.partner",
                "search",
                '<search><field name="name"/>'
                "<searchpanel><separator/></searchpanel></search>",
            )

    def test_a_groupby_body_the_schema_rejects_is_rejected(self):
        with self.assertRaises(ValidationError):
            self._create(
                "res.partner",
                "list",
                '<list><field name="name"/>'
                '<groupby name="parent_id"><separator/></groupby></list>',
            )

    def test_a_valid_searchpanel_still_passes(self):
        self.assertTrue(
            self._create(
                "res.partner",
                "search",
                '<search><field name="name"/>'
                '<searchpanel><field name="parent_id" select="one"/></searchpanel>'
                "</search>",
            )
        )

    def test_a_valid_groupby_still_passes(self):
        self.assertTrue(
            self._create(
                "res.partner",
                "list",
                '<list><field name="name"/>'
                '<groupby name="parent_id"><field name="display_name"/></groupby>'
                "</list>",
            )
        )

    def test_the_searchpanel_survives_validation_in_the_tree(self):
        view = self._create(
            "res.partner",
            "search",
            '<search><field name="name"/>'
            '<searchpanel><field name="parent_id" select="one"/></searchpanel>'
            "</search>",
        )
        tree = etree.fromstring(view.arch)
        view._check_view(tree, "res.partner")
        self.assertIsNotNone(
            tree.find("searchpanel"),
            "_check_view must leave the searchpanel where valid_view can see it",
        )

    def test_a_groupby_keeps_its_children_through_validation(self):
        view = self._create(
            "res.partner",
            "list",
            '<list><field name="name"/>'
            '<groupby name="parent_id"><field name="display_name"/></groupby>'
            "</list>",
        )
        tree = etree.fromstring(view.arch)
        view._check_view(tree, "res.partner")
        groupby = tree.find("groupby")
        self.assertEqual(
            [child.get("name") for child in groupby],
            ["display_name"],
            "E.groupby(*node) reparents the children; they must be put back, or "
            "list_view.rng never sees what the groupby contained",
        )

    def test_the_searchpanel_is_walked_once_not_twice(self):
        view = self._create(
            "res.partner",
            "search",
            '<search><field name="name"/>'
            '<searchpanel><field name="parent_id" select="one"/></searchpanel>'
            "</search>",
        )
        seen = []
        handler = type(ELEMENT_HANDLERS["searchpanel"])
        original = handler.check

        def counted(h, v, node, name_manager, node_info):
            seen.append(node)
            return original(h, v, node, name_manager, node_info)

        with patch.object(handler, "check", counted):
            view._check_view(etree.fromstring(view.arch), "res.partner")
        self.assertEqual(len(seen), 1, "the searchpanel was validated twice")


class TestViewHeaderIsNotCached(ViewCase):
    def test_the_header_follows_the_context_not_the_first_caller(self):
        Partner = self.registry["res.partner"]

        def header(model, view_id, view_type):
            tag = model.env.context.get("hdr_tag")
            return f"Partners: {tag}" if tag else False

        with patch.object(Partner, "view_header_get", header):
            self.env.registry.clear_cache("templates")
            tagged_arch = (
                self.env["res.partner"].with_context(hdr_tag="ZZTAG").get_view()["arch"]
            )
            plain_arch = self.env["res.partner"].get_view()["arch"]

        self.assertEqual(etree.fromstring(tagged_arch).get("string"), "Partners: ZZTAG")
        self.assertNotEqual(
            etree.fromstring(plain_arch).get("string"),
            "Partners: ZZTAG",
            "the first caller's context must not be served to the next one",
        )

    def test_the_list_root_gets_its_header_too(self):
        Partner = self.registry["res.partner"]
        with patch.object(
            Partner, "view_header_get", lambda model, view_id, view_type: "HDR"
        ):
            self.env.registry.clear_cache("templates")
            arch = self.env["res.partner"].get_view(view_type="list")["arch"]
        self.assertEqual(etree.fromstring(arch).get("string"), "HDR")


class TestNestedSubviewsAreChecked(ViewCase):
    def test_attrs_on_a_nested_list_is_refused(self):
        self.assertInvalid(
            """<form>
                <field name="inherit_children_ids">
                    <list><field name="name" attrs="{}"/></list>
                </field>
            </form>""",
            'Since 17.0, the "attrs" and "states" attributes are no longer used.',
        )

    def test_states_on_a_nested_form_is_refused(self):
        self.assertInvalid(
            """<list>
                <field name="inherit_children_ids">
                    <form><field name="name" states="draft"/></form>
                </field>
            </list>""",
            'Since 17.0, the "attrs" and "states" attributes are no longer used.',
        )

    def test_a_clean_nested_list_still_passes(self):
        self.assertValid(
            """<form>
                <field name="inherit_children_ids">
                    <list><field name="name"/></list>
                </field>
            </form>"""
        )

    def test_an_unknown_attribute_on_a_nested_list_is_refused(self):
        self.assertInvalid(
            """<form>
                <field name="inherit_children_ids">
                    <list bogus="1"><field name="name"/></list>
                </field>
            </form>""",
            "Invalid <list> subview definition",
        )

    def test_groups_on_nested_lists_are_accepted(self):
        self.assertValid(
            """<form>
                <field name="inherit_children_ids">
                    <list groups="base.group_user"><field name="name"/></list>
                    <list groups="base.group_system"><field name="model"/></list>
                </field>
            </form>"""
        )

    def test_no_open_on_a_nested_list_is_accepted(self):
        self.assertValid(
            """<form>
                <field name="inherit_children_ids">
                    <list no_open="1"><field name="name"/></list>
                </field>
            </form>"""
        )

    def test_a_partially_validated_extension_of_a_nested_list_is_accepted(self):
        base = self.assertValid(
            """<form>
                <field name="inherit_children_ids">
                    <list><field name="name"/></list>
                </field>
            </form>"""
        )
        self.View.with_context(ir_ui_view_partial_validation=True).create(
            {
                "name": "extension",
                "model": "ir.ui.view",
                "inherit_id": base.id,
                "arch": """<xpath expr="//list/field[@name='name']" position="attributes">
                    <attribute name="string">Renamed</attribute>
                </xpath>""",
            }
        )

    def test_control_create_with_invisible_on_a_nested_list_is_accepted(self):
        self.assertValid(
            """<form>
                <field name="inherit_children_ids">
                    <list editable="bottom">
                        <control>
                            <create string="Add" invisible="not id" class="x"/>
                            <delete invisible="not id"/>
                        </control>
                        <field name="name"/>
                    </list>
                </field>
            </form>"""
        )


class TestXmlIdFollowsTheFirstDeclaration(ViewCase):
    def test_the_oldest_declaration_wins_over_the_alphabetical_one(self):
        view = self.assertValid("<form><field name='name'/></form>")
        self.env["ir.model.data"].create(
            [
                {
                    "module": "zzz_orig",
                    "name": "v1",
                    "model": "ir.ui.view",
                    "res_id": view.id,
                },
                {
                    "module": "aaa_later",
                    "name": "v1",
                    "model": "ir.ui.view",
                    "res_id": view.id,
                },
            ]
        )
        view.invalidate_recordset(["xml_id", "model_data_id"])
        self.assertEqual(view.xml_id, "zzz_orig.v1")


class TestViewModeScrub(ViewCase):
    """Deleting a model's last view of a type it generates no default arch for
    takes that type out of the model's window actions. base itself registers
    no such window type -- qweb has no default but is no window mode, and every
    window mode base has is generated -- so the two halves are pinned apart:
    which (model, type) pairs qualify, and what the scrub does to the actions.
    web_grid's tests drive the whole path with a real type.
    """

    def _action(self, view_mode):
        return self.env["ir.actions.act_window"].create(
            {"name": "partners", "res_model": "res.partner", "view_mode": view_mode}
        )

    def test_only_a_type_without_a_default_arch_qualifies(self):
        qweb = self.View.create(
            {
                "name": "scrub_qweb",
                "model": "res.partner",
                "type": "qweb",
                "arch": "<t t-name='scrub_qweb'>x</t>",
            }
        )
        graph = self.View.create(
            {
                "name": "scrub_graph",
                "model": "res.partner",
                "type": "graph",
                "arch": "<graph><field name='name'/></graph>",
            }
        )
        self.assertEqual(
            (qweb | graph)._view_modes_without_default(), {("res.partner", "qweb")}
        )

    def test_the_scrub_leaves_the_actions_of_a_model_with_no_view_left(self):
        action = self._action("list,graph,form")
        other_model = self.env["ir.actions.act_window"].create(
            {"name": "users", "res_model": "res.users", "view_mode": "list,graph"}
        )
        alone = self._action("graph")
        self.View.search(
            [("model", "=", "res.partner"), ("type", "=", "graph")]
        ).unlink()
        self.env["ir.actions.act_window"]._remove_view_modes_without_views(
            {("res.partner", "graph")}
        )
        self.assertEqual(action.view_mode, "list,form")
        self.assertEqual(
            alone.view_mode, "list", "an action of that mode alone falls back to list"
        )
        self.assertEqual(
            other_model.view_mode,
            "list,graph",
            "another model's actions are not touched",
        )

    def test_the_scrub_leaves_the_actions_alone_while_a_view_remains(self):
        self.View.create(
            {
                "name": "scrub_graph_kept",
                "model": "res.partner",
                "type": "graph",
                "arch": "<graph><field name='name'/></graph>",
            }
        )
        action = self._action("list,graph")
        self.env["ir.actions.act_window"]._remove_view_modes_without_views(
            {("res.partner", "graph")}
        )
        self.assertEqual(action.view_mode, "list,graph")
