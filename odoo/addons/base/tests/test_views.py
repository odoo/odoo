# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import re
import time
from contextlib import contextmanager

from functools import partial
from collections import defaultdict

from lxml import etree
from lxml.builder import E
from psycopg2 import IntegrityError
from psycopg2.extras import Json

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import common, tagged
from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.tools import mute_logger, view_validation, safe_eval
from odoo.tools.cache import get_cache_key_counter
from odoo.addons.base.models import ir_ui_view

_logger = logging.getLogger(__name__)


class ViewXMLID(common.TransactionCase):
    def test_model_data_id(self):
        """ Check whether views know their xmlid record. """
        view = self.env.ref('base.view_company_form')
        self.assertTrue(view)
        self.assertTrue(view.model_data_id)
        self.assertEqual(view.model_data_id.complete_name, 'base.view_company_form')


class ViewCase(TransactionCaseWithUserDemo):
    def setUp(self):
        super(ViewCase, self).setUp()
        self.View = self.env['ir.ui.view']

    def assertValid(self, arch, name='valid view', inherit_id=False, model='ir.ui.view'):
        return self.View.create({
            'name': name,
            'model': model,
            'inherit_id': inherit_id,
            'arch': arch,
        })

    def assertInvalid(self, arch, expected_message=None, name='invalid view', inherit_id=False, model='ir.ui.view'):
        with mute_logger('odoo.addons.base.models.ir_ui_view'):
            with self.assertRaises(ValidationError) as catcher:
                self.View.create({
                    'name': name,
                    'model': model,
                    'inherit_id': inherit_id,
                    'arch': arch,
                })
        message = str(catcher.exception.args[0])
        self.assertEqual(catcher.exception.context['name'], name)
        if expected_message:
            self.assertIn(expected_message, message)
        else:
            _logger.warning(message)

    def assertWarning(self, arch, expected_message=None, name='invalid view', model='ir.ui.view'):
        with self.assertLogs('odoo.addons.base.models.ir_ui_view', level="WARNING") as log_catcher:
            self.View.create({
                'name': name,
                'model': model,
                'arch': arch,
            })
        self.assertEqual(len(log_catcher.output), 1, "Exactly one warning should be logged")
        message = log_catcher.output[0]
        self.assertIn('View error context', message)
        self.assertIn("'name': '%s'" % name, message)
        if expected_message:
            self.assertIn(expected_message, message)


class TestNodeLocator(common.TransactionCase):
    """
    The node locator returns None when it can not find a node, and the first
    match when it finds something (no jquery-style node sets)
    """

    def test_no_match_xpath(self):
        """
        xpath simply uses the provided @expr pattern to find a node
        """
        node = self.env['ir.ui.view'].locate_node(
            E.root(E.foo(), E.bar(), E.baz()),
            E.xpath(expr="//qux"),
        )
        self.assertIsNone(node)

    def test_match_xpath(self):
        bar = E.bar()
        node = self.env['ir.ui.view'].locate_node(
            E.root(E.foo(), bar, E.baz()),
            E.xpath(expr="//bar"),
        )
        self.assertIs(node, bar)

    def test_no_match_field(self):
        """
        A field spec will match by @name against all fields of the view
        """
        node = self.env['ir.ui.view'].locate_node(
            E.root(E.foo(), E.bar(), E.baz()),
            E.field(name="qux"),
        )
        self.assertIsNone(node)

        node = self.env['ir.ui.view'].locate_node(
            E.root(E.field(name="foo"), E.field(name="bar"), E.field(name="baz")),
            E.field(name="qux"),
        )
        self.assertIsNone(node)

    def test_match_field(self):
        bar = E.field(name="bar")
        node = self.env['ir.ui.view'].locate_node(
            E.root(E.field(name="foo"), bar, E.field(name="baz")),
            E.field(name="bar"),
        )
        self.assertIs(node, bar)

    def test_no_match_other(self):
        """
        Non-xpath non-fields are matched by node name first
        """
        node = self.env['ir.ui.view'].locate_node(
            E.root(E.foo(), E.bar(), E.baz()),
            E.qux(),
        )
        self.assertIsNone(node)

    def test_match_other(self):
        bar = E.bar()
        node = self.env['ir.ui.view'].locate_node(
            E.root(E.foo(), bar, E.baz()),
            E.bar(),
        )
        self.assertIs(bar, node)

    def test_attribute_mismatch(self):
        """
        Non-xpath non-field are filtered by matching attributes on spec and
        matched nodes
        """
        node = self.env['ir.ui.view'].locate_node(
            E.root(E.foo(attr='1'), E.bar(attr='2'), E.baz(attr='3')),
            E.bar(attr='5'),
        )
        self.assertIsNone(node)

    def test_attribute_filter(self):
        match = E.bar(attr='2')
        node = self.env['ir.ui.view'].locate_node(
            E.root(E.bar(attr='1'), match, E.root(E.bar(attr='3'))),
            E.bar(attr='2'),
        )
        self.assertIs(node, match)

    def test_version_mismatch(self):
        """
        A @version on the spec will be matched against the view's version
        """
        node = self.env['ir.ui.view'].locate_node(
            E.root(E.foo(attr='1'), version='4'),
            E.foo(attr='1', version='3'),
        )
        self.assertIsNone(node)


class TestViewInheritance(ViewCase):
    def arch_for(self, name, view_type='form', parent=None):
        """ Generates a trivial view of the specified ``view_type``.

        The generated view is empty but ``name`` is set as its root's ``@string``.

        If ``parent`` is not falsy, generates an extension view (instead of
        a root view) replacing the parent's ``@string`` by ``name``

        :param str name: ``@string`` value for the view root
        :param str view_type:
        :param bool parent:
        :return: generated arch
        :rtype: str
        """
        if not parent:
            element = E(view_type, string=name)
        else:
            element = E(view_type,
                E.attribute(name, name='string'),
                position='attributes'
            )
        return etree.tostring(element, encoding='unicode')

    def makeView(self, name, parent=None, arch=None):
        """ Generates a basic ir.ui.view with the provided name, parent and arch.

        If no parent is provided, the view is top-level.

        If no arch is provided, generates one by calling :meth:`~.arch_for`.

        :param str name:
        :param int parent: id of the parent view, if any
        :param str arch:
        :returns: the created view's id.
        :rtype: int
        """
        view = self.View.create({
            'model': self.model,
            'name': name,
            'arch': arch or self.arch_for(name, parent=parent),
            'inherit_id': parent,
            'priority': 5, # higher than default views
        })
        self.view_ids[name] = view
        return view

    def get_views(self, names):
        return self.View.concat(*(self.view_ids[name] for name in names))

    def setUp(self):
        super(TestViewInheritance, self).setUp()

        self.patch(self.registry, '_init', False)

        self.model = 'ir.ui.view.custom'
        self.view_ids = {}

        self.a = self.makeView("A")
        self.a1 = self.makeView("A1", self.a.id)
        self.a2 = self.makeView("A2", self.a.id)
        self.a11 = self.makeView("A11", self.a1.id)
        self.a11.mode = 'primary'
        self.makeView("A111", self.a11.id)
        self.makeView("A12", self.a1.id)
        self.makeView("A21", self.a2.id)
        self.a22 = self.makeView("A22", self.a2.id)
        self.makeView("A221", self.a22.id)

        self.b = self.makeView('B', arch=self.arch_for("B", 'list'))
        self.makeView('B1', self.b.id, arch=self.arch_for("B1", 'list', parent=self.b))
        self.c = self.makeView('C', arch=self.arch_for("C", 'list'))
        self.c.write({'priority': 1})

        self.d = self.makeView("D")
        self.d1 = self.makeView("D1", self.d.id)
        self.d1.arch = None

    def test_get_inheriting_views(self):
        self.assertEqual(
            self.view_ids['A']._get_inheriting_views(),
            self.get_views('A A1 A2 A12 A21 A22 A221'.split()),
        )
        self.assertEqual(
            self.view_ids['A21']._get_inheriting_views(),
            self.get_views(['A21']),
        )
        self.assertEqual(
            self.view_ids['A11']._get_inheriting_views(),
            self.get_views(['A11', 'A111']),
        )
        self.assertEqual(
            (self.view_ids['A11'] + self.view_ids['A'])._get_inheriting_views(),
            self.get_views('A A1 A2 A11 A111 A12 A21 A22 A221'.split()),
        )

    def test_default_view(self):
        default = self.View.default_view(model=self.model, view_type='form')
        self.assertEqual(default, self.view_ids['A'].id)

        default_list = self.View.default_view(model=self.model, view_type='list')
        self.assertEqual(default_list, self.view_ids['C'].id)

    def test_no_default_view(self):
        self.assertFalse(self.View.default_view(model='no_model.exist', view_type='form'))
        self.assertFalse(self.View.default_view(model=self.model, view_type='graph'))

    def test_no_recursion(self):
        r1 = self.makeView('R1')
        with self.assertRaises(ValidationError):
            r1.write({'inherit_id': r1.id})

        r2 = self.makeView('R2', r1.id)
        r3 = self.makeView('R3', r2.id)
        with self.assertRaises(ValidationError):
            r2.write({'inherit_id': r3.id})

        with self.assertRaises(ValidationError):
            r1.write({'inherit_id': r3.id})

        with self.assertRaises(ValidationError):
            r1.write({
                'inherit_id': r1.id,
                'arch': self.arch_for('itself', parent=True),
            })

    def test_write_arch(self):
        self.env['res.lang']._activate_lang('fr_FR')

        v = self.makeView("T", arch='<form string="Foo">Bar</form>')
        v.update_field_translations('arch_db', {'fr_FR': {'Foo': 'Fou', 'Bar': 'Barre'}})
        self.assertEqual(v.arch, '<form string="Foo">Bar</form>')

        # modify v to discard translations; this should not invalidate 'arch'!
        v.arch = '<form/>'
        self.assertEqual(v.arch, '<form/>')

    def test_get_combined_arch_query_count(self):
        # If the query count increases, you probably made the view combination
        # fetch an extra field on views. You better fetch that extra field with
        # the query of _get_inheriting_views() and manually feed the cache.
        self.env.invalidate_all()
        with self.assertQueryCount(3):
            # 1: browse([self.view_ids['A']])
            # 2: _get_inheriting_views: id, inherit_id, mode, groups
            # 3: _combine: arch_db
            self.view_ids['A'].get_combined_arch()

    def test_view_validate_button_action_query_count(self):
        _, _, counter = get_cache_key_counter(self.env['ir.model.data']._xmlid_lookup, 'base.action_ui_view')
        hit, miss = counter.hit, counter.miss

        with self.assertQueryCount(10):
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

        with self.assertQueryCount(5):
            self.assertValid("""
                <field name="name" position="replace"/>
            """, inherit_id=base_view.id)
        self.assertEqual(counter.hit, hit + 2)
        self.assertEqual(counter.miss, miss + 2)

    def test_view_validate_attrs_groups_query_count(self):
        _, _, counter = get_cache_key_counter(self.env['ir.model.data']._xmlid_lookup, 'base.group_system')
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
            self.assertValid("""
                <field name="name" position="replace">
                    <field name="key" groups="base.group_system"/>
                </field>
            """, inherit_id=base_view.id)
        self.assertEqual(counter.hit, hit)
        self.assertEqual(counter.miss, miss)

    def test_no_arch(self):
        self.d1._check_xml()

    def test_invalid_locators(self):
        """ Check ir.ui.view's invalid_locators field is computed correctly."""
        base_view_arch = """
            <form string="View">
                <div name="div1">
                    <field name="id"/>
                </div>
            </form>
        """
        base_view = self.makeView('invalid_xpath_base_view', arch=base_view_arch)

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

        child_view = self.View.create({
            'model': self.model,
            'name': "child_view",
            'arch': child_view_arch,
            'inherit_id': base_view.id,
            'priority': 10,
            'active': False,
        })

        child_primary_no_arch = self.View.create({
            'model': self.model,
            'name': "child_view",
            'inherit_id': base_view.id,
            'priority': 18,
            'active': False,
        })

        self.assertEqual(
            child_view.invalid_locators,
            [
                {
                    "tag": "xpath",
                    "attrib": {"expr": "//form/div[1]/div[1]", "position": "attributes"},
                    "sourceline": 2,
                },
                {
                    'tag': 'field',
                    'attrib': {'name': 'invalid_field', 'position': 'after'},
                    'sourceline': 5
                },
                {
                    'tag': 'xpath',
                    'attrib': {'expr': "//field[@name='invalid_field']", 'position': 'move'},
                    'sourceline': 9
                }
            ],
        )

        self.assertEqual(child_primary_no_arch.invalid_locators, False)

    def test_invalid_locators_with_valid_xpath(self):
        """ Check ir.ui.view's invalid_locators field is computed correctly."""
        base_view_arch = """
            <form string="View">
                <div name="div1">
                    <field name="id"/>
                </div>
            </form>
        """
        base_view = self.makeView('invalid_xpath_base_view', arch=base_view_arch)

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

        child_view = self.View.create({
            'model': self.model,
            'name': "child_view",
            'arch': child_view_arch,
            'inherit_id': base_view.id,
            'priority': 10,
            'active': False,
        })

        child_applied = self.View.create({
            'model': self.model,
            'name': "child_view",
            'arch': """<data>
                <!-- One comment: should be ignored -->
                <field name="id" position="before">
                    <div class="parasite" />
                </field>
                </data>""",
            'inherit_id': base_view.id,
            'priority': 10,
            'active': True,
        })

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

        child_view2 = self.View.create({
            'model': self.model,
            'name': "child_view",
            'arch': child_view_arch2,
            'inherit_id': base_view.id,
            'priority': 10,
            'active': False,
        })

        child_view3 = self.View.create({
            'model': self.model,
            'name': "child_view",
            'arch': """<data>
                        <xpath expr="//div[hasclass('parasite')]" position="inside" >
                            <div class="invalid" />
                        </xpath>
                    </data>""",
            'inherit_id': base_view.id,
            'priority': 7,
            'active': False,
        })

        child_view4 = self.View.create({
            'model': self.model,
            'name': "child_view",
            'arch': """<data>
                        <xpath expr="//div[hasclass('parasite')]" position="inside" >
                            <div class="valid" />
                        </xpath>
                    </data>""",
            'inherit_id': child_applied.id,
            'priority': 5,
            'active': True,
        })

        # Assert that accessing invalid_locators does not cause database writes.
        actual_queries = []
        with contextmanager(lambda: self._patchExecute(actual_queries))():
            self.assertEqual(child_applied.invalid_locators, False)
        self.assertTrue(len(actual_queries) > 0)

        re_sql_update = re.compile(r'\bupdate\b', re.IGNORECASE)
        self.assertFalse(any(re_sql_update.search(q) for q in actual_queries))

        self.assertEqual(child_view.invalid_locators, [{'tag': 'xpath', 'attrib': {'expr': "//div[hasclass('parasite')]", 'position': 'inside'}, 'sourceline': 8}])
        self.assertEqual(child_view2.invalid_locators, [{'tag': 'field', 'attrib': {'name': 'user_id', 'position': 'after'}, 'sourceline': 5}])
        self.assertEqual(child_view3.invalid_locators, [{'tag': 'xpath', 'attrib': {'expr': "//div[hasclass('parasite')]", 'position': 'inside'}, 'sourceline': 2}])
        self.assertEqual(child_view4.invalid_locators, False)

    def test_nested_move_invalid_locator(self):
        """ Check ir.ui.view's invalid_locators field is computed correctly."""
        base_view_arch = """
            <form string="View">
                <div name="div1">
                    <div>
                        <span />
                    </div>
                </div>
            </form>
        """
        base_view = self.makeView('invalid_xpath_base_view', arch=base_view_arch)

        child_view = self.View.create({
            'model': self.model,
            'name': "child_view",
            'inherit_id': base_view.id,
            'priority': 10,
            'active': False,
            'arch': """
            <data>
                <xpath expr="/form/div/div" position="replace">
                    <xpath expr="/form/div/div/span" position="move" />
                </xpath>
            </data>
            """,
        })
        self.assertEqual(child_view.invalid_locators, False)

        child_view.arch = """
            <data>
                <xpath expr="/form/div/div" position="replace">
                    <xpath expr="/form/div/div/h1" position="move" />
                </xpath>
            </data>"""
        self.assertEqual(child_view.invalid_locators,
            [{
                'attrib': {
                    'expr': '/form/div/div/h1',
                    'position': 'move',
                },
                'sourceline': 3,
                'tag': 'xpath',
            }])

    def test_broken_hierarchy_locators(self):
        self.patch(self.env.registry.get("ir.ui.view"), "_check_xml", lambda self: True)
        view = self.View.create({
            'model': self.model,
            'name': "child_view",
            'arch': "<form></form>",
            'active': True,
        })
        broken = self.View.create({
            'model': self.model,
            'inherit_id': view.id,
            'name': "child_view",
            'arch': """<data><xpath expr="//group" position="after"><div /></xpath></data>""",
            'active': True,
        })
        not_broken = self.View.create({
            'model': self.model,
            'inherit_id': view.id,
            'name': "child_view",
            'arch': """<data><xpath expr="/form" position="inside"><div /></xpath></data>""",
            'active': True,
        })

        self.assertEqual(broken.invalid_locators, [{
            'attrib': {'expr': '//group', 'position': 'after'},
            'sourceline': 1,
            'tag': 'xpath'
        }])
        self.assertEqual(not_broken.invalid_locators, [{"broken_hierarchy": True}])


class TestApplyInheritanceSpecs(ViewCase):
    """ Applies a sequence of inheritance specification nodes to a base
    architecture. IO state parameters (cr, uid, model, context) are used for
    error reporting

    The base architecture is altered in-place.
    """
    def setUp(self):
        super(TestApplyInheritanceSpecs, self).setUp()
        self.base_arch = E.form(
            E.field(name="target"),
            string="Title")
        self.adv_arch = E.form(
            E.field(
                "TEXT1",
                E.field(name="subtarget"),
                "TEXT2",
                E.field(name="anothersubtarget"),
                "TEXT3",
                name="target",
            ),
            string="Title")

    def test_replace_outer(self):
        spec = E.field(
                E.field(name="replacement"),
                name="target", position="replace")

        self.View.apply_inheritance_specs(self.base_arch, spec)

        self.assertEqual(
            self.base_arch,
            E.form(E.field(name="replacement"), string="Title"))

    def test_delete(self):
        spec = E.field(name="target", position="replace")

        self.View.apply_inheritance_specs(self.base_arch, spec)

        self.assertEqual(
            self.base_arch,
            E.form(string="Title"))

    def test_insert_after(self):
        spec = E.field(
                E.field(name="inserted"),
                name="target", position="after")

        self.View.apply_inheritance_specs(self.base_arch, spec)

        self.assertEqual(
            self.base_arch,
            E.form(
                E.field(name="target"),
                E.field(name="inserted"),
                string="Title"
            ))

    def test_insert_before(self):
        spec = E.field(
                E.field(name="inserted"),
                name="target", position="before")

        self.View.apply_inheritance_specs(self.base_arch, spec)

        self.assertEqual(
            self.base_arch,
            E.form(
                E.field(name="inserted"),
                E.field(name="target"),
                string="Title"))

    def test_insert_inside(self):
        default = E.field(E.field(name="inserted"), name="target")
        spec = E.field(E.field(name="inserted 2"), name="target", position='inside')

        self.View.apply_inheritance_specs(self.base_arch, default)
        self.View.apply_inheritance_specs(self.base_arch, spec)

        self.assertEqual(
            self.base_arch,
            E.form(
                E.field(
                    E.field(name="inserted"),
                    E.field(name="inserted 2"),
                    name="target"),
                string="Title"))

    def test_replace_inner(self):
        spec = E.field(
            "TEXT 4",
            E.field(name="replacement"),
            "TEXT 5",
            E.field(name="replacement2"),
            "TEXT 6",
            name="target", position="replace", mode="inner")

        expected = E.form(
            E.field(
                "TEXT 4",
                E.field(name="replacement"),
                "TEXT 5",
                E.field(name="replacement2"),
                "TEXT 6",
                name="target"),
            string="Title")

        # applying spec to both base_arch and adv_arch is expected to give the same result
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
            name="target", position="replace", mode="inner")

        expected = E.form(
            E.field(
                "TEXT 4",
                E.field(name="anothersubtarget"),
                "TEXT 5",
                E.field(name="subtarget"),
                "TEXT 6",
                name="target"),
            string="Title")

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
                    name="target"),
                string="Title"))

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_invalid_position(self):
        spec = E.field(
                E.field(name="whoops"),
                name="target", position="serious_series")

        with self.assertRaises(ValueError):
            self.View.apply_inheritance_specs(self.base_arch, spec)

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_incorrect_version(self):
        # Version ignored on //field elements, so use something else
        arch = E.form(E.element(foo="42"))
        spec = E.element(
            E.field(name="placeholder"),
            foo="42", version="7.0")

        with self.assertRaises(ValueError):
            self.View.apply_inheritance_specs(arch, spec)

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_target_not_found(self):
        spec = E.field(name="targut")

        with self.assertRaises(ValueError):
            self.View.apply_inheritance_specs(self.base_arch, spec)


class TestApplyInheritanceWrapSpecs(ViewCase):
    def setUp(self):
        super(TestApplyInheritanceWrapSpecs, self).setUp()
        self.base_arch = E.template(E.div(E.p("Content")))

    def apply_spec(self, spec):
        self.View.apply_inheritance_specs(self.base_arch, spec)

    def test_replace(self):
        spec = E.xpath(
            E.div("$0", {'class': "some"}),
            expr="//p", position="replace")

        self.apply_spec(spec)
        self.assertEqual(
            self.base_arch,
            E.template(E.div(
                E.div(E.p('Content'), {'class': 'some'})
            ))
        )


class TestApplyInheritanceMoveSpecs(ViewCase):
    def setUp(self):
        super(TestApplyInheritanceMoveSpecs, self).setUp()
        self.base_arch = E.template(
            E.div(E.p("Content", {'class': 'some'})),
            E.div({'class': 'target'})
        )
        self.wrapped_arch = E.template(
            E.div("aaaa", E.p("Content", {'class': 'some'}), "bbbb"),
            E.div({'class': 'target'})
        )

    def apply_spec(self, arch, spec):
        self.View.apply_inheritance_specs(arch, spec)

    def test_move_replace(self):
        spec = E.xpath(
            E.xpath(expr="//p", position="move"),
            expr="//div[@class='target']", position="replace")

        self.apply_spec(self.base_arch, spec)
        self.assertEqual(
            self.base_arch,
            E.template(
                E.div(),
                E.p("Content", {'class': 'some'})
            )
        )
        self.apply_spec(self.wrapped_arch, spec)
        self.assertEqual(
            self.wrapped_arch,
            E.template(
                E.div("aaaabbbb"),
                E.p("Content", {'class': 'some'})
            )
        )

    def test_move_inside(self):
        spec = E.xpath(
            E.xpath(expr="//p", position="move"),
            expr="//div[@class='target']", position="inside")

        self.apply_spec(self.base_arch, spec)
        self.assertEqual(
            self.base_arch,
            E.template(
                E.div(),
                E.div(E.p("Content", {'class': 'some'}), {'class': 'target'})
            )
        )
        self.apply_spec(self.wrapped_arch, spec)
        self.assertEqual(
            self.wrapped_arch,
            E.template(
                E.div("aaaabbbb"),
                E.div(E.p("Content", {'class': 'some'}), {'class': 'target'})
            )
        )

    def test_move_before(self):
        spec = E.xpath(
            E.xpath(expr="//p", position="move"),
            expr="//div[@class='target']", position="before")

        self.apply_spec(self.base_arch, spec)
        self.assertEqual(
            self.base_arch,
            E.template(
                E.div(""),
                E.p("Content", {'class': 'some'}),
                E.div({'class': 'target'}),
            )
        )
        self.apply_spec(self.wrapped_arch, spec)
        self.assertEqual(
            self.wrapped_arch,
            E.template(
                E.div("aaaabbbb"),
                E.p("Content", {'class': 'some'}),
                E.div({'class': 'target'}),
            )
        )

    def test_move_after(self):
        spec = E.xpath(
            E.xpath(expr="//p", position="move"),
            expr="//div[@class='target']", position="after")

        self.apply_spec(self.base_arch, spec)
        self.assertEqual(
            self.base_arch,
            E.template(
                E.div(),
                E.div({'class': 'target'}),
                E.p("Content", {'class': 'some'}),
            )
        )
        self.apply_spec(self.wrapped_arch, spec)
        self.assertEqual(
            self.wrapped_arch,
            E.template(
                E.div("aaaabbbb"),
                E.div({'class': 'target'}),
                E.p("Content", {'class': 'some'}),
            )
        )

    def test_move_with_other_1(self):
        # multiple elements with move in first position
        spec = E.xpath(
            E.xpath(expr="//p", position="move"),
            E.p("Content2", {'class': 'new_p'}),
            expr="//div[@class='target']", position="after")

        self.apply_spec(self.base_arch, spec)
        self.assertEqual(
            self.base_arch,
            E.template(
                E.div(),
                E.div({'class': 'target'}),
                E.p("Content", {'class': 'some'}),
                E.p("Content2", {'class': 'new_p'}),
            )
        )

    def test_move_with_other_2(self):
        # multiple elements with move in last position
        spec = E.xpath(
            E.p("Content2", {'class': 'new_p'}),
            E.xpath(expr="//p", position="move"),
            expr="//div[@class='target']", position="after")

        self.apply_spec(self.wrapped_arch, spec)
        self.assertEqual(
            self.wrapped_arch,
            E.template(
                E.div("aaaabbbb"),
                E.div({'class': 'target'}),
                E.p("Content2", {'class': 'new_p'}),
                E.p("Content", {'class': 'some'}),
            )
        )

    def test_move_with_tail(self):
        moved_paragraph_xpath = E.xpath(expr="//p", position="move")
        moved_paragraph_xpath.tail = "tail of paragraph"
        spec = E.xpath(
            E.p("Content2", {'class': 'new_p'}),
            moved_paragraph_xpath,
            expr="//div[@class='target']", position="after")

        self.apply_spec(self.wrapped_arch, spec)

        moved_paragraph = E.p("Content", {'class': 'some'})
        moved_paragraph.tail = "tail of paragraph"
        self.assertEqual(
            self.wrapped_arch,
            E.template(
                E.div("aaaabbbb"),
                E.div({'class': 'target'}),
                E.p("Content2", {'class': 'new_p'}),
                moved_paragraph,
            )
        )

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_incorrect_move_1(self):
        # cannot move an inexisting element
        spec = E.xpath(
            E.xpath(expr="//p[@name='none']", position="move"),
            expr="//div[@class='target']", position="after")

        with self.assertRaises(ValueError):
            self.apply_spec(self.base_arch, spec)

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_incorrect_move_2(self):
        # move xpath cannot contain any children
        spec = E.xpath(
            E.xpath(E.p("Content2", {'class': 'new_p'}), expr="//p", position="move"),
            expr="//div[@class='target']", position="after")

        with self.assertRaises(ValueError):
            self.apply_spec(self.base_arch, spec)

    def test_incorrect_move_3(self):
        # move won't be correctly applied if not a direct child of an xpath
        spec = E.xpath(
            E.div(E.xpath(E.p("Content2", {'class': 'new_p'}), expr="//p", position="move"), {'class': 'wrapper'}),
            expr="//div[@class='target']", position="after")

        self.apply_spec(self.base_arch, spec)
        self.assertEqual(
            self.base_arch,
            E.template(
                E.div(E.p("Content", {'class': 'some'})),
                E.div({'class': 'target'}),
                E.div(E.xpath(E.p("Content2", {'class': 'new_p'}), expr="//p", position="move"), {'class': 'wrapper'}),
            )
        )


class TestNoModel(ViewCase):
    def test_create_view_nomodel(self):
        view = self.View.create({
            'name': 'dummy',
            'arch': '<template name="foo"/>',
            'inherit_id': False,
            'type': 'qweb',
        })
        fields = ['name', 'arch', 'type', 'priority', 'inherit_id', 'model']
        [data] = view.read(fields)
        self.assertEqual(data, {
            'id': view.id,
            'name': 'dummy',
            'arch': '<template name="foo"/>',
            'type': 'qweb',
            'priority': 16,
            'inherit_id': False,
            'model': False,
        })

    text_para = E.p("", {'class': 'legalese'})
    arch = E.body(
        E.div(
            E.h1("Title"),
            id="header"),
        E.p("Welcome!"),
        E.div(
            E.hr(),
            text_para,
            id="footer"),
        {'class': "index"},)

    def test_qweb_translation(self):
        """
        Test if translations work correctly without a model
        """
        self.env['res.lang']._activate_lang('fr_FR')
        ARCH = '<template name="foo">%s</template>'
        TEXT_EN = "Copyright copyrighter"
        TEXT_FR = u"Copyrighter, tous droits réservés"
        view = self.View.create({
            'name': 'dummy',
            'arch': ARCH % TEXT_EN,
            'inherit_id': False,
            'type': 'qweb',
        })
        view.update_field_translations('arch_db', {'fr_FR': {TEXT_EN: TEXT_FR}})
        view = view.with_context(lang='fr_FR')
        self.assertEqual(view.arch, ARCH % TEXT_FR)


class TestTemplating(ViewCase):
    def setUp(self):
        super(TestTemplating, self).setUp()
        self.patch(self.registry, '_init', False)

    def test_branding_t0(self):
        view1 = self.View.create({
            'name': "Base view",
            'type': 'qweb',
            'arch': """<root>
                <div role="search">
                    <input type="search" name="search"/>
                    <button type="submit">
                        <i class="oi-search"/>
                    </button>
                </div>
            </root>
            """
        })
        self.View.create({
            'name': "Extension view",
            'type': 'qweb',
            'inherit_id': view1.id,
            'arch': """<xpath expr="//div[@role='search']" position="replace">
                <form>
                    <t>$0</t>
                </form>
            </xpath>
            """
        })
        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()
        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)
        [initial] = arch.xpath("//div[@role='search']")
        self.assertEqual(
            '1',
            initial.get('data-oe-no-branding'),
            'Injected view must be marked as no-branding')

    def test_branding_inherit(self):
        view1 = self.View.create({
            'name': "Base view",
            'type': 'qweb',
            'arch': """<root>
                <item order="1"/>
            </root>
            """
        })
        view2 = self.View.create({
            'name': "Extension",
            'type': 'qweb',
            'inherit_id': view1.id,
            'arch': """<xpath expr="//item" position="before">
                <item order="2"/>
            </xpath>
            """
        })

        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()

        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        [initial] = arch.xpath('//item[@order=1]')
        self.assertEqual(
            str(view1.id),
            initial.get('data-oe-id'),
            "initial should come from the root view")
        self.assertEqual(
            '/root[1]/item[1]',
            initial.get('data-oe-xpath'),
            "initial's xpath should be within the root view only")

        [second] = arch.xpath('//item[@order=2]')
        self.assertEqual(
            str(view2.id),
            second.get('data-oe-id'),
            "second should come from the extension view")

    def test_branding_inherit_replace_node(self):
        view1 = self.View.create({
            'name': "Base view",
            'type': 'qweb',
            'arch': """<hello>
                <world></world>
                <world><t t-esc="hello"/></world>
                <world></world>
            </hello>
            """
        })
        self.View.create({
            'name': "Extension",
            'type': 'qweb',
            'inherit_id': view1.id,
            'arch': """<xpath expr="/hello/world[1]" position="replace">
                <world>Is a ghetto</world>
                <world>Wonder when I'll find paradise</world>
            </xpath>
            """
        })

        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()

        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        # First world - has been replaced by inheritance
        [initial] = arch.xpath('/hello[1]/world[1]')
        self.assertEqual(
            '/xpath/world[1]',
            initial.get('data-oe-xpath'),
            'Inherited nodes have correct xpath')

        # Second world added by inheritance
        [initial] = arch.xpath('/hello[1]/world[2]')
        self.assertEqual(
            '/xpath/world[2]',
            initial.get('data-oe-xpath'),
            'Inherited nodes have correct xpath')

        # Third world - is not editable
        [initial] = arch.xpath('/hello[1]/world[3]')
        self.assertFalse(
            initial.get('data-oe-xpath'),
            'node containing t-esc is not branded')

        # The most important assert
        # Fourth world - should have a correct oe-xpath, which is 3rd in main view
        [initial] = arch.xpath('/hello[1]/world[4]')
        self.assertEqual(
            '/hello[1]/world[3]',
            initial.get('data-oe-xpath'),
            "The node's xpath position should be correct")

    def test_branding_inherit_replace_node2(self):
        view1 = self.View.create({
            'name': "Base view",
            'type': 'qweb',
            'arch': """<hello>
                <world></world>
                <world><t t-esc="hello"/></world>
                <world></world>
            </hello>
            """
        })
        self.View.create({
            'name': "Extension",
            'type': 'qweb',
            'inherit_id': view1.id,
            'arch': """<xpath expr="/hello/world[1]" position="replace">
                <war>Is a ghetto</war>
                <world>Wonder when I'll find paradise</world>
            </xpath>
            """
        })

        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()

        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        [initial] = arch.xpath('/hello[1]/war[1]')
        self.assertEqual(
            '/xpath/war',
            initial.get('data-oe-xpath'),
            'Inherited nodes have correct xpath')

        # First world: from inheritance
        [initial] = arch.xpath('/hello[1]/world[1]')
        self.assertEqual(
            '/xpath/world',
            initial.get('data-oe-xpath'),
            'Inherited nodes have correct xpath')

        # Second world - is not editable
        [initial] = arch.xpath('/hello[1]/world[2]')
        self.assertFalse(
            initial.get('data-oe-xpath'),
            'node containing t-esc is not branded')

        # The most important assert
        # Third world - should have a correct oe-xpath, which is 3rd in main view
        [initial] = arch.xpath('/hello[1]/world[3]')
        self.assertEqual(
            '/hello[1]/world[3]',
            initial.get('data-oe-xpath'),
            "The node's xpath position should be correct")

    def test_branding_inherit_remove_node(self):
        view1 = self.View.create({
            'name': "Base view",
            'type': 'qweb',
            # The t-esc node is to ensure branding is distributed to both
            # <world/> elements from the start
            'arch': """
                <hello>
                    <world></world>
                    <world></world>

                    <t t-esc="foo"/>
                </hello>
            """
        })
        self.View.create({
            'name': "Extension",
            'type': 'qweb',
            'inherit_id': view1.id,
            'arch': """
                <data>
                    <xpath expr="/hello/world[1]" position="replace"/>
                </data>
            """
        })

        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()

        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        # Only remaining world but still the second in original view
        [initial] = arch.xpath('/hello[1]/world[1]')
        self.assertEqual(
            '/hello[1]/world[2]',
            initial.get('data-oe-xpath'),
            "The node's xpath position should be correct")

    def test_branding_inherit_remove_node2(self):
        view1 = self.View.create({
            'name': "Base view",
            'type': 'qweb',
            'arch': """
                <hello>
                    <world></world>
                    <world></world>
                </hello>
            """
        })
        self.View.create({
            'name': "Extension",
            'type': 'qweb',
            'inherit_id': view1.id,
            'arch': """
                <data>
                    <xpath expr="/hello/world[1]" position="replace"/>
                </data>
            """
        })

        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()

        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        # Note: this test is a variant of the test_branding_inherit_remove_node
        # -> in this case, we expect the branding to not be distributed on the
        # <hello/> element anymore but on the only remaining world.
        [initial] = arch.xpath('/hello[1]')
        self.assertIsNone(
            initial.get('data-oe-model'),
            "The inner content of the root was xpath'ed, it should not receive branding anymore")

        # Only remaining world but still the second in original view
        [initial] = arch.xpath('/hello[1]/world[1]')
        self.assertEqual(
            '/hello[1]/world[2]',
            initial.get('data-oe-xpath'),
            "The node's xpath position should be correct")

    def test_branding_inherit_multi_replace_node(self):
        view1 = self.View.create({
            'name': "Base view",
            'type': 'qweb',
            'arch': """
                <hello>
                    <world class="a"></world>
                    <world class="b"></world>
                    <world class="c"></world>
                </hello>
            """
        })
        view2 = self.View.create({
            'name': "Extension",
            'type': 'qweb',
            'inherit_id': view1.id,
            'arch': """
                <data>
                    <xpath expr="//world" position="replace">
                        <world class="new_a"></world>
                        <world class="z"></world>
                    </xpath>
                </data>
            """
        })
        self.View.create({  # Inherit from the child view and target the added element
            'name': "Extension",
            'type': 'qweb',
            'inherit_id': view2.id,
            'arch': """
                <data>
                    <xpath expr="//world[hasclass('new_a')]" position="replace">
                        <world class="another_new_a"></world>
                    </xpath>
                </data>
            """
        })

        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()
        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        # Check if the replacement inside the child view did not mess up the
        # branding of elements in that child view
        [initial] = arch.xpath('//world[hasclass("z")]')
        self.assertEqual(
            '/data/xpath/world[2]',
            initial.get('data-oe-xpath'),
            "The node's xpath position should be correct")

        # Check if the replacement of the first worlds did not mess up the
        # branding of the last world.
        [initial] = arch.xpath('//world[hasclass("c")]')
        self.assertEqual(
            '/hello[1]/world[3]',
            initial.get('data-oe-xpath'),
            "The node's xpath position should be correct")

    def test_branding_inherit_multi_replace_node2(self):
        view1 = self.View.create({
            'name': "Base view",
            'type': 'qweb',
            'arch': """
                <hello>
                    <world class="a"></world>
                    <world class="b"></world>
                    <world class="c"></world>
                </hello>
            """
        })
        self.View.create({
            'name': "Extension",
            'type': 'qweb',
            'inherit_id': view1.id,
            'arch': """
                <data>
                    <xpath expr="//world" position="replace">
                        <world class="new_a"></world>
                        <world class="z"></world>
                    </xpath>
                </data>
            """
        })
        self.View.create({  # Inherit from the parent view but actually target
                            # the element added by the first child view
            'name': "Extension",
            'type': 'qweb',
            'inherit_id': view1.id,
            'arch': """
                <data>
                    <xpath expr="//world" position="replace">
                        <world class="another_new_a"></world>
                    </xpath>
                </data>
            """
        })

        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()
        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        # Check if the replacement inside the child view did not mess up the
        # branding of elements in that child view
        [initial] = arch.xpath('//world[hasclass("z")]')
        self.assertEqual(
            '/data/xpath/world[2]',
            initial.get('data-oe-xpath'),
            "The node's xpath position should be correct")

        # Check if the replacement of the first worlds did not mess up the
        # branding of the last world.
        [initial] = arch.xpath('//world[hasclass("c")]')
        self.assertEqual(
            '/hello[1]/world[3]',
            initial.get('data-oe-xpath'),
            "The node's xpath position should be correct")

    def test_branding_inherit_remove_added_from_inheritance(self):
        view1 = self.View.create({
            'name': "Base view",
            'type': 'qweb',
            'arch': """
                <hello>
                    <world class="a"></world>
                    <world class="b"></world>
                </hello>
            """
        })
        view2 = self.View.create({
            'name': "Extension",
            'type': 'qweb',
            'inherit_id': view1.id,
            # Note: class="x" instead of t-field="x" in this arch, should lead
            # to the same result that this test is ensuring but was actually
            # a different case in old stable versions.
            'arch': """
                <data>
                    <xpath expr="//world[hasclass('a')]" position="after">
                        <world t-field="x"></world>
                        <world class="y"></world>
                    </xpath>
                </data>
            """
        })
        self.View.create({  # Inherit from the child view and target the added element
            'name': "Extension",
            'type': 'qweb',
            'inherit_id': view2.id,
            'arch': """
                <data>
                    <xpath expr="//world[@t-field='x']" position="replace"/>
                </data>
            """
        })

        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()
        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        # Check if the replacement inside the child view did not mess up the
        # branding of elements in that child view, should not be the case as
        # that root level branding is not distributed.
        [initial] = arch.xpath('//world[hasclass("y")]')
        self.assertEqual(
            '/data/xpath/world[2]',
            initial.get('data-oe-xpath'),
            "The node's xpath position should be correct")

        # Check if the child view replacement of added nodes did not mess up
        # the branding of last world in the parent view.
        [initial] = arch.xpath('//world[hasclass("b")]')
        self.assertEqual(
            '/hello[1]/world[2]',
            initial.get('data-oe-xpath'),
            "The node's xpath position should be correct")

    def test_branding_inherit_remove_node_processing_instruction(self):
        view1 = self.View.create({
            'name': "Base view",
            'type': 'qweb',
            'arch': """
                <html>
                    <head>
                        <hello></hello>
                    </head>
                    <body>
                        <world></world>
                    </body>
                </html>
            """
        })
        self.View.create({
            'name': "Extension",
            'type': 'qweb',
            'inherit_id': view1.id,
            'arch': """
                <data>
                    <xpath expr="//hello" position="replace"/>
                    <xpath expr="//world" position="replace"/>
                </data>
            """
        })

        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()
        arch = etree.fromstring(arch_string)

        head = arch.xpath('//head')[0]
        head_child = head[0]
        self.assertEqual(
            head_child.target,
            'apply-inheritance-specs-node-removal',
            "A node was removed at the start of the <head>, a processing instruction should exist as first child node")
        self.assertEqual(
            head_child.text,
            'hello',
            "The processing instruction should mention the tag of the node that was removed")

        body = arch.xpath('//body')[0]
        body_child = body[0]
        self.assertEqual(
            body_child.target,
            'apply-inheritance-specs-node-removal',
            "A node was removed at the start of the <body>, a processing instruction should exist as first child node")
        self.assertEqual(
            body_child.text,
            'world',
            "The processing instruction should mention the tag of the node that was removed")

        self.View.distribute_branding(arch)

        # Test that both head and body have their processing instruction
        # 'apply-inheritance-specs-node-removal' removed after branding
        # distribution. Note: test head and body separately as the code in
        # charge of the removal is different in each case.
        self.assertEqual(
            len(head),
            0,
            "The processing instruction of the <head> should have been removed")
        self.assertEqual(
            len(body),
            0,
            "The processing instruction of the <body> should have been removed")

    def test_branding_inherit_top_t_field(self):
        view1 = self.View.create({
            'name': "Base view",
            'type': 'qweb',
            'arch': """
                <hello>
                    <world></world>
                    <world t-field="a"/>
                    <world></world>
                    <world></world>
                </hello>
            """
        })
        self.View.create({
            'name': "Extension",
            'type': 'qweb',
            'inherit_id': view1.id,
            'arch': """
                <xpath expr="/hello/world[3]" position="after">
                    <world t-field="b"/>
                </xpath>
            """
        })
        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()
        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        # First t-field should have an indication of xpath
        [node] = arch.xpath('//*[@t-field="a"]')
        self.assertEqual(
            node.get('data-oe-xpath'),
            '/hello[1]/world[2]',
            'First t-field has indication of xpath')

        # Second t-field, from inheritance, should also have an indication of xpath
        [node] = arch.xpath('//*[@t-field="b"]')
        self.assertEqual(
            node.get('data-oe-xpath'),
            '/xpath/world',
            'Inherited t-field has indication of xpath')

        # The most important assert
        # The last world xpath should not have been impacted by the t-field from inheritance
        [node] = arch.xpath('//world[last()]')
        self.assertEqual(
            node.get('data-oe-xpath'),
            '/hello[1]/world[4]',
            "The node's xpath position should be correct")

        # Also test inherit via non-xpath t-field node, direct children of data,
        # is not impacted by the feature
        self.View.create({
            'name': "Extension",
            'type': 'qweb',
            'inherit_id': view1.id,
            'arch': """
                <data>
                    <world t-field="a" position="replace">
                        <world t-field="z"/>
                    </world>
                </data>
            """
        })
        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()
        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        node = arch.xpath('//world')[1]
        self.assertEqual(
            node.get('t-field'),
            'z',
            "The node has properly been replaced")

    def test_branding_primary_inherit(self):
        view1 = self.View.create({
            'name': "Base view",
            'type': 'qweb',
            'arch': """<root>
                <item order="1"/>
            </root>
            """
        })
        view2 = self.View.create({
            'name': "Extension",
            'type': 'qweb',
            'mode': 'primary',
            'inherit_id': view1.id,
            'arch': """<xpath expr="//item" position="after">
                <item order="2"/>
            </xpath>
            """
        })

        arch_string = view2.with_context(inherit_branding=True).get_combined_arch()

        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        [initial] = arch.xpath('//item[@order=1]')
        self.assertEqual(
            initial.get('data-oe-id'),
            str(view1.id),
            "initial should come from the root view")
        self.assertEqual(
            initial.get('data-oe-xpath'),
            '/root[1]/item[1]',
            "initial's xpath should be within the inherited view only")

        [second] = arch.xpath('//item[@order=2]')
        self.assertEqual(
            second.get('data-oe-id'),
            str(view2.id),
            "second should come from the extension view")
        self.assertEqual(
            second.get('data-oe-xpath'),
            '/xpath/item',
            "second xpath should be on the inheriting view only")

    def test_branding_distribute_inner(self):
        """ Checks that the branding is correctly distributed within a view
        extension
        """
        view1 = self.View.create({
            'name': "Base view",
            'type': 'qweb',
            'arch': """<root>
                <item order="1"/>
            </root>"""
        })
        view2 = self.View.create({
            'name': "Extension",
            'type': 'qweb',
            'inherit_id': view1.id,
            'arch': """<xpath expr="//item" position="before">
                <item order="2">
                    <content t-att-href="foo">bar</content>
                </item>
            </xpath>"""
        })

        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()

        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        self.assertEqual(
            arch,
            E.root(
                E.item(
                    E.content("bar", {
                        't-att-href': "foo",
                        'data-oe-model': 'ir.ui.view',
                        'data-oe-id': str(view2.id),
                        'data-oe-field': 'arch',
                        'data-oe-xpath': '/xpath/item/content[1]',
                    }), {
                        'order': '2',
                    }),
                E.item({
                    'order': '1',
                    'data-oe-model': 'ir.ui.view',
                    'data-oe-id': str(view1.id),
                    'data-oe-field': 'arch',
                    'data-oe-xpath': '/root[1]/item[1]',
                })
            )
        )

    def test_branding_attribute_groups(self):
        view = self.View.create({
            'name': "Base View",
            'type': 'qweb',
            'arch': """<root>
                <item groups="base.group_no_one"/>
            </root>""",
        })

        arch_string = view.with_context(inherit_branding=True).get_combined_arch()
        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        self.assertEqual(arch, E.root(E.item({
            'groups': 'base.group_no_one',
            'data-oe-model': 'ir.ui.view',
            'data-oe-id': str(view.id),
            'data-oe-field': 'arch',
            'data-oe-xpath': '/root[1]/item[1]',
        })))

    def test_call_no_branding(self):
        view = self.View.create({
            'name': "Base View",
            'type': 'qweb',
            'arch': """<root>
                <item><span><t t-call="foo"/></span></item>
            </root>""",
        })

        arch_string = view.with_context(inherit_branding=True).get_combined_arch()
        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        self.assertEqual(arch, E.root(E.item(E.span(E.t({'t-call': "foo"})))))

    def test_esc_no_branding(self):
        view = self.View.create({
            'name': "Base View",
            'type': 'qweb',
            'arch': """<root>
                <item><span t-esc="foo"/></item>
            </root>""",
        })

        arch_string = view.with_context(inherit_branding=True).get_combined_arch()
        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        self.assertEqual(arch, E.root(E.item(E.span({'t-esc': "foo"}))))

    def test_ignore_unbrand(self):
        view1 = self.View.create({
            'name': "Base view",
            'type': 'qweb',
            'arch': """<root>
                <item order="1" t-ignore="true">
                    <t t-esc="foo"/>
                </item>
            </root>"""
        })
        view2 = self.View.create({
            'name': "Extension",
            'type': 'qweb',
            'inherit_id': view1.id,
            'arch': """<xpath expr="//item[@order='1']" position="inside">
                <item order="2">
                    <content t-att-href="foo">bar</content>
                </item>
            </xpath>"""
        })

        arch_string = view1.with_context(inherit_branding=True).get_combined_arch()

        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        self.assertEqual(
            arch,
            E.root(
                E.item(
                    {'t-ignore': 'true', 'order': '1'},
                    E.t({'t-esc': 'foo'}),
                    E.item(
                        {'order': '2'},
                        E.content(
                            {'t-att-href': 'foo'},
                            "bar")
                    )
                )
            ),
            "t-ignore should apply to injected sub-view branding, not just to"
            " the main view's"
        )

    def test_branding_remove_add_text(self):
        view1 = self.View.create({
            'name': "Base view",
            'type': 'qweb',
            'arch': """<root>
                <item order="1">
                    <item/>
                </item>
            </root>""",
        })
        view2 = self.View.create({
            'name': "Extension",
            'type': 'qweb',
            'inherit_id': view1.id,
            'arch': """
            <data>
                <xpath expr="/root/item/item" position="replace" />
                <xpath expr="/root/item" position="inside">A<div/>B</xpath>
            </data>
            """
        })

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


@tagged('post_install', '-at_install')
class TestViews(ViewCase):

    def test_nonexistent_attribute_removal(self):
        self.View.create({
            'name': 'Test View',
            'model': 'ir.ui.view',
            'inherit_id': self.ref('base.view_view_tree'),
            'arch': """<?xml version="1.0"?>
                        <xpath expr="//field[@name='name']" position="attributes">
                            <attribute name="non_existing_attribute"></attribute>
                        </xpath>
                    """,
        })

    def _insert_view(self, **kw):
        """Insert view into database via a query to passtrough validation"""
        kw.pop('id', None)
        kw.setdefault('mode', 'extension' if kw.get('inherit_id') else 'primary')
        kw.setdefault('active', True)
        if 'arch_db' in kw:
            arch_db = kw['arch_db']
            if kw.get('inherit_id'):
                self.cr.execute('SELECT type FROM ir_ui_view WHERE id = %s', [kw['inherit_id']])
                kw['type'] = self.cr.fetchone()[0]
            else:
                kw['type'] = etree.fromstring(arch_db).tag
            kw['arch_db'] = Json({'en_US': arch_db}) if self.env.lang in (None, 'en_US') else Json({'en_US': arch_db, self.env.lang: arch_db})

        keys = sorted(kw)
        fields = ','.join('"%s"' % (k.replace('"', r'\"'),) for k in keys)
        params = ','.join('%%(%s)s' % (k,) for k in keys)

        query = 'INSERT INTO ir_ui_view(%s) VALUES(%s) RETURNING id' % (fields, params)
        self.cr.execute(query, kw)
        return self.cr.fetchone()[0]

    def test_view_root_node_matches_view_type(self):
        view = self.View.create({
            'name': 'foo',
            'model': 'ir.ui.view',
            'arch': """
                <form>
                </form>
            """,
        })
        self.assertEqual(view.type, 'form')

        with self.assertRaises(ValidationError):
            self.View.create({
                'name': 'foo',
                'model': 'ir.ui.view',
                'type': 'form',
                'arch': """
                    <data>
                        <div>
                        </div>
                        <form>
                        </form>
                    </data>
                """,
            })

    def test_custom_view_validation(self):
        model = 'ir.actions.act_url'
        validate = partial(self.View._validate_custom_views, model)

        # validation of a single view
        vid = self._insert_view(
            name='base view',
            model=model,
            priority=1,
            arch_db="""<?xml version="1.0"?>
                        <list string="view">
                          <field name="url"/>
                        </list>
                    """,
        )
        self.assertTrue(validate())     # single view

        # validation of a inherited view
        self._insert_view(
            name='inherited view',
            model=model,
            priority=1,
            inherit_id=vid,
            arch_db="""<?xml version="1.0"?>
                        <xpath expr="//field[@name='url']" position="before">
                          <field name="name"/>
                        </xpath>
                    """,
        )
        self.assertTrue(validate())     # inherited view

        # validation of a second inherited view (depending on 1st)
        self._insert_view(
            name='inherited view 2',
            model=model,
            priority=5,
            inherit_id=vid,
            arch_db="""<?xml version="1.0"?>
                        <xpath expr="//field[@name='name']" position="after">
                          <field name="target"/>
                        </xpath>
                    """,
        )
        self.assertTrue(validate())     # inherited view

    def test_view_inheritance(self):
        view1 = self.View.create({
            'name': "bob",
            'model': 'ir.ui.view',
            'arch': """
                <form string="Base title">
                    <separator name="separator" string="Separator" colspan="4"/>
                    <footer>
                        <button name="action_archive" type="object" string="Next button" class="btn-primary"/>
                        <button string="Skip" special="cancel" class="btn-secondary"/>
                    </footer>
                </form>
            """
        })
        view2 = self.View.create({
            'name': "edmund",
            'model': 'ir.ui.view',
            'inherit_id': view1.id,
            'arch': """
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
            """
        })
        view3 = self.View.create({
            'name': 'jake',
            'model': 'ir.ui.view',
            'inherit_id': view1.id,
            'priority': 17,
            'arch': """
                <footer position="attributes">
                    <attribute name="thing">bob tata lolo</attribute>
                    <attribute name="thing" add="bibi and co" remove="tata" separator=" " />
                    <attribute name="otherthing">bob, tata,lolo</attribute>
                    <attribute name="otherthing" remove="tata, bob"/>
                </footer>
            """
        })

        view = self.View.with_context(check_view_ids=[view2.id, view3.id]).get_view(view2.id, 'form')
        self.assertEqual(
            etree.fromstring(
                view['arch'],
                parser=etree.XMLParser(remove_blank_text=True)
            ),
            E.form(
                E.p("Replacement data"),
                E.footer(
                    E.button(name="action_archive", type="object", string="New button"),
                    thing="bob lolo bibi and co", otherthing="lolo"
                ),
                string="Replacement title"))

    def test_view_inheritance_text_inside(self):
        """ Test view inheritance when adding elements and text. """
        view1 = self.View.create({
            'name': "alpha",
            'model': 'ir.ui.view',
            'arch': '<form string="F">(<div/>)</form>',
        })
        view2 = self.View.create({
            'name': "beta",
            'model': 'ir.ui.view',
            'inherit_id': view1.id,
            'arch': '<div position="inside">a<p/>b<p/>c</div>',
        })
        view = self.View.with_context(check_view_ids=view2.ids).get_view(view1.id)
        self.assertEqual(
            view['arch'],
            '<form string="F">(<div>a<p/>b<p/>c</div>)</form>',
        )

    def test_view_inheritance_text_after(self):
        """ Test view inheritance when adding elements and text. """
        view1 = self.View.create({
            'name': "alpha",
            'model': 'ir.ui.view',
            'arch': '<form string="F">(<div/>)</form>',
        })
        view2 = self.View.create({
            'name': "beta",
            'model': 'ir.ui.view',
            'inherit_id': view1.id,
            'arch': '<div position="after">a<p/>b<p/>c</div>',
        })
        view = self.View.with_context(check_view_ids=view2.ids).get_view(view1.id)
        self.assertEqual(
            view['arch'],
            '<form string="F">(<div/>a<p/>b<p/>c)</form>',
        )

    def test_view_inheritance_text_before(self):
        """ Test view inheritance when adding elements and text. """
        view1 = self.View.create({
            'name': "alpha",
            'model': 'ir.ui.view',
            'arch': '<form string="F">(<div/>)</form>',
        })
        view2 = self.View.create({
            'name': "beta",
            'model': 'ir.ui.view',
            'inherit_id': view1.id,
            'arch': '<div position="before">a<p/>b<p/>c</div>',
        })
        view = self.View.with_context(check_view_ids=view2.ids).get_view(view1.id)
        self.assertEqual(
            view['arch'],
            '<form string="F">(a<p/>b<p/>c<div/>)</form>',
        )

    def test_view_inheritance_divergent_models(self):
        view1 = self.View.create({
            'name': "bob",
            'model': 'ir.ui.view.custom',
            'arch': """
                <form string="Base title">
                    <separator name="separator" string="Separator" colspan="4"/>
                    <footer>
                        <button name="action_archive" type="object" string="Next button" class="btn-primary"/>
                        <button string="Skip" special="cancel" class="btn-secondary"/>
                    </footer>
                </form>
            """
        })
        view2 = self.View.create({
            'name': "edmund",
            'model': 'ir.ui.view',
            'inherit_id': view1.id,
            'arch': """
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
            """
        })
        view3 = self.View.create({
            'name': 'jake',
            'model': 'ir.ui.menu',
            'inherit_id': view1.id,
            'priority': 17,
            'arch': """
                <footer position="attributes">
                    <attribute name="thing">bob</attribute>
                </footer>
            """
        })

        view = self.View.with_context(check_view_ids=[view2.id, view3.id]) \
                        .get_view(view2.id, view_type='form')
        self.assertEqual(
            etree.fromstring(
                view['arch'],
                parser=etree.XMLParser(remove_blank_text=True)
            ),
            E.form(
                E.p("Replacement data"),
                E.footer(
                    E.button(name="action_unarchive", type="object", string="New button")),
                string="Replacement title"
            ))

    def test_invalid_field(self):
        self.assertInvalid("""
                <form string="View">
                    <field name="name"/>
                    <field name="not_a_field"/>
                </form>
            """, 'Field "not_a_field" does not exist in model "ir.ui.view"')
        self.assertInvalid("""
                <form string="View">
                    <field/>
                </form>
            """, 'Field tag must have a "name" attribute defined')

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

    def test_invalid_type(self):
        """Ensure invalid root tag infers an invalid type and raises ValidationError"""
        with self.assertRaises(ValidationError):
            self.View.create({
                'name': 'invalid_view',
                'arch': '<template></template>',
                'inherit_id': False,
            })

    def test_attribute_node_with_no_name(self):
        """Ensure that an attribute node with no name raises ValidationError"""
        with self.assertRaises(ValidationError):
            self.View.create({
                'name': 'also_invalid_view',
                'type': 'list',
                'arch': '<attribute></attribute>',
                'inherit_id': False,
            })

    def test_xml_editor_rejects_encoding_declaration(self):
        """Must raise a UserError when encoding declaration is included."""
        with self.assertRaises(UserError):
            self.View.create({
                'name': 'encoding_declaration_view',
                'arch_base': "<?xml version='1.0' encoding='utf-8'?>",
                'inherit_id': False,
            })

        view = self.assertValid("<form string='Test'></form>", name="test_xml_encoding_view")
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
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertFalse(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))

        view = self.assertValid(arch % '')
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))

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
        view = self.assertValid(arch % ('', '<field name="model"/>'))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertFalse(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))

        view = self.assertValid(arch % ('', ''))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//field/form/field[@name="model"][@invisible][@readonly]'))

        view = self.assertValid(arch % ('<field name="model"/>', ''))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//field/form/field[@name="model"][@invisible][@readonly]'))

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

        view = self.assertValid(arch % ('<field name="model"/>', ''))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertFalse(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))

        view = self.assertValid(arch % ('', ''))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))
        self.assertFalse(etree.fromstring(view_arch).xpath('//field/form/field[@name="model"][@invisible][@readonly]'))

        view = self.assertValid(arch % ('', '<field name="model"/>'))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))
        self.assertFalse(etree.fromstring(view_arch).xpath('//field/form/field[@name="model"][@invisible][@readonly]'))

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

        view = self.assertValid(arch % ('<field name="model"/>', '', ''))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertFalse(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))

        view = self.assertValid(arch % ('', '', ''))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))
        self.assertFalse(etree.fromstring(view_arch).xpath('//field//field[@name="model"][@invisible][@readonly]'))

        view = self.assertValid(arch % ('', '<field name="model"/>', ''))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))
        self.assertFalse(etree.fromstring(view_arch).xpath('//field//field[@name="model"][@invisible][@readonly]'))

        view = self.assertValid(arch % ('', '', '<field name="model"/>'))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))
        self.assertFalse(etree.fromstring(view_arch).xpath('//field//field[@name="model"][@invisible][@readonly]'))

    def test_domain_id_case(self):
        # id is read by default and should be usable in domains
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
        self.assertValid(arch % ('', '1', '1'))
        self.assertValid(arch % ('', '0', '1'))
        # self.assertInvalid(arch % ('', '1', '0'))
        self.assertValid(arch % ('<field name="name"/>', '1', '0 if name else 1'))
        self.assertInvalid(arch % ('<field name="name"/><field name="type"/>', "'tata' if name else 'tutu'", 'type'), 'Wrong domain formatting')
        view = self.assertValid(arch % ('', '1', '0 if name else 1'))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//field[@name="name"][@invisible][@readonly]'))

    def test_domain_in_view(self):
        arch = """
            <form string="View">
                <field name="name"/>%s
                <field name="inherit_id" domain="[('model', '=', model)]"/>
            </form>
        """
        view = self.assertValid(arch % '<field name="model"/>')
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertFalse(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))

        view = self.assertValid(arch % '')
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))

    def test_domain_unknown_field(self):
        self.assertInvalid("""
                <form string="View">
                    <field name="name"/>
                    <field name="inherit_id" domain="[('invalid_field', '=', 'res.users')]"/>
                </form>
            """,
            '''Unknown field "ir.ui.view.invalid_field" in domain of <field name="inherit_id"> ([('invalid_field', '=', 'res.users')])''',
        )

    def test_domain_field_searchable(self):
        arch = """
            <form string="View">
                <field name="name"/>
                <field name="inherit_id" domain="[('%s', '=', 'test')]"/>
            </form>
        """
        # computed field with a search method
        self.assertValid(arch % 'model_data_id')
        # computed field, not stored, no search
        self.assertInvalid(
            arch % 'xml_id',
            '''Unsearchable field “xml_id” in path “xml_id” in domain of <field name="inherit_id"> ([('xml_id', '=', 'test')])''',
        )

    def test_domain_field_no_comodel(self):
        self.assertInvalid("""
            <form string="View">
                <field name="name" domain="[('test', '=', 'test')]"/>
            </form>
        """, "Domain on non-relational field \"name\" makes no sense (domain:[('test', '=', 'test')])")

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
        self.assertValid(arch % ('', '<field name="model"/>'))

        view = self.assertValid(arch % ('', ''))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//field/form/field[@name="model"][@invisible][@readonly]'))

        view = self.assertValid(arch % ('<field name="model"/>', ''))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//field/form/field[@name="model"][@invisible][@readonly]'))

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
        view = self.assertValid(arch % ('<field name="model"/>', '', ''))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertFalse(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))

        view = self.assertValid(arch % ('', '', '<field name="model"/>'))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertFalse(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))

        view = self.assertValid(arch % ('', '', ''))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))

        view = self.assertValid(arch % ('', '<field name="model"/>', ''))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))

    def test_domain_on_field_in_view(self):
        field = self.env['ir.ui.view']._fields['inherit_id']
        self.patch(field, 'domain', "[('model', '=', model)]")

        arch = """
            <form string="View">
                <field name="name"/>%s
                <field name="inherit_id"/>
            </form>
        """
        view = self.assertValid(arch % '<field name="model"/>')
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertFalse(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))

        view = self.assertValid(arch % '')
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))

    def test_domain_on_field_in_subview(self):
        field = self.env['ir.ui.view']._fields['inherit_id']
        self.patch(field, 'domain', "[('model', '=', model)]")

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
        view = self.assertValid(arch % ('', '<field name="model"/>'))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertFalse(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))

        view = self.assertValid(arch % ('', ''))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//field/form/field[@name="model"][@invisible][@readonly]'))

    def test_domain_on_field_in_subview_with_parent(self):
        field = self.env['ir.ui.view']._fields['inherit_id']
        self.patch(field, 'domain', "[('model', '=', parent.model)]")

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
        view = self.assertValid(arch % ('<field name="model"/>', ''))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertFalse(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))

        view = self.assertValid(arch % ('', ''))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))
        self.assertFalse(etree.fromstring(view_arch).xpath('//field/form/field[@name="model"][@invisible][@readonly]'))

        view = self.assertValid(arch % ('', '<field name="model"/>'))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))
        self.assertFalse(etree.fromstring(view_arch).xpath('//field/form/field[@name="model"][@invisible][@readonly]'))

    def test_domain_on_field_in_noneditable_subview(self):
        field = self.env['ir.ui.view']._fields['inherit_id']
        self.patch(field, 'domain', "[('model', '=', model)]")

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
        view = self.assertValid(arch % '')
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertFalse(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))

        view = self.assertValid(arch % ' editable="bottom"')
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//field/list/field[@name="model"][@column_invisible][@readonly]'))

    def test_domain_on_readonly_field_in_view(self):
        field = self.env['ir.ui.view']._fields['inherit_id']
        self.patch(field, 'domain', "[('model', '=', model)]")

        arch = """
            <form string="View">
                <field name="name"/>
                <field name="inherit_id" readonly="1"/>
            </form>
        """
        self.assertValid(arch)

        self.patch(field, 'readonly', True)
        arch = """
            <form string="View">
                <field name="name"/>
                <field name="inherit_id"/>
            </form>
        """
        self.assertValid(arch)

    def test_domain_on_readonly_field_in_subview(self):
        field = self.env['ir.ui.view']._fields['inherit_id']
        self.patch(field, 'domain', "[('model', '=', model)]")

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
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertFalse(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))

        view = self.assertValid(arch % '')
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//field/form/field[@name="model"][@invisible][@readonly]'))

    def test_domain_in_filter(self):
        arch = """
            <search string="Search">
                <field name="%s"/>
                <filter string="Dummy" name="draft" domain="[('%s', '=', 'dummy')]"/>
            </search>
        """
        self.assertValid(arch % ('name', 'name'))
        self.assertValid(arch % ('name', 'inherit_children_ids.name'))
        self.assertInvalid(
            arch % ('invalid_field', 'name'),
            'Field "invalid_field" does not exist in model "ir.ui.view"',
        )
        self.assertInvalid(
            arch % ('name', 'invalid_field'),
            """Unknown field "ir.ui.view.invalid_field" in domain of <filter name="draft"> ([('invalid_field', '=', 'dummy')])""",
        )
        self.assertInvalid(
            arch % ('name', 'inherit_children_ids.invalid_field'),
            """Unknown field "ir.ui.view.invalid_field" in domain of <filter name="draft"> ([('inherit_children_ids.invalid_field', '=', 'dummy')])""",
        )
        # todo add check for non searchable fields and group by

    def test_group_by_in_filter(self):
        arch = """
            <search string="Search">
                <filter string="Date" name="month" domain="[]" context="{'group_by':'%s'}"/>
            </search>
        """
        self.assertValid(arch % 'name')
        self.assertInvalid(
            arch % 'invalid_field',
            """Unknown field “invalid_field” in "group_by" value in context=“{'group_by':'invalid_field'}”""",
        )

    def test_domain_invalid_in_filter(self):
        # invalid domain: it should be a list of tuples
        self.assertInvalid(
            """ <search string="Search">
                    <filter string="Dummy" name="draft" domain="['name', '=', 'dummy']"/>
                </search>
            """,
            '''Invalid domain of <filter name="draft">: “['name', '=', 'dummy']”''',
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
        view = self.assertValid(arch % ('', '<field name="inherit_id"/>', 'view_access', 'inherit_id'))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertFalse(etree.fromstring(view_arch).xpath('//field[@name="inherit_id"][@invisible][@readonly]'))
        self.assertFalse(etree.fromstring(view_arch).xpath('//field[@name="view_access"][@invisible][@readonly]'))

        view = self.assertValid(arch % ('<field name="inherit_id"/>', '', 'view_access', 'inherit_id'))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//searchpanel/field[@name="inherit_id"][@invisible][@readonly]'))

        view = self.assertValid(arch % ('', '<field name="inherit_id"/>', 'view_access', 'parent.arch_updated'))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertFalse(etree.fromstring(view_arch).xpath('//field[@name="view_access"][@invisible][@readonly]'))

        self.assertInvalid(
            arch % ('', '<field name="inherit_id"/>', 'view_access', 'view_access'),
            """field “view_access” does not exist in model “ir.ui.view”.""",
        )
        self.assertInvalid(
            arch % ('', '<field name="inherit_id"/>', 'inherit_id', 'inherit_id'),
            """Unknown field "res.groups.inherit_id" in domain of <field name="group_ids"> ([('inherit_id', '=', inherit_id)])""",
        )
        self.assertInvalid(
            arch % ('', '<field name="inherit_id" select="multi"/>', 'view_access', 'inherit_id'),
            """Field “inherit_id” used in domain of <field name="group_ids"> ([('view_access', '=', inherit_id)]) is present in view but is in select multi.""",
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
        self.assertValid(arch % 'base.group_no_one')
        self.assertWarning(arch % 'base.dummy')

    def test_groups_field_removed(self):
        view = self.View.create({
            'name': 'valid view',
            'model': 'ir.ui.view',
            'arch': """
                <form string="View">
                    <span class="oe_inline" invisible="0 == 0">
                        (<field name="name" groups="base.group_portal"/>)
                    </span>
                </form>
            """,
        })
        arch = self.View.get_views([(view.id, view.type)])['views']['form']['arch']

        self.assertEqual(arch, """
                <form string="View">
                    <span class="oe_inline" invisible="0 == 0">
                        ()
                    </span>
                </form>
            """.strip())

    def test_attrs_groups_behavior(self):
        view = self.View.create({
            'name': 'foo',
            'model': 'res.partner',
            'arch': """
                <form>
                    <field name="name"/>
                    <field name="company_id" groups="base.group_system"/>
                    <div id="foo"/>
                    <div id="bar" groups="base.group_system"/>
                </form>
            """,
        })
        user_demo = self.user_demo
        # Make sure demo doesn't have the base.group_system
        self.assertFalse(user_demo.has_group('base.group_system'))
        arch = self.env['res.partner'].with_user(user_demo).get_view(view_id=view.id)['arch']
        tree = etree.fromstring(arch)
        self.assertTrue(tree.xpath('//field[@name="name"]'))
        self.assertFalse(tree.xpath('//field[@name="company_id"]'))
        self.assertTrue(tree.xpath('//div[@id="foo"]'))
        self.assertFalse(tree.xpath('//div[@id="bar"]'))

        user_admin = self.env.ref('base.user_admin')
        # Make sure admin has the base.group_system
        self.assertTrue(user_admin.has_group('base.group_system'))
        arch = self.env['res.partner'].with_user(user_admin).get_view(view_id=view.id)['arch']
        tree = etree.fromstring(arch)
        self.assertTrue(tree.xpath('//field[@name="name"]'))
        self.assertTrue(tree.xpath('//field[@name="company_id"]'))
        self.assertTrue(tree.xpath('//div[@id="foo"]'))
        self.assertTrue(tree.xpath('//div[@id="bar"]'))

    def test_attrs_groups_validation(self):
        def validate(arch, valid=False, parent=False, field='name', model='ir.ui.view'):
            parent = 'parent.' if parent else ''
            if valid:
                self.assertValid(arch % {'attrs': f"""invisible="{parent}{field} == 'foo'" """}, model=model)
                self.assertValid(arch % {'attrs': f"""domain="[('name', '!=', {parent}{field})]" """}, model=model)
                self.assertValid(arch % {'attrs': f"""context="{{'default_name': {parent}{field}}}" """}, model=model)
                self.assertValid(arch % {'attrs': f"""decoration-info="{parent}{field} == 'foo'" """}, model=model)
            else:
                self.assertInvalid(
                    arch % {'attrs': f"""invisible="{parent}{field} == 'foo'" """},
                    f"""Field '{field}' used in modifier 'invisible' ({parent}{field} == 'foo') is restricted to the group(s)""",
                    model=model,
                )
                target = 'inherit_id' if model == 'ir.ui.view' else 'company_id'
                self.assertInvalid(
                    arch % {'attrs': f"""domain="[('name', '!=', {parent}{field})]" """},
                    f"""Field '{field}' used in domain of <field name="{target}"> ([('name', '!=', {parent}{field})]) is restricted to the group(s)""",
                    model=model,
                )
                self.assertInvalid(
                    arch % {'attrs': f"""context="{{'default_name': {parent}{field}}}" """},
                    f"""Field '{field}' used in context ({{'default_name': {parent}{field}}}) is restricted to the group(s)""",
                    model=model,
                )
                self.assertInvalid(
                    arch % {'attrs': f"""decoration-info="{parent}{field} == 'foo'" """},
                    f"""Field '{field}' used in decoration-info="{parent}{field} == 'foo'" is restricted to the group(s)""",
                    model=model,
                )

        # Assert using a parent field restricted to a group
        # in a child field with the same group is valid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="inherit_children_ids">
                    <list editable="bottom">
                        <field name="inherit_id" groups="base.group_system" %(attrs)s/>
                    </list>
                </field>
            </form>
        """, valid=True, parent=True)

        # Assert using a parent field available for everyone
        # in a child field restricted to a group is valid
        validate("""
            <form string="View">
                <field name="name"/>
                <field name="inherit_children_ids">
                    <list editable="bottom">
                        <field name="inherit_id" groups="base.group_system" %(attrs)s/>
                    </list>
                </field>
            </form>
        """, valid=True, parent=True)

        # Assert using a field available for everyone
        # in another field restricted to a group is valid
        validate("""
            <form string="View">
                <field name="name"/>
                <field name="inherit_id" %(attrs)s groups="base.group_system"/>
            </form>
        """, valid=True)

        # Assert using a field restricted to a group
        # in another field with the same group is valid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="inherit_id" groups="base.group_system" %(attrs)s/>
            </form>
        """, valid=True)

        # Assert using a field available twice for 2 diffent groups
        # in another field restricted to one of the 2 groups is valid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_portal"/>
                <field name="name" groups="base.group_system"/>
                <field name="inherit_id" groups="base.group_system" %(attrs)s/>
            </form>
        """, valid=True)

        # Assert using a field available twice for 2 different groups
        # in other fields restricted to the same 2 group is valid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="name" groups="base.group_portal"/>
                <field name="inherit_id" groups="base.group_system" %(attrs)s/>
                <field name="inherit_id" groups="base.group_portal" %(attrs)s/>
            </form>
        """, valid=True)

        # Assert using a field available for 2 diffent groups,
        # in another field restricted to one of the 2 groups is valid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_portal,base.group_system"/>
                <field name="inherit_id" groups="base.group_system" %(attrs)s/>
            </form>
        """, valid=True)

        # Assert using a field restricted to a group
        # in another field restricted to a group including the group for which the field is available is valid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_erp_manager"/>
                <field name="inherit_id" groups="base.group_system" %(attrs)s/>
            </form>
        """, valid=True)

        # Assert using a parent field restricted to a group
        # in a child field restricted to a group including the group for which the field is available is valid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_erp_manager"/>
                <field name="inherit_children_ids">
                    <list editable="bottom">
                        <field name="inherit_id" groups="base.group_system" %(attrs)s/>
                    </list>
                </field>
            </form>
        """, valid=True, parent=True)

        # Assert using a field within a block restricted to a group
        # in another field within the same block restricted to a group is valid
        validate("""
            <form string="View">
                <group groups="base.group_system">
                    <field name="name"/>
                    <field name="inherit_id" %(attrs)s/>
                </group>
            </form>
        """, valid=True)

        # Assert using a field within a block restricted to a group
        # in another field within the same block restricted to a group and additional groups on the field node is valid
        validate("""
            <form string="View">
                <group groups="base.group_system">
                    <field name="name"/>
                    <field name="inherit_id" %(attrs)s groups="base.group_multi_currency,base.group_multi_company"/>
                </group>
            </form>
        """, valid=True)

        # Assert using a field within a block restricted to a group
        # in another field within a block restricted to the same group is valid
        validate("""
            <form string="View">
                <group groups="base.group_system">
                    <field name="name"/>
                </group>
                <group groups="base.group_system">
                    <field name="inherit_id" %(attrs)s/>
                </group>
            </form>
        """, valid=True)

        # Assert using a field within a block restricted to a group
        # in another field within a block restricted to a group including the group for which the field is available
        # is valid
        validate("""
            <form string="View">
                <group groups="base.group_erp_manager">
                    <field name="name"/>
                </group>
                <group groups="base.group_system">
                    <field name="inherit_id" %(attrs)s/>
                </group>
            </form>
        """, valid=True)

        # Assert using a parent field restricted to a group
        # in a child field under a relational field restricted to the same group is valid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="inherit_children_ids" groups="base.group_system">
                    <list editable="bottom">
                        <field name="inherit_id" %(attrs)s/>
                    </list>
                </field>
            </form>
        """, valid=True, parent=True)

        # Assert using a parent field restricted to a group
        # in a child field under a relational field restricted
        # to a group including the group for which the field is available is valid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_erp_manager"/>
                <field name="inherit_children_ids" groups="base.group_system">
                    <list editable="bottom">
                        <field name="inherit_id" %(attrs)s/>
                    </list>
                </field>
            </form>
        """, valid=True, parent=True)

        # Assert using a field not restricted to any group
        # in another field restricted to users not having a group is valid
        validate("""
            <form string="View">
                <field name="name"/>
                <field name="inherit_id" groups="!base.group_system" %(attrs)s/>
            </form>
        """, valid=True)

        # Assert using a field restricted to users not having a group
        # in another field restricted to users not having multiple group including the one above is valid
        # e.g.
        # if the user is portal, the field "name" will be in the view
        # but the field "inherit_id" where "name" is used will not be in the view
        # making it valid.
        validate("""
            <form string="View">
                <field name="name" groups="!base.group_user"/>
                <field name="inherit_id" groups="!base.group_user,!base.group_portal" %(attrs)s/>
            </form>
        """, valid=True)

        # Assert using a field restricted to a non group
        # in another field restricted to a non group implied in the non group of the available field is valid
        # e.g.
        # if the user is employee, the field "name" will be in the view
        # but the field "inherit_id", where "name" is used, will not be in the view,
        # therefore making it valid
        validate("""
            <form string="View">
                <field name="name" groups="!base.group_system"/>
                <field name="inherit_id" groups="!base.group_user" %(attrs)s/>
            </form>
        """, valid=True)

        # Assert having two times the same field with a mutually exclusive group
        # and using that field in another field without any group is valid
        validate("""
            <form string="View">
                <field name="name" groups="!base.group_system"/>
                <field name="name" groups="base.group_system"/>
                <field name="inherit_id" %(attrs)s/>
            </form>
        """, valid=True)

        # Assert having two times the same field with a mutually exclusive group
        # and using that field in another field using the group is valid
        validate("""
            <form string="View">
                <field name="name" groups="!base.group_system"/>
                <field name="name" groups="base.group_system"/>
                <field name="inherit_id" groups="base.group_system" %(attrs)s/>
            </form>
        """, valid=True)

        # Assert having two times the same field with a mutually exclusive group
        # and using that field in another field using the !group is valid
        validate("""
            <form string="View">
                <field name="name" groups="!base.group_system"/>
                <field name="name" groups="base.group_system"/>
                <field name="inherit_id" groups="!base.group_system" %(attrs)s/>
            </form>
        """, valid=True)

        # Assert having two times the same field with a mutually exclusive group
        # and using that field in another field restricted to any other group is valid
        validate("""
            <form string="View">
                <field name="name" groups="!base.group_system"/>
                <field name="name" groups="base.group_system"/>
                <field name="inherit_id" groups="base.group_portal" %(attrs)s/>
            </form>
        """, valid=True)

        # The modifier node should have the same group 'base.group_user'
        # (or a depending group '') that the used field 'access_token'
        validate("""
            <form string="View attachment">
                <field name="access_token"/>
                <field name="company_id" %(attrs)s groups="base.group_user"/>
            </form>
        """, model='ir.attachment', field='access_token', valid=True)
        validate("""
            <form string="View attachment">
                <field name="company_id" %(attrs)s groups="base.group_user"/>
            </form>
        """, model='ir.attachment', field='access_token', valid=True)
        validate("""
            <form string="View attachment">
                <field name="company_id" %(attrs)s groups="base.group_erp_manager"/>
            </form>
        """, model='ir.attachment', field='access_token', valid=True)
        validate("""
            <form string="View attachment">
                <group groups="base.group_erp_manager">
                    <field name="company_id" %(attrs)s/>
                </group>
            </form>
        """, model='ir.attachment', field='access_token', valid=True)

        # 'access_token' has 'group_user' groups but only 'group_user' has access to read 'ir.attachment'
        validate("""
            <form string="View attachment">
                <field name="access_token"/>
                <field name="company_id" %(attrs)s/>
            </form>
        """, model='ir.attachment', field='access_token', valid=True)
        validate("""
            <form string="View attachment">
                <field name="access_token"/>
                <field name="company_id" %(attrs)s groups="base.group_portal"/>
            </form>
        """, model='ir.attachment', field='access_token', valid=True)
        validate("""
            <form string="View attachment">
                <field name="company_id" %(attrs)s groups="base.group_portal"/>
            </form>
        """, model='ir.attachment', field='access_token', valid=True)
        validate("""
            <form string="View attachment">
                <field name="company_id" %(attrs)s/>
            </form>
        """, model='ir.attachment', field='access_token', valid=True)

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_attrs_missing_field(self):
        user = self.env['res.users'].create({
            'name': 'A User',
            'login': 'a_user',
            'email': 'a@user.com',
            'group_ids': [(4, self.env.ref('base.group_user').id)],
        })

        def validate(template, field, demo=True, no_add=False):
            # add 'access_token' field automatically
            view = self.View.create({
                'name': 'Form view attachment',
                'model': 'ir.attachment',
                'arch': template,
            })
            # cached view
            arch = self.env['ir.attachment']._get_view_cache(view_id=view.id)['arch']
            tree = etree.fromstring(arch)
            nodes = tree.xpath(f"//field[@name='{field}'][@invisible='True'][@readonly='True']")
            if no_add:
                nodes = [etree.tostring(node, encoding='unicode') for node in nodes]
                self.assertFalse(nodes, f"Field '{field}' should not be added automatically")
                return
            self.assertTrue(len(nodes) == 1, f"Field '{field}' should be added automatically")

            # admin
            arch = self.env['ir.attachment'].get_view(view_id=view.id)['arch']
            tree = etree.fromstring(arch)
            nodes = tree.xpath(f"//field[@name='{field}'][@invisible='True'][@readonly='True']")
            self.assertTrue(len(nodes) == 1, f"Field '{field}' should be added automatically")

            # user
            arch = self.env['ir.attachment'].with_user(user).get_view(view_id=view.id)['arch']
            tree = etree.fromstring(arch)
            nodes = tree.xpath(f"//field[@name='{field}'][@invisible='True'][@readonly='True']")
            if demo:
                self.assertTrue(len(nodes) == 1, f"Field '{field}' should be added automatically")
            else:
                self.assertFalse(nodes, f"Field '{field}' should be added automatically but was removed by access rigth")

        # add missing field
        validate("""
                <form string="View attachment">
                    <field name="company_id" invisible="name != 'toto'"/>
                </form>
            """, field='name')


        # add missing field with groups
        validate("""
                <form string="View attachment">
                    <field name="company_id" invisible="not access_token" groups="base.group_erp_manager"/>
                </form>
            """, field='access_token', demo=False)

        # add missing field with multi groups
        validate("""
                <form string="View attachment">
                    <field name="company_id" invisible="not name" groups="base.group_erp_manager"/>
                    <field name="company_id" invisible="not name" groups="base.group_system"/>
                </form>
            """, field='name', demo=False)
        # add missing field without group because the view is already restricted to the group 'base.group_user'
        validate("""
                <form string="View attachment">
                    <field name="company_id" invisible="not name" groups="base.group_erp_manager"/>
                    <field name="company_id" invisible="not name" groups="base.group_system"/>
                    <field name="company_id" invisible="not name" groups="base.group_multi_company"/>
                    <field name="company_id" invisible="not name" groups="base.group_user"/>
                </form>
            """, field='name', demo=True)
        validate("""
                <form string="View attachment">
                    <field name="company_id" invisible="not name" groups="base.group_erp_manager"/>
                    <field name="company_id" invisible="not name"/>
                </form>
            """, field='name', demo=True)

        # nested groups
        validate("""
                <form string="View attachment">
                    <group groups="base.group_erp_manager">
                        <field name="company_id" invisible="not access_token"/>
                    </group>
                </form>
            """, field='access_token', demo=False)
        validate("""
                <form string="View attachment">
                    <group groups="base.group_erp_manager">
                        <field name="company_id" invisible="not name" groups="base.group_multi_company"/>
                        <field name="company_id" invisible="not name" groups="base.group_user"/>
                    </group>
                </form>
            """, field='name', demo=False)
        validate("""
                <form string="View attachment">
                    <group groups="base.group_erp_manager" invisible="not display_name">
                        <field name="company_id" invisible="not name" groups="base.group_multi_company"/>
                        <field name="company_id" invisible="not name" groups="base.group_user"/>
                    </group>
                </form>
            """, field='name', demo=False)
        validate("""
                <form string="View attachment">
                    <group groups="base.group_erp_manager" invisible="not display_name">
                        <field name="company_id" invisible="not name" groups="base.group_multi_company"/>
                        <field name="company_id" invisible="not name" groups="base.group_user"/>
                    </group>
                </form>
            """, field='display_name', demo=False)
        validate("""
                <form string="View attachment">
                    <group groups="base.group_user" invisible="not display_name">
                        <field name="company_id" invisible="not name" groups="base.group_multi_company"/>
                        <field name="company_id" invisible="not name" groups="base.group_erp_manager"/>
                    </group>
                </form>
            """, field='name', demo=False)
        validate("""
                <form string="View attachment">
                    <group groups="base.group_user" invisible="not display_name">
                        <field name="company_id" invisible="not name" groups="base.group_multi_company"/>
                        <field name="company_id" invisible="not name" groups="base.group_erp_manager"/>
                    </group>
                </form>
            """, field='display_name', demo=True)

        # field already exist with implied groups
        validate("""
                <form string="View attachment">
                    <field name="name" groups="base.group_user"/>
                    <field name="name" groups="base.group_multi_company"/>

                    <group groups="base.group_erp_manager" invisible="not name">
                        <field name="company_id" invisible="not name" groups="base.group_multi_company"/>
                        <field name="company_id" invisible="not name" groups="base.group_user"/>
                    </group>
                </form>
            """, field='name', no_add=True)

        # add missing field without group because the view is already restricted to the group 'base.group_user'
        validate("""
                <form string="View attachment">
                    <field name="access_token" invisible="not name"/>
                </form>
            """, field='name', demo=True)

    def test_empty_groups_attrib(self):
        """Ensure we allow empty groups attribute"""
        view = self.View.create({
            'name': 'foo',
            'model': 'res.partner',
            'arch': """
                <form>
                    <field name="name" groups="" />
                </form>
            """,
        })
        arch = self.env['res.partner'].get_view(view_id=view.id)['arch']
        tree = etree.fromstring(arch)
        nodes = tree.xpath("//field[@name='name' and not (@groups)]")
        self.assertEqual(1, len(nodes))

    def test_invisible_groups_with_groups_in_model(self):
        """Tests the attrs is well processed to modifiers for a field node combining:
        - a `groups` attribute on the field node in the view architecture
        - a `groups` attribute on the field in the Python model
        This is an edge case and it worths a unit test."""
        self.patch(self.env.registry['res.partner'].name, 'groups', 'base.group_system')
        self.env.user.group_ids += self.env.ref('base.group_multi_company')
        view = self.View.create({
            'name': 'foo',
            'model': 'res.partner',
            'arch': """
                <form>
                    <field name="active"/>
                    <field name="name" groups="base.group_multi_company" invisible="active"/>
                </form>
            """,
        })
        arch = self.env['res.partner'].get_view(view_id=view.id)['arch']
        tree = etree.fromstring(arch)
        node_field_name = tree.xpath('//field[@name="name"]')[0]
        self.assertEqual(node_field_name.get('invisible'), "active")

    def test_button(self):
        arch = """
            <form>
                <button type="object" name="%s"/>
            </form>
        """
        self.assertValid(arch % 'action_archive', name='valid button name')
        self.assertInvalid(
            arch % 'wtfzzz', 'wtfzzz is not a valid action on ir.ui.view',
            name='button name is not even a method',
        )
        self.assertInvalid(
            arch % '_check_xml',
            '_check_xml on ir.ui.view is private and cannot be called from a button',
            name='button name is a private method',
        )
        self.assertWarning(arch % 'postprocess_and_fields', name='button name is a method that requires extra arguments')
        arch = """
            <form>
                <button type="action" name="%s"/>
            </form>
        """
        self.assertInvalid(arch % 0, 'Action 0 (id: 0) does not exist for button of type action.')
        self.assertInvalid(arch % 'base.random_xmlid', 'Invalid xmlid base.random_xmlid for button of type action')
        self.assertInvalid('<form><button special="dummy"/></form>', "Invalid special 'dummy' in button")
        self.assertInvalid(arch % 'base.partner_root', "base.partner_root is of type res.partner, expected a subclass of ir.actions.actions")

    def test_tree(self):
        arch = """
            <list>
                <field name="name"/>
                <button type='object' name="action_archive"/>
                %s
            </list>
        """
        self.assertValid(arch % '')
        self.assertInvalid(arch % '<group/>', "List child can only have one of field, button, control, groupby, widget, header tag (not group)")

    def test_tree_groupby(self):
        arch = """
            <list>
                <field name="name"/>
                <groupby name="%s">
                    <button type="object" name="action_archive"/>
                </groupby>
            </list>
        """
        self.assertValid(arch % ('model_data_id'))
        self.assertInvalid(arch % ('type'), "Field 'type' found in 'groupby' node can only be of type many2one, found selection")
        self.assertInvalid(arch % ('dummy'), "Field 'dummy' found in 'groupby' node does not exist in model ir.ui.view")

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
        view = self.assertValid(arch % ('', '<field name="noupdate"/>'))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertFalse(etree.fromstring(view_arch).xpath('//field[@name="noupdate"][@invisible][@readonly]'))

        view = self.assertValid(arch % ('', ''))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//groupby/field[@name="noupdate"][@invisible][@readonly]'))

        self.assertInvalid(
            arch % ('<field name="noupdate"/>', ''),
            '''Field "noupdate" does not exist in model "ir.ui.view"''',
        )
        self.assertInvalid(
            arch % ('', '<field name="noupdate"/><field name="fake_field"/>'),
            '''Field "fake_field" does not exist in model "ir.model.data"''',
        )

    def test_check_xml_on_reenable(self):
        view1 = self.View.create({
            'name': 'valid _check_xml',
            'model': 'ir.ui.view',
            'arch': """
                <form string="View">
                    <field name="name"/>
                </form>
            """,
        })
        view2 = self.View.create({
            'name': 'valid _check_xml',
            'model': 'ir.ui.view',
            'inherit_id': view1.id,
            'active': False,
            'arch': """
                <field name="foo" position="after">
                    <field name="bar"/>
                </field>
            """
        })
        with self.assertRaises(ValidationError):
            view2.active = True

        # Re-enabling the view and correcting it at the same time should not raise the `_check_xml` constraint.
        view2.write({
            'active': True,
            'arch': """
                <field name="name" position="after">
                    <span>bar</span>
                </field>
            """,
        })

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
        self.assertValid('<form><div class="alert alert-success" role="alertdialog"/></form>')
        self.assertValid('<form><div class="alert alert-success" role="status"/></form>')
        self.assertWarning('<form><div class="alert alert-success"/></form>')

    def test_valid_prohibited_none_role(self):
        self.assertWarning('<form><div role="none"/></form>')
        self.assertWarning('<form><div role="presentation"/></form>')

    def test_valid_alternative_image_text(self):
        self.assertValid('<form><img src="a" alt="a image"></img></form>')
        self.assertWarning('<form><img src="a"></img></form>')

    def test_valid_accessibility_icon_text(self):
        self.assertWarning(
            '<form><span class="fa fa-warning"/></form>',
            'A <span> with fa class (fa fa-warning) must have title in its tag, parents, descendants or have text'
        )
        self.assertWarning(
            '<form><button icon="fa-warning"/></form>',
            'A button with icon attribute (fa-warning) must have title in its tag, parents, descendants or have text'
        )
        self.assertWarning(
            '<form><span class="fa fa-warning"/><label for="key"/><field name="key"/></form>',
            'A <span> with fa class (fa fa-warning) must have title in its tag, parents, descendants or have text'
        )
        self.assertValid('<form><button icon="fa-warning"/>text</form>')
        self.assertValid('<form><span class="fa fa-warning"/>text</form>')
        self.assertValid('<form><span class="fa fa-warning"/><label for="key" string="Some Text"/><field name="key"/></form>')
        self.assertValid('<form><span class="fa fa-warning"/><field name="key" string="Some Text"/></form>')
        self.assertValid('<form>text<span class="fa fa-warning"/></form>')
        self.assertValid('<form><span class="fa fa-warning">text</span></form>')
        self.assertValid('<form><span title="text" class="fa fa-warning"/></form>')
        self.assertValid('<form><span aria-label="text" class="fa fa-warning"/></form>')

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
        self.assertValid('<form><div class="o_progressbar" role="progressbar" aria-valuenow="14" aria-valuemin="0" aria-valuemax="100">14%</div></form>')
        self.assertWarning('<form><div class="o_progressbar" aria-valuenow="14" aria-valuemin="0" aria-valuemax="100">14%</div></form>')
        self.assertWarning('<form><div class="o_progressbar" role="progressbar" aria-valuemin="0" aria-valuemax="100">14%</div></form>')
        self.assertWarning('<form><div class="o_progressbar" role="progressbar" aria-valuenow="14" aria-valuemax="100">14%</div></form>')
        self.assertWarning('<form><div class="o_progressbar" role="progressbar" aria-valuenow="14" aria-valuemin="0" >14%</div></form>')

    def test_valid_simili_tabpanel(self):
        self.assertValid('<form><div class="tab-pane" role="tabpanel"/></form>')
        self.assertWarning('<form><div class="tab-pane"/></form>')

    def test_valid_simili_tablist(self):
        self.assertValid('<form><div class="nav-tabs" role="tablist"/></form>')
        self.assertWarning('<form><div class="nav-tabs"/></form>')

    def test_valid_simili_tab(self):
        self.assertValid('<form><a data-bs-toggle="tab" role="tab" aria-controls="test"/></form>')
        self.assertWarning('<form><a data-bs-toggle="tab" aria-controls="test"/></form>')
        self.assertWarning('<form><a data-bs-toggle="tab" role="tab"/></form>')
        self.assertWarning('<form><a data-bs-toggle="tab" role="tab" aria-controls="#test"/></form>')

    def test_valid_focusable_button(self):
        self.assertValid('<form><a class="btn" role="button"/></form>')
        self.assertValid('<form><button class="btn" role="button"/></form>')
        self.assertValid('<form><select class="btn" role="button"/></form>')
        self.assertValid('<form><input type="button" class="btn" role="button"/></form>')
        self.assertValid('<form><input type="submit" class="btn" role="button"/></form>')
        self.assertValid('<form><input type="reset" class="btn" role="button"/></form>')
        self.assertValid('<form><div type="reset" class="btn btn-group" role="button"/></form>')
        self.assertValid('<form><div type="reset" class="btn btn-toolbar" role="button"/></form>')
        self.assertValid('<form><div type="reset" class="btn btn-addr" role="button"/></form>')
        self.assertWarning('<form><div class="btn" role="button"/></form>')
        self.assertWarning('<form><input type="email" class="btn" role="button"/></form>')

    def test_partial_validation(self):
        self.View = self.View.with_context(load_all_views=True)

        # base view
        view0 = self.assertValid("""
            <form string="View">
                <field name="model"/>
                <field name="inherit_id" domain="[('model', '=', model)]"/>
            </form>
        """)

        # added elements should be validated
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

        # modifying attributes should validate the target element
        self.assertInvalid(
            """<field name="inherit_id" position="attributes">
                <attribute name="domain">[('invalid_field', '=', 'dummy')]</attribute>
            </field>""",
            """Unknown field "ir.ui.view.invalid_field" in domain of <field name="inherit_id"> ([('invalid_field', '=', 'dummy')]))""",
            inherit_id=view0.id,
        )

        # replacing an element should validate the whole view
        view_arch = self.View.get_views([(view0.id, 'form')])['views']['form']['arch']
        self.assertFalse(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))
        view0bis = None
        view0bis = self.assertValid(
            """<field name="model" position="replace"/>""",
            inherit_id=view0.id,
        )
        view_arch = self.View.get_views([(view0.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))
        view0bis.active = False
        view_arch = self.View.get_views([(view0.id, 'form')])['views']['form']['arch']
        self.assertFalse(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))

        # moving an element should have no impact; this test checks that the
        # implementation does not flag the inner element to be validated, which
        # prevents to locate the corresponding element inside the arch
        self.assertValid(
            """<field name="group_ids" position="before">
                <label for="group_ids" position="move"/>
            </field>""",
            inherit_id=view2.id,
        )

        # modifying a view extension should validate the other views
        self.assertFalse(etree.fromstring(view_arch).xpath('//field[@name="name"][@invisible][@readonly]'))
        view1.arch = """<form position="inside">
            <field name="type"/>
        </form>"""
        view_arch = self.View.get_views([(view0.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//field[@name="name"][@invisible][@readonly]'))

    def test_graph_fields(self):
        self.assertValid('<graph string="Graph"><field name="model" type="row"/><field name="inherit_id" type="measure"/></graph>')
        self.assertInvalid(
            '<graph string="Graph"><label for="model"/><field name="model" type="row"/><field name="inherit_id" type="measure"/></graph>',
            'A <graph> can only contains <field> nodes, found a <label>'
        )

    def test_graph_attributes(self):
        self.assertValid('<graph string="Graph" cumulated="1" ><field name="model" type="row"/><field name="inherit_id" type="measure"/></graph>')

    def test_view_ref(self):
        view = self.assertValid(
            """
                <form>
                    <field name="group_ids" class="canary"/>
                </form>
            """
        )
        self.env["ir.model.data"].create({
            'module': 'base',
            'name': 'test_views_test_view_ref',
            'model': 'ir.ui.view',
            'res_id': view.id,
        })
        view_data = self.env['ir.ui.view'].with_context(form_view_ref='base.test_views_test_view_ref').get_view()
        self.assertEqual(view.id, view_data['id'], "The view returned should be test_views_test_view_ref")
        view_data = self.env['ir.ui.view'].with_context(form_view_ref='base.test_views_test_view_ref').get_view(view.id)
        tree = etree.fromstring(view_data['arch'])
        field_groups_id = tree.xpath('//field[@name="group_ids"]')[0]
        self.assertEqual(
            len(field_groups_id.xpath(".//*[@class='canary']")),
            0,
            "The view test_views_test_view_ref should not be in the views of the many2many field all_group_ids"
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

    @mute_logger('odoo.addons.base.models.ir_ui_view')
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

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_forbidden_data_tooltip_attributes_in_form(self):
        arch = "<form>%s</form>"

        self.assertInvalid(
            arch % ('<span data-tooltip="Test"/>'),
            """Error while validating view near:

<form __validate__="1"><span data-tooltip="Test"/></form>
Forbidden attribute used in arch (data-tooltip)."""
        )

        self.assertInvalid(
            arch % ('<span data-tooltip-template="test"/>'),
            """Error while validating view near:

<form __validate__="1"><span data-tooltip-template="test"/></form>
Forbidden attribute used in arch (data-tooltip-template)."""
        )

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_forbidden_data_tooltip_attributes_in_kanban(self):
        arch = "<kanban><templates><t t-name='card'>%s</t></templates></kanban>"

        self.assertInvalid(
            arch % ('<span data-tooltip="Test"/>'),
            """Error while validating view near:

<kanban __validate__="1"><templates><t t-name="card"><span data-tooltip="Test"/></t></templates></kanban>
Forbidden attribute used in arch (data-tooltip)."""
        )

        self.assertInvalid(
            arch % ('<span data-tooltip-template="test"/>'),
            """Error while validating view near:

<kanban __validate__="1"><templates><t t-name="card"><span data-tooltip-template="test"/></t></templates></kanban>
Forbidden attribute used in arch (data-tooltip-template)."""
        )

        self.assertInvalid(
            arch % ('<span t-att-data-tooltip="test"/>'),
            """Error while validating view near:

<kanban __validate__="1"><templates><t t-name="card"><span t-att-data-tooltip="test"/></t></templates></kanban>
Forbidden attribute used in arch (t-att-data-tooltip)."""
        )

        self.assertInvalid(
            arch % ('<span t-attf-data-tooltip-template="{{ test }}"/>'),
            """Error while validating view near:

<kanban __validate__="1"><templates><t t-name="card"><span t-attf-data-tooltip-template="{{ test }}"/></t></templates></kanban>
Forbidden attribute used in arch (t-attf-data-tooltip-template)."""
        )

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_forbidden_use_of___comp___in_kanban(self):
        arch = "<kanban><templates><t t-name='card'>%s</t></templates></kanban>"
        self.assertInvalid(
            arch % '<t t-esc="__comp__.props.resId"/>',
            """Error while validating view near:

<kanban __validate__="1"><templates><t t-name="card"><t t-esc="__comp__.props.resId"/></t></templates></kanban>
Forbidden use of `__comp__` in arch."""
        )

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_check_primary_when_update_siblins_inherited_tree(self):
        # P: primary, E: extension
        #
        #         P1
        #       /    \
        #     E1      E2
        #    /  \    /  \
        #   E3  E4  P2  E5
        #
        # If we update the E4, we should check the P1 and P2 views
        View = self.env['ir.ui.view']
        p1 = View.create({
            'name': 'test_view_p1',
            'type': 'qweb',
            'key': 'website.test_view_p1',
            'arch_db': '''<div><p1/></div>'''
        })
        View.create({
            'name': 'test_view_e1',
            'mode': 'extension',
            'inherit_id': p1.id,
            'arch_db': '<div position="inside"><e1/></div>',
            'key': 'website.test_view_e1',
        })
        e2 = View.create({
            'name': 'test_view_e2',
            'mode': 'extension',
            'inherit_id': p1.id,
            'arch_db': '<div position="inside"><e2/></div>',
            'key': 'website.test_view_e2',
        })
        View.create({
            'name': 'test_view_e3',
            'mode': 'extension',
            'inherit_id': p1.id,
            'arch_db': '<div position="inside"><e3/></div>',
            'key': 'website.test_view_e3',
        })
        e4 = View.create({
            'name': 'test_view_e4',
            'mode': 'extension',
            'inherit_id': p1.id,
            'arch_db': '<div position="inside"><e4/></div>',
            'key': 'website.test_view_e4',
        })
        p2 = View.create({
            'name': 'test_view_p2',
            'mode': 'primary',
            'inherit_id': e2.id,
            'arch_db': '<e4 position="replace"><p2/></e4>',
            'key': 'website.test_view_p2',
            'active': False,
        })
        View.create({
            'name': 'test_view_e5',
            'mode': 'extension',
            'inherit_id': p1.id,
            'arch_db': '<div position="inside"><e5/></div>',
            'key': 'website.test_view_e5',
        })

        self.assertEqual(self.env['ir.qweb']._render(p1.id), '<div><p1></p1><e1></e1><e2></e2><e3></e3><e4></e4><e5></e5></div>')
        e4.active = False
        self.assertEqual(self.env['ir.qweb']._render(p1.id), '<div><p1></p1><e1></e1><e2></e2><e3></e3><e5></e5></div>')

        with self.assertRaises(ValidationError) as catcher:
            p2.active = True
        self.assertIn("Element '<e4>' cannot be located in parent view", str(catcher.exception.args[0]))

        e4.active = True
        p2.active = True
        self.assertEqual(self.env['ir.qweb']._render(p1.id), '<div><p1></p1><e1></e1><e2></e2><e3></e3><e4></e4><e5></e5></div>')
        self.assertEqual(self.env['ir.qweb']._render(p2.id), '<div><p1></p1><e1></e1><e2></e2><e3></e3><p2></p2><e5></e5></div>')

        with self.assertRaises(ValidationError) as catcher:
            e4.active = False
        self.assertIn("Element '<e4>' cannot be located in parent view", str(catcher.exception.args[0]))

        with self.assertRaises(ValidationError) as catcher:
            View.create({
                'name': 'test_view_e6',
                'mode': 'extension',
                'inherit_id': e2.id,
                'arch_db': '<e4 position="replace"><e6/></e4>',
                'key': 'website.test_view_e6',
            })
        self.assertIn("Element '<e4>' cannot be located in parent view", str(catcher.exception.args[0]))


@tagged('post_install', '-at_install')
class TestDebugger(common.TransactionCase):
    def test_t_debug_in_qweb_based_views(self):
        View = self.env['ir.ui.view']
        views_with_t_debug = View.search([["arch_db", "like", "t-debug="]])
        self.assertEqual([v.xml_id for v in views_with_t_debug], [])


class TestViewTranslations(common.TransactionCase):
    # these tests are essentially the same as in test_translate.py, but they use
    # the computed field 'arch' instead of the translated field 'arch_db'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('fr_FR')
        cls.env['res.lang']._activate_lang('nl_NL')
        cls.env['ir.module.module']._load_module_terms(['base'], ['fr_FR', 'nl_NL'])

    def create_view(self, archf, terms, **kwargs):
        view = self.env['ir.ui.view'].create({
            'name': 'test',
            'model': 'res.partner',
            'arch': archf % terms,
        })
        # DLE P70: `_sync_terms_translations`, which delete translations for which there is no value, is called sooner than before
        # because it's called in `_write`, which is called by `flush`, which is called by the `search`.
        # `arch_db` is in `_write` instead of `create` because `arch_db` is the inverse of `arch`.
        # We need to flush `arch_db` before creating the translations otherwise the translation for which there is no value will be deleted,
        # while the `test_sync_update` specifically needs empty translations
        self.env.flush_all()
        val = {'en_US': archf % terms}
        for lang, trans_terms in kwargs.items():
            val[lang] = archf % trans_terms
        query = "UPDATE ir_ui_view SET arch_db = %s WHERE id = %s"
        self.env.cr.execute(query, [Json(val), view.id])
        self.env.invalidate_all()
        return view

    def test_sync(self):
        """ Check translations of 'arch' after minor change in source terms. """
        archf = '<form string="X">%s</form>'
        terms_en = ('Bread and cheeze',)
        terms_fr = ('Pain et fromage',)
        terms_nl = ('Brood and kaas',)
        view = self.create_view(archf, terms_en, en_US=terms_en, fr_FR=terms_fr, nl_NL=terms_nl)

        env_nolang = self.env(context={})
        env_en = self.env(context={'lang': 'en_US'})
        env_fr = self.env(context={'lang': 'fr_FR'})
        env_nl = self.env(context={'lang': 'nl_NL'})

        self.assertEqual(view.with_env(env_nolang).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_en).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_fr).arch, archf % terms_fr)
        self.assertEqual(view.with_env(env_nl).arch, archf % terms_nl)

        # modify source term in view (fixed type in 'cheeze')
        terms_en = ('Bread and cheese',)
        view.with_env(env_en).write({'arch': archf % terms_en})

        # check whether translations have been synchronized
        self.assertEqual(view.with_env(env_nolang).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_en).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_fr).arch, archf % terms_fr)
        self.assertEqual(view.with_env(env_nl).arch, archf % terms_nl)

        view = self.create_view(archf, terms_fr, en_US=terms_en, fr_FR=terms_fr, nl_NL=terms_nl)
        # modify source term in view in another language with close term
        new_terms_fr = ('Pains et fromage',)
        view.with_env(env_fr).write({'arch': archf % new_terms_fr})

        # check whether translations have been synchronized
        self.assertEqual(view.with_env(env_nolang).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_en).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_fr).arch, archf % new_terms_fr)
        self.assertEqual(view.with_env(env_nl).arch, archf % terms_nl)

    def test_sync_xml(self):
        """ Check translations of 'arch' after xml tags changes in source terms. """
        archf = '<form string="X">%s</form>'
        terms_en = ('Bread and cheese',)
        terms_fr = ('Pain et fromage',)
        terms_nl = ('Brood and kaas',)
        view = self.create_view(archf, terms_en, en_US=terms_en, fr_FR=terms_fr, nl_NL=terms_nl)

        env_nolang = self.env(context={})
        env_en = self.env(context={'lang': 'en_US'})
        env_fr = self.env(context={'lang': 'fr_FR'})
        env_nl = self.env(context={'lang': 'nl_NL'})

        self.assertEqual(view.with_env(env_nolang).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_en).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_fr).arch, archf % terms_fr)
        self.assertEqual(view.with_env(env_nl).arch, archf % terms_nl)

        # modify source term in view (add css style)
        terms_en = ('Bread <span style="font-weight:bold">and</span> cheese',)
        view.with_env(env_en).write({'arch': archf % terms_en})

        # check whether translations have been kept
        self.assertEqual(view.with_env(env_nolang).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_en).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_fr).arch, archf % terms_fr)
        self.assertEqual(view.with_env(env_nl).arch, archf % terms_nl)

        # modify source term in view (actual text change)
        terms_en = ('Bread <span style="font-weight:bold">and</span> butter',)
        view.with_env(env_en).write({'arch': archf % terms_en})

        # check whether translations have been reset
        self.assertEqual(view.with_env(env_nolang).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_en).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_fr).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_nl).arch, archf % terms_en)

    def test_sync_update(self):
        """ Check translations after major changes in source terms. """
        archf = '<form string="X"><div>%s</div><div>%s</div></form>'
        terms_src = ('Subtotal', 'Subtotal:')
        terms_en = ('', 'Sub total:')
        view = self.create_view(archf, terms_src, en_US=terms_en)

        # modifying the arch should sync existing translations without errors
        new_arch = archf % ('Subtotal', 'Subtotal : <br/>')
        view.write({"arch": new_arch})
        self.assertEqual(view.arch, new_arch)

    def test_cache_consistency(self):
        view = self.env["ir.ui.view"].create({
            "name": "test_translate_xml_cache_invalidation",
            "model": "res.partner",
            "arch": "<form><b>content</b></form>",
        })
        view_fr = view.with_context({"lang": "fr_FR"})
        self.assertIn("<b>", view.arch_db)
        self.assertIn("<b>", view.arch)
        self.assertIn("<b>", view_fr.arch_db)
        self.assertIn("<b>", view_fr.arch)

        # write with no lang, and check consistency in other languages
        view.write({"arch": "<form><i>content</i></form>"})
        self.assertIn("<i>", view.arch_db)
        self.assertIn("<i>", view.arch)
        self.assertIn("<i>", view_fr.arch_db)
        self.assertIn("<i>", view_fr.arch)

    def test_no_groups_for_inherited(self):
        parent = self.env["ir.ui.view"].create({
            "name": "test_no_groups_for_inherited_parent",
            "model": "ir.ui.view",
            "arch": "<form></form>",
        })

        view = self.env["ir.ui.view"].create({
            "name": "test_no_groups_for_inherited_child",
            "model": "ir.ui.view",
            "arch": "<data></data>",
            "inherit_id": parent.id,
            "mode": "extension",
        })

        with self.assertRaises(ValidationError):
            view.write({'group_ids': [1]})

        view.write({'mode': 'primary'})
        view.write({'group_ids': [1]})

        with self.assertRaises(ValidationError):
            view.write({'mode': 'extension'})


class ViewModeField(ViewCase):
    """
    This should probably, eventually, be folded back into other test case
    classes, integrating the test (or not) of the mode field to regular cases
    """

    def testModeImplicitValue(self):
        """ mode is auto-generated from inherit_id:
        * inherit_id -> mode=extension
        * not inherit_id -> mode=primary
        """
        view = self.View.create({
            'inherit_id': None,
            'arch': '<qweb/>'
        })
        self.assertEqual(view.mode, 'primary')

        view2 = self.View.create({
            'inherit_id': view.id,
            'arch': '<qweb/>'
        })
        self.assertEqual(view2.mode, 'extension')

        view2.write({'inherit_id': None})
        self.assertEqual(view2.mode, 'primary')

        view2.write({'inherit_id': view.id})
        self.assertEqual(view2.mode, 'extension')

    @mute_logger('odoo.sql_db')
    def testModeExplicit(self):
        view = self.View.create({
            'inherit_id': None,
            'arch': '<qweb/>'
        })
        view2 = self.View.create({
            'inherit_id': view.id,
            'mode': 'primary',
            'arch': '<qweb/>'
        })
        self.assertEqual(view.mode, 'primary')
        self.assertEqual(view2.mode, 'primary')

        with self.assertRaises(IntegrityError):
            self.View.create({
                'inherit_id': None,
                'mode': 'extension',
                'arch': '<qweb/>'
            })

    @mute_logger('odoo.sql_db')
    def testPurePrimaryToExtension(self):
        """
        A primary view with inherit_id=None can't be converted to extension
        """
        view_pure_primary = self.View.create({
            'inherit_id': None,
            'arch': '<qweb/>'
        })
        with self.assertRaises(IntegrityError):
            view_pure_primary.write({'mode': 'extension'})
            view_pure_primary.env.flush_all()

    def testInheritPrimaryToExtension(self):
        """
        A primary view with an inherit_id can be converted to extension
        """
        base = self.View.create({
            'inherit_id': None,
            'arch': '<qweb/>',
        })
        view = self.View.create({
            'inherit_id': base.id,
            'mode': 'primary',
            'arch': '<qweb/>'
        })

        view.write({'mode': 'extension'})

    def testDefaultExtensionToPrimary(self):
        """
        An extension view can be converted to primary
        """
        base = self.View.create({
            'inherit_id': None,
            'arch': '<qweb/>',
        })
        view = self.View.create({
            'inherit_id': base.id,
            'arch': '<qweb/>'
        })

        view.write({'mode': 'primary'})

    def testChangeInheritOfPrimary(self):
        """
        A primary view with an inherit_id must remain primary when changing the inherit_id
        """
        base1 = self.View.create({
            'inherit_id': None,
            'arch': '<qweb/>',
        })
        base2 = self.View.create({
            'inherit_id': None,
            'arch': '<qweb/>',
        })
        view = self.View.create({
            'mode': 'primary',
            'inherit_id': base1.id,
            'arch': '<qweb/>',
        })
        self.assertEqual(view.mode, 'primary')
        view.write({'inherit_id': base2.id})
        self.assertEqual(view.mode, 'primary')


class TestDefaultView(ViewCase):
    def testDefaultViewBase(self):
        self.View.create({
            'inherit_id': False,
            'priority': 10,
            'mode': 'primary',
            'arch': '<qweb/>',
        })
        view2 = self.View.create({
            'inherit_id': False,
            'priority': 1,
            'mode': 'primary',
            'arch': '<qweb/>',
        })

        default = self.View.default_view(False, 'qweb')
        self.assertEqual(
            default, view2.id,
            "default_view should get the view with the lowest priority for "
            "a (model, view_type) pair"
        )

    def testDefaultViewPrimary(self):
        view1 = self.View.create({
            'inherit_id': False,
            'priority': 10,
            'mode': 'primary',
            'arch': '<qweb/>',
        })
        self.View.create({
            'inherit_id': False,
            'priority': 5,
            'mode': 'primary',
            'arch': '<qweb/>',
        })
        view3 = self.View.create({
            'inherit_id': view1.id,
            'priority': 1,
            'mode': 'primary',
            'arch': '<qweb/>',
        })

        default = self.View.default_view(False, 'qweb')
        self.assertEqual(
            default, view3.id,
            "default_view should get the view with the lowest priority for "
            "a (model, view_type) pair in all the primary tables"
        )


class TestViewCombined(ViewCase):
    """
    * When asked for a view, instead of looking for the closest parent with
      inherit_id=False look for mode=primary
    * If root.inherit_id, resolve the arch for root.inherit_id (?using which
      model?), then apply root's inheritance specs to it
    * Apply inheriting views on top
    """

    def setUp(self):
        super(TestViewCombined, self).setUp()

        self.a1 = self.View.create({
            'model': 'a',
            'arch': '<qweb><a1/></qweb>'
        })
        self.a2 = self.View.create({
            'model': 'a',
            'inherit_id': self.a1.id,
            'priority': 5,
            'arch': '<xpath expr="//a1" position="after"><a2/></xpath>'
        })
        self.a3 = self.View.create({
            'model': 'a',
            'inherit_id': self.a1.id,
            'arch': '<xpath expr="//a1" position="after"><a3/></xpath>'
        })
        # mode=primary should be an inheritance boundary in both direction,
        # even within a model it should not extend the parent
        self.a4 = self.View.create({
            'model': 'a',
            'inherit_id': self.a1.id,
            'mode': 'primary',
            'arch': '<xpath expr="//a1" position="after"><a4/></xpath>',
        })

        self.b1 = self.View.create({
            'model': 'b',
            'inherit_id': self.a3.id,
            'mode': 'primary',
            'arch': '<xpath expr="//a1" position="after"><b1/></xpath>'
        })
        self.b2 = self.View.create({
            'model': 'b',
            'inherit_id': self.b1.id,
            'arch': '<xpath expr="//a1" position="after"><b2/></xpath>'
        })

        self.c1 = self.View.create({
            'model': 'c',
            'inherit_id': self.a1.id,
            'mode': 'primary',
            'arch': '<xpath expr="//a1" position="after"><c1/></xpath>'
        })
        self.c2 = self.View.create({
            'model': 'c',
            'inherit_id': self.c1.id,
            'priority': 5,
            'arch': '<xpath expr="//a1" position="after"><c2/></xpath>'
        })
        self.c3 = self.View.create({
            'model': 'c',
            'inherit_id': self.c2.id,
            'priority': 10,
            'arch': '<xpath expr="//a1" position="after"><c3/></xpath>'
        })

        self.d1 = self.View.create({
            'model': 'd',
            'inherit_id': self.b1.id,
            'mode': 'primary',
            'arch': '<xpath expr="//a1" position="after"><d1/></xpath>'
        })

    def test_basic_read(self):
        context = {'check_view_ids': self.View.search([]).ids}
        arch = self.a1.with_context(context).get_combined_arch()
        self.assertEqual(
            etree.fromstring(arch),
            E.qweb(
                E.a1(),
                E.a3(),
                E.a2(),
            ), arch)

    def test_read_from_child(self):
        context = {'check_view_ids': self.View.search([]).ids}
        arch = self.a3.with_context(context).get_combined_arch()
        self.assertEqual(
            etree.fromstring(arch),
            E.qweb(
                E.a1(),
                E.a3(),
                E.a2(),
            ), arch)

    def test_read_from_child_primary(self):
        context = {'check_view_ids': self.View.search([]).ids}
        arch = self.a4.with_context(context).get_combined_arch()
        self.assertEqual(
            etree.fromstring(arch),
            E.qweb(
                E.a1(),
                E.a4(),
                E.a3(),
                E.a2(),
            ), arch)

    def test_cross_model_simple(self):
        context = {'check_view_ids': self.View.search([]).ids}
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
            ), arch)

    def test_cross_model_double(self):
        context = {'check_view_ids': self.View.search([]).ids}
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
            ), arch)

    def test_primary_after_extensions(self):
        # Here is a tricky use-case:                        a*
        #  - views a and d are primary                     / \
        #  - views b and c are extensions                 b   c
        #  - depth-first order is: a, b, d, c             |
        #  - combination order is: a, b, c, d             d*
        #
        # The arch of d has been chosen to fail if d is applied before c.
        # Because this child of 'b' is primary, it must be applied *after* the
        # other extensions of a!
        a = self.View.create({
            'model': 'a',
            'arch': '<qweb><a/></qweb>',
        })
        b = self.View.create({
            'model': 'a',
            'inherit_id': a.id,
            'arch': '<a position="after"><b/></a>'
        })
        c = self.View.create({  # pylint: disable=unused-variable
            'model': 'a',
            'inherit_id': a.id,
            'arch': '<a position="after"><c/></a>'
        })
        d = self.View.create({  # pylint: disable=unused-variable
            'model': 'a',
            'inherit_id': b.id,
            'mode': 'primary',
            'arch': '<a position="replace"/>',
        })

    def test_inherit_python_expression(self):
        main_view = self.View.create({
            'model': 'res.partner',
            'arch': '''
                <form>
                    <sheet>
                        <field name="name"/>
                    </sheet>
                </form>''',
        })

        def test_inherit(arch, result):
            view = self.View.create({
                'model': 'res.partner',
                'inherit_id': main_view.id,
                'mode': 'primary',
                'arch': arch,
            })
            python_expr = etree.fromstring(view.get_combined_arch())[0][0].get('invisible')
            self.assertEqual(python_expr, result)

        test_inherit('''
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">name == 'a'</attribute>
                </xpath>
            </data>
        ''', "name == 'a'")

        test_inherit('''
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">name == 'a'</attribute>
                </xpath>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">True</attribute>
                </xpath>
            </data>
        ''', "True")

        test_inherit('''
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">name == 'a'</attribute>
                </xpath>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible" add="name == 'b'" separator="or"/>
                </xpath>
            </data>
        ''', "(name == 'a') or (name == 'b')")

        test_inherit('''
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">name == 'e' and name == 'f'</attribute>
                    <attribute name="invisible" add="id == 33" separator="and"/>
                </xpath>
            </data>
        ''', "(name == 'e' and name == 'f') and (id == 33)")

        test_inherit('''
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">name == 'e' and name == 'f'</attribute>
                    <attribute name="invisible" add="id == 33" separator="and"/>
                    <attribute name="invisible" add="id == 42" separator="or"/>
                    <attribute name="invisible" add="id == 1" separator=" and "/>
                </xpath>
            </data>
        ''', "(((name == 'e' and name == 'f') and (id == 33)) or (id == 42)) and (id == 1)")

        test_inherit('''
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">id == 1</attribute>
                    <attribute name="invisible" add="id == 2" separator="and"/>
                    <attribute name="invisible" add="id == 3" separator="and"/>
                    <attribute name="invisible" add="id == 4" separator="and"/>
                </xpath>
            </data>
        ''', "(((id == 1) and (id == 2)) and (id == 3)) and (id == 4)")

        test_inherit('''
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">(((id == 1) and (id == 2)) and (id == 3)) and (id == 4)</attribute>
                    <attribute name="invisible" remove="id == 2" separator="and"/>
                </xpath>
            </data>
        ''', "(((id == 1)) and (id == 3)) and (id == 4)")

        test_inherit('''
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">(id == 1) and (id == 2) and (id == 3)</attribute>
                    <attribute name="invisible" remove="id == 2" separator="and"/>
                </xpath>
            </data>
        ''', "(id == 1) and (id == 3)")

        test_inherit('''
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">(((id == 1) and (id == 2)) and (id == 3)) and (id == 4)</attribute>
                    <attribute name="invisible" remove="id == 3" separator="and"/>
                </xpath>
            </data>
        ''', "(((id == 1) and (id == 2))) and (id == 4)")

        test_inherit('''
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">id == 1</attribute>
                    <attribute name="invisible" add="id == 2" separator="and"/>
                    <attribute name="invisible" remove="id == 2" separator="and"/>
                    <attribute name="invisible" remove="id == 1" separator="and"/>
                </xpath>
            </data>
        ''', None)

        test_inherit('''
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">id == 1</attribute>
                    <attribute name="invisible" add="id == 2" separator="and"/>
                    <attribute name="invisible" add="id == 3" separator="and"/>
                    <attribute name="invisible" add="id == 4" separator="and"/>
                    <attribute name="invisible" remove="id == 3" separator="and"/>
                </xpath>
            </data>
        ''', "(((id == 1) and (id == 2))) and (id == 4)")

        test_inherit('''
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">(((id == 1) and (id == 2)) and (id == 3)) and (id == 4)</attribute>
                    <attribute name="invisible" remove="id == 3" separator="and"/>
                    <attribute name="invisible" remove="NO_MATCH" separator="and"/>
                </xpath>
            </data>
        ''', "(((id == 1) and (id == 2))) and (id == 4)")

        test_inherit('''
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">id == 1</attribute>
                    <attribute name="invisible" add="id == 2" separator="and"/>
                    <attribute name="invisible" remove="id == 2" separator="and"/>
                    <attribute name="invisible" remove="id == 1" add="name" separator="and"/>
                </xpath>
            </data>
        ''', "name")

        test_inherit('''
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">id == 1</attribute>
                    <attribute name="invisible" add="id == 2" separator="and"/>
                    <attribute name="invisible" remove="id == 2" add="name == 'foo'" separator="and"/>
                    <attribute name="invisible" add="name" separator="and"/>
                </xpath>
            </data>
        ''', "(((id == 1)) and (name == 'foo')) and (name)")

        test_inherit('''
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">1 or not name</attribute>
                    <attribute name="invisible" remove="1" separator="or"/>
                </xpath>
            </data>
        ''', "not name")

        test_inherit('''
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">1 or not name</attribute>
                    <attribute name="invisible" add="id == 2" separator="and"/>
                    <attribute name="invisible" remove="1" separator="or"/>
                    <attribute name="invisible" remove="not name" separator="and"/>
                </xpath>
            </data>
        ''', "(id == 2)")

        test_inherit('''
            <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">1 or not name</attribute>
                    <attribute name="invisible" add="id == 2" separator="and"/>
                    <attribute name="invisible" remove="1" separator="or"/>
                </xpath>
            </data>
        ''', "(not name) and (id == 2)")

        self.assertInvalid(
            ''' <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible" position="add">True</attribute>
                </xpath>
            </data> ''',
            "Invalid attributes 'position' in element <attribute>",
            inherit_id=main_view.id,
            model=main_view.model,
        )

        self.assertInvalid(
            ''' <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible" add="True">text</attribute>
                </xpath>
            </data> ''',
            "Element <attribute> with 'add' or 'remove' cannot contain text 'text'",
            inherit_id=main_view.id,
            model=main_view.model,
        )

        self.assertInvalid(
            ''' <data>
                <xpath expr="//field[@name='name']" position="attributes">
                    <attribute name="invisible">id == 1</attribute>
                    <attribute name="invisible" add="id == 2" separator="else"/>
                </xpath>
            </data> ''',
            "Invalid separator 'else' for python expression 'invisible'; valid values are 'and' and 'or'",
            inherit_id=main_view.id,
            model=main_view.model,
        )

    def test_multi_combine(self):
        n1 = self.View.create({
            'model': 'a',
            'arch': '<qweb><n1/></qweb>'
        })
        self.View.create({
            'model': 'a',
            'inherit_id': n1.id,
            'priority': 5,
            'arch': '<xpath expr="//n1" position="after"><n2/></xpath>'
        })
        n3 = self.View.create({
            'model': 'a',
            'inherit_id': n1.id,
            'priority': 1,
            'arch': '<xpath expr="//n1" position="after"><n3/></xpath>'
        })
        n4 = self.View.create({
            'model': 'a',
            'inherit_id': n3.id,
            'mode': 'primary',
            'arch': '<xpath expr="//n1" position="after"><n4/></xpath>'
        })

        arch_a4 = self.a4.get_combined_arch()
        arch_n4 = n4.get_combined_arch()
        trees = (self.a4 + n4)._get_combined_archs()
        self.assertEqual(
            {k: etree.tostring(tree, encoding='unicode') for k, tree in zip(['a4', 'n4'], trees)},
            {'a4': arch_a4, 'n4': arch_n4})

    def test_multi_combine_with_same_ancestor(self):
        arch_a4 = self.a4.get_combined_arch()
        arch_c2 = self.c2.get_combined_arch()
        trees = (self.a4 + self.c2)._get_combined_archs()
        self.assertEqual(
            {k: etree.tostring(tree, encoding='unicode') for k, tree in zip(['a4', 'c2'], trees)},
            {'a4': arch_a4, 'c2': arch_c2})


class TestOptionalViews(ViewCase):
    """
    Tests ability to enable/disable inherited views, formerly known as
    inherit_option_id
    """

    def setUp(self):
        super(TestOptionalViews, self).setUp()
        self.v0 = self.View.create({
            'model': 'a',
            'arch': '<qweb><base/></qweb>',
        })
        self.v1 = self.View.create({
            'model': 'a',
            'inherit_id': self.v0.id,
            'active': True,
            'priority': 10,
            'arch': '<xpath expr="//base" position="after"><v1/></xpath>',
        })
        self.v2 = self.View.create({
            'model': 'a',
            'inherit_id': self.v0.id,
            'active': True,
            'priority': 9,
            'arch': '<xpath expr="//base" position="after"><v2/></xpath>',
        })
        self.v3 = self.View.create({
            'model': 'a',
            'inherit_id': self.v0.id,
            'active': False,
            'priority': 8,
            'arch': '<xpath expr="//base" position="after"><v3/></xpath>'
        })

    def test_applied(self):
        """ mandatory and enabled views should be applied
        """
        context = {'check_view_ids': self.View.search([]).ids}
        arch = self.v0.with_context(context).get_combined_arch()
        self.assertEqual(
            etree.fromstring(arch),
            E.qweb(
                E.base(),
                E.v1(),
                E.v2(),
            )
        )

    def test_applied_state_toggle(self):
        """ Change active states of v2 and v3, check that the results
        are as expected
        """
        self.v2.action_archive()
        context = {'check_view_ids': self.View.search([]).ids}
        arch = self.v0.with_context(context).get_combined_arch()
        self.assertEqual(
            etree.fromstring(arch),
            E.qweb(
                E.base(),
                E.v1(),
            )
        )

        self.v3.action_unarchive()
        context = {'check_view_ids': self.View.search([]).ids}
        arch = self.v0.with_context(context).get_combined_arch()
        self.assertEqual(
            etree.fromstring(arch),
            E.qweb(
                E.base(),
                E.v1(),
                E.v3(),
            )
        )

        self.v2.action_unarchive()
        context = {'check_view_ids': self.View.search([]).ids}
        arch = self.v0.with_context(context).get_combined_arch()
        self.assertEqual(
            etree.fromstring(arch),
            E.qweb(
                E.base(),
                E.v1(),
                E.v2(),
                E.v3(),
            )
        )


class TestXPathExtentions(common.BaseCase):
    def test_hasclass(self):
        tree = E.node(
            E.node({'class': 'foo bar baz'}),
            E.node({'class': 'foo bar'}),
            {'class': "foo"})

        self.assertEqual(
            len(tree.xpath('//node[hasclass("foo")]')),
            3)
        self.assertEqual(
            len(tree.xpath('//node[hasclass("bar")]')),
            2)
        self.assertEqual(
            len(tree.xpath('//node[hasclass("baz")]')),
            1)
        self.assertEqual(
            len(tree.xpath('//node[hasclass("foo")][not(hasclass("bar"))]')),
            1)
        self.assertEqual(
            len(tree.xpath('//node[hasclass("foo", "baz")]')),
            1)


class TestQWebRender(ViewCase):

    def test_render(self):
        view1 = self.View.create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <div><span>something</span></div>
                </t>
        """
        })
        view2 = self.View.create({
            'name': "dummy_ext",
            'type': 'qweb',
            'inherit_id': view1.id,
            'arch': """
                <xpath expr="//div" position="inside">
                    <span>another thing</span>
                </xpath>
            """
        })
        view3 = self.View.create({
            'name': "dummy_primary_ext",
            'type': 'qweb',
            'inherit_id': view1.id,
            'mode': 'primary',
            'arch': """
                <xpath expr="//div" position="inside">
                    <span>another primary thing</span>
                </xpath>
            """
        })

        # render view and child view with an id
        content1 = self.env['ir.qweb'].with_context(check_view_ids=[view1.id, view2.id])._render(view1.id)
        content2 = self.env['ir.qweb'].with_context(check_view_ids=[view1.id, view2.id])._render(view2.id)

        self.assertEqual(content1, content2)

        # render view and child view with an xmlid
        self.env.cr.execute("INSERT INTO ir_model_data(name, model, res_id, module)"
                            "VALUES ('dummy', 'ir.ui.view', %s, 'base')" % view1.id)
        self.env.cr.execute("INSERT INTO ir_model_data(name, model, res_id, module)"
                            "VALUES ('dummy_ext', 'ir.ui.view', %s, 'base')" % view2.id)

        content1 = self.env['ir.qweb'].with_context(check_view_ids=[view1.id, view2.id])._render('base.dummy')
        content2 = self.env['ir.qweb'].with_context(check_view_ids=[view1.id, view2.id])._render('base.dummy_ext')

        self.assertEqual(content1, content2)

        # render view and primary extension with an id
        content1 = self.env['ir.qweb'].with_context(check_view_ids=[view1.id, view2.id, view3.id])._render(view1.id)
        content3 = self.env['ir.qweb'].with_context(check_view_ids=[view1.id, view2.id, view3.id])._render(view3.id)

        self.assertNotEqual(content1, content3)

        # render view and primary extension with an xmlid
        self.env.cr.execute("INSERT INTO ir_model_data(name, model, res_id, module)"
                            "VALUES ('dummy_primary_ext', 'ir.ui.view', %s, 'base')" % view3.id)

        content1 = self.env['ir.qweb'].with_context(check_view_ids=[view1.id, view2.id, view3.id])._render('base.dummy')
        content3 = self.env['ir.qweb'].with_context(check_view_ids=[view1.id, view2.id, view3.id])._render('base.dummy_primary_ext')

        self.assertNotEqual(content1, content3)


class TestValidationTools(common.BaseCase):

    def test_get_expression_identities(self):
        self.assertEqual(
            view_validation.get_expression_field_names("context_today().strftime('%Y-%m-%d')"),
            set(),
        )
        self.assertEqual(
            view_validation.get_expression_field_names("field and field[0] or not field2"),
            {'field', 'field2'},
        )
        self.assertEqual(
            view_validation.get_expression_field_names("context_today().strftime('%Y-%m-%d') or field"),
            {'field'},
        )
        self.assertEqual(
            view_validation.get_expression_field_names("(datetime.datetime.combine(context_today(), datetime.time(x,y,z)).to_utc()).strftime('%Y-%m-%d %H:%M:%S')"),
            {'x', 'y', 'z'},
        )
        self.assertEqual(
            view_validation.get_expression_field_names("set(field).intersection([1, 2])"),
            {'field'},
        )


class TestAccessRights(TransactionCaseWithUserDemo):

    @common.users('demo')
    def test_access(self):
        # a user can not access directly a view
        with self.assertRaises(AccessError):
            self.env['ir.ui.view'].search([("model", '=', "res.partner"), ('type', '=', 'form')])

        # but can call view_get
        self.env['res.partner'].get_view(view_type='form')

        # unless he does not have access to the model
        with self.assertRaises(AccessError):
            self.env['ir.ui.view'].get_view(view_type='form')

@common.tagged('post_install', '-at_install', '-standard', 'migration')
class TestAllViews(common.TransactionCase):
    def test_views(self):
        views = self.env['ir.ui.view'].with_context(lang=None).search([])
        for index, view in enumerate(views):
            if index % 500 == 0:
                _logger.info('checked %s/%s views', index, len(views))
            with self.subTest(name=view.name):
                view._check_xml()

@common.tagged('post_install', '-at_install', '-standard', 'render_all_views')
class TestRenderAllViews(TransactionCaseWithUserDemo):

    @common.users('demo', 'admin')
    def test_render_all_views(self):
        env = self.env(context={'lang': 'en_US'})
        count = 0
        elapsed = 0
        for model in env.values():
            if not model._abstract and model.has_access('read'):
                with self.subTest(model=model):
                    times = []
                    for _ in range(5):
                        env.invalidate_all()
                        before = time.perf_counter()
                        model.get_view()
                        times.append(time.perf_counter() - before)
                    count += 1
                    elapsed += min(times)

        _logger.info('Rendered %d views as %s using (best of 5) %ss',
            count, self.env.user.name, elapsed)


@common.tagged('post_install', '-at_install', 'post_install_l10n')
class TestInvisibleField(TransactionCaseWithUserDemo):
    def test_uncommented_invisible_field(self):
        # NEVER add new name in this list ! The new addons must add comment for all always invisible field.
        only_log_modules = (
            'account',
            'account_3way_match',
            'account_accountant',
            'account_accountant_batch_payment',
            'account_asset',
            'account_asset_fleet',
            'account_auto_transfer',
            'account_avatax',
            'account_avatax_geolocalize',
            'account_avatax_sale',
            'account_base_import',
            'account_batch_payment',
            'account_budget',
            'account_check_printing',
            'account_consolidation',
            'account_debit_note',
            'account_disallowed_expenses',
            'account_edi',
            'account_edi_proxy_client',
            'account_edi_ubl_cii',
            'account_external_tax',
            'account_fleet',
            'account_followup',
            'account_intrastat',
            'account_invoice_extract',
            'account_online_synchronization',
            'account_payment',
            'account_peppol',
            'account_qr_code_emv',
            'account_reports',
            'account_saft_import',
            'account_sepa',
            'account_sepa_direct_debit',
            'account_winbooks_import',
            'analytic',
            'appointment',
            'approvals',
            'approvals_purchase_stock',
            'auth_signup',
            'auth_totp',
            'barcodes_gs1_nomenclature',
            'base_address_extended',
            'base_automation',
            'base_geolocalize',
            'base_import_module',
            'base_install_request',
            'base_setup',
            'base_vat',
            'calendar',
            'crm',
            'crm_helpdesk',
            'crm_iap_enrich',
            'crm_iap_mine',
            'data_cleaning',
            'data_merge',
            'data_recycle',
            'delivery',
            'delivery_dhl',
            'delivery_easypost',
            'delivery_fedex',
            'delivery_iot',
            'delivery_mondialrelay',
            'delivery_sendcloud',
            'delivery_shiprocket',
            'delivery_starshipit',
            'delivery_ups',
            'delivery_ups_rest',
            'delivery_usps',
            'digest',
            'documents',
            'documents_account',
            'documents_approvals',
            'documents_fleet',
            'documents_l10n_be_hr_payroll',
            'documents_project',
            'documents_project_sale',
            'documents_spreadsheet',
            'event',
            'event_booth',
            'event_booth_sale',
            'event_crm',
            'event_sale',
            'fleet',
            'frontdesk',
            'gamification',
            'helpdesk',
            'helpdesk_account',
            'helpdesk_fsm',
            'helpdesk_fsm_report',
            'helpdesk_repair',
            'helpdesk_sale',
            'helpdesk_sale_loyalty',
            'helpdesk_sale_timesheet',
            'helpdesk_stock',
            'helpdesk_stock_account',
            'helpdesk_timesheet',
            'hr',
            'hr_appraisal',
            'hr_appraisal_skills',
            'hr_appraisal_survey',
            'hr_attendance',
            'hr_contract',
            'hr_contract_salary',
            'hr_contract_salary_holidays',
            'hr_expense',
            'hr_expense_extract',
            'hr_fleet',
            'hr_gamification',
            'hr_holidays',
            'hr_holidays_attendance',
            'hr_hourly_cost',
            'hr_maintenance',
            'hr_payroll',
            'hr_payroll_account',
            'hr_payroll_expense',
            'hr_recruitment',
            'hr_recruitment_extract',
            'hr_recruitment_sign',
            'hr_recruitment_skills',
            'hr_recruitment_survey',
            'hr_referral',
            'hr_sign',
            'hr_skills',
            'hr_skills_slides',
            'hr_skills_survey',
            'hr_timesheet',
            'hr_work_entry',
            'hr_work_entry_holidays_enterprise',
            'iap',
            'im_livechat',
            'industry_fsm',
            'industry_fsm_report',
            'industry_fsm_sale',
            'industry_fsm_sale_report',
            'industry_fsm_stock',
            'iot',
            'knowledge',
            'l10n_ae_hr_payroll',
            'l10n_ar',
            'l10n_ar_edi',
            'l10n_ar_withholding',
            'l10n_au_hr_payroll',
            'l10n_au_hr_payroll_account',
            'l10n_be_codabox',
            'l10n_be_hr_contract_salary',
            'l10n_be_hr_payroll',
            'l10n_be_hr_payroll_dimona',
            'l10n_be_hr_payroll_fleet',
            'l10n_be_hr_payroll_sd_worx',
            'l10n_be_reports',
            'l10n_be_soda',
            'l10n_br',
            'l10n_br_avatax',
            'l10n_br_edi',
            'l10n_br_edi_stock',
            'l10n_ch_hr_payroll',
            'l10n_cl',
            'l10n_cl_edi',
            'l10n_cl_edi_exports',
            'l10n_cl_edi_stock',
            'l10n_cn',
            'l10n_co_dian',
            'l10n_co_edi',
            'l10n_cz_reports',
            'l10n_de_pos_cert',
            'l10n_ec',
            'l10n_ec_edi',
            'l10n_ec_edi_pos',
            'l10n_ec_edi_stock',
            'l10n_ec_sale',
            'l10n_eg_edi_eta',
            'l10n_eg_hr_payroll',
            'l10n_employment_hero',
            'l10n_es_edi_facturae',
            'l10n_es_edi_sii',
            'l10n_es_edi_tbai',
            'l10n_es_edi_tbai_pos',
            'l10n_es_reports',
            'l10n_eu_oss_reports',
            'l10n_fr_hr_holidays',
            'l10n_fr_hr_payroll',
            'l10n_fr_intrastat',
            'l10n_fr_pos_cert',
            'l10n_fr_reports',
            'l10n_gr_edi',
            'l10n_hk_hr_payroll',
            'l10n_hu_edi',
            'l10n_id_efaktur',
            'l10n_id_efaktur_coretax',
            'l10n_in_hr_payroll',
            'l10n_it_edi',
            'l10n_it_edi_doi',
            'l10n_it_edi_sale',
            'l10n_it_stock_ddt',
            'l10n_it_xml_export',
            'l10n_jo_edi',
            'l10n_jo_hr_payroll',
            'l10n_jp_zengin',
            'l10n_ke_edi_oscu',
            'l10n_ke_edi_oscu_mrp',
            'l10n_ke_edi_oscu_pos',
            'l10n_ke_edi_oscu_stock',
            'l10n_ke_edi_tremol',
            'l10n_ke_hr_payroll',
            'l10n_latam_check',
            'l10n_latam_invoice_document',
            'l10n_lu_hr_payroll',
            'l10n_lu_reports',
            'l10n_ma_hr_payroll',
            'l10n_mx',
            'l10n_mx_edi',
            'l10n_mx_edi_extended',
            'l10n_mx_edi_landing',
            'l10n_mx_edi_pos',
            'l10n_mx_edi_stock',
            'l10n_mx_hr_payroll',
            'l10n_mx_reports',
            'l10n_mx_xml_polizas',
            'l10n_my_edi',
            'l10n_my_edi_pos',
            'l10n_nl_reports',
            'l10n_nz_eft',
            'l10n_pe',
            'l10n_pe_edi',
            'l10n_pe_edi_stock',
            'l10n_pe_reports',
            'l10n_pe_reports_stock',
            'l10n_ph',
            'l10n_ph_check_printing',
            'l10n_pl_reports',
            'l10n_ro_edi_stock',
            'l10n_ro_edi_stock_batch',
            'l10n_ro_saft',
            'l10n_sa_edi',
            'l10n_sa_hr_payroll',
            'l10n_se',
            'l10n_se_sie4_import',
            'l10n_tr_nilvera_edispatch',
            'l10n_uk_bacs',
            'l10n_uk_reports',
            'l10n_uk_reports_cis',
            'l10n_us_hr_payroll',
            'l10n_us_hr_payroll_adp',
            'l10n_uy_edi',
            'loyalty',
            'lunch',
            'mail',
            'mail_bot_hr',
            'mail_group',
            'maintenance',
            'maintenance_worksheet',
            'marketing_automation',
            'marketing_automation_sms',
            'mass_mailing',
            'mass_mailing_crm',
            'mass_mailing_event',
            'mass_mailing_slides',
            'mass_mailing_sms',
            'membership',
            'mrp',
            'mrp_account',
            'mrp_account_enterprise',
            'mrp_landed_costs',
            'mrp_maintenance',
            'mrp_mps',
            'mrp_plm',
            'mrp_product_expiry',
            'mrp_subcontracting',
            'mrp_subcontracting_dropshipping',
            'mrp_workorder',
            'mrp_workorder_expiry',
            'mrp_workorder_iot',
            'onboarding',
            'partner_autocomplete',
            'partner_commission',
            'payment',
            'payment_adyen',
            'payment_authorize',
            'payment_custom',
            'payment_demo',
            'planning',
            'point_of_sale',
            'portal',
            'pos_enterprise',
            'pos_hr',
            'pos_iot',
            'pos_online_payment',
            'pos_restaurant',
            'pos_restaurant_appointment',
            'pos_self_order',
            'privacy_lookup',
            'product',
            'product_email_template',
            'product_expiry',
            'product_margin',
            'project',
            'project_enterprise',
            'project_timesheet_forecast',
            'project_timesheet_holidays',
            'project_todo',
            'purchase',
            'purchase_product_matrix',
            'purchase_requisition',
            'purchase_stock',
            'quality',
            'quality_control',
            'quality_control_iot',
            'quality_control_picking_batch',
            'quality_control_worksheet',
            'quality_iot',
            'quality_mrp',
            'quality_mrp_workorder',
            'rating',
            'repair',
            'resource',
            'room',
            'sale',
            'sale_amazon',
            'sale_crm',
            'sale_expense',
            'sale_external_tax',
            'sale_loyalty',
            'sale_management',
            'sale_margin',
            'sale_pdf_quote_builder',
            'sale_planning',
            'sale_product_matrix',
            'sale_project',
            'sale_purchase',
            'sale_renting',
            'sale_renting_crm',
            'sale_stock',
            'sale_stock_renting',
            'sale_subscription',
            'sale_timesheet',
            'sale_timesheet_enterprise',
            'sales_team',
            'sign',
            'sms',
            'snailmail',
            'snailmail_account',
            'social',
            'social_crm',
            'social_facebook',
            'social_instagram',
            'social_linkedin',
            'social_push_notifications',
            'social_twitter',
            'social_youtube',
            'spreadsheet_dashboard_edition',
            'spreadsheet_dashboard_sale_subscription',
            'stock',
            'stock_account',
            'stock_barcode',
            'stock_barcode_mrp',
            'stock_barcode_picking_batch',
            'stock_barcode_product_expiry',
            'stock_delivery',
            'stock_enterprise',
            'stock_intrastat',
            'stock_landed_costs',
            'stock_picking_batch',
            'survey',
            'test_testing_utilities',
            'timesheet_grid',
            'uom',
            'utm',
            'voip',
            'web',
            'web_studio',
            'website',
            'website_appointment',
            'website_blog',
            'website_crm_iap_reveal',
            'website_crm_partner_assign',
            'website_customer',
            'website_delivery_sendcloud',
            'website_event',
            'website_event_booth_exhibitor',
            'website_event_exhibitor',
            'website_event_social',
            'website_event_track',
            'website_event_track_gantt',
            'website_event_track_quiz',
            'website_event_track_social',
            'website_event_twitter_wall',
            'website_forum',
            'website_helpdesk_forum',
            'website_hr_recruitment',
            'website_knowledge',
            'website_livechat',
            'website_payment',
            'website_sale',
            'website_sale_loyalty',
            'website_sale_slides',
            'website_sale_stock',
            'website_slides',
            'website_slides_survey',
            'website_sms',
            'website_studio',
            'website_twitter_wall',
            'whatsapp',
            'whatsapp_payment',
            'worksheet',
        )

        modules_without_error = set(self.env['ir.module.module'].search([('state', '=', 'intalled'), ('name', 'in', only_log_modules)]).mapped('name'))
        module_log_views = defaultdict(list)
        module_error_views = defaultdict(lambda: defaultdict(list))
        uncommented_regexp = r'''(<field [^>]*invisible=['"](True|1)['"][^>]*>)[\s\t\n ]*(.*)'''
        views = self.env['ir.ui.view'].search([('type', 'in', ('list', 'form')), '|', ('arch_db', 'like', 'invisible=_True_'), ('arch_db', 'like', 'invisible=_1_')])
        for view in views.filtered('model_data_id'):
            module_name = view.model_data_id.module
            view_name = view.model_data_id.name
            for field, _val, comment in re.findall(uncommented_regexp, view.arch_db):
                if (not comment or not comment.startswith('<!--')):
                    if module_name in only_log_modules:
                        modules_without_error.discard(module_name)
                        module_log_views[module_name].append(view_name)
                        break
                    else:
                        module_error_views[module_name][view_name].append(field)

        msg = 'Please indicate why the always invisible fields are present in the view, or remove the field tag.'

        if module_log_views:
            msg_info = '\n'.join(f'Addons: {module!r}   Views: {names}' for module, names in module_log_views.items())
            _logger.info('%s\n%s', msg, msg_info)

        if module_error_views:
            error_lines = []
            for module, view_errors in module_error_views.items():
                error_lines.append(f"Addon: {module!r}")
                for view, fields in view_errors.items():
                    error_lines.extend([f"{' ' * 3}View: {view}\n{' ' * 6}Fields:"])
                    error_lines.extend(["\n".join(f"{' ' * 9}{field}" for field in fields)])
            _logger.error("%s\n%s", msg, "\n".join(error_lines))

        if modules_without_error:
            _logger.error('Please remove this module names from the white list of this current test: %r', sorted(modules_without_error))

class CompRegexTest(common.TransactionCase):
    def test_comp_regex(self):
        self.assertIsNone(re.search(ir_ui_view.COMP_REGEX, ""))
        self.assertIsNone(re.search(ir_ui_view.COMP_REGEX, "__comp__2"))
        self.assertIsNone(re.search(ir_ui_view.COMP_REGEX, "__comp___that"))
        self.assertIsNone(re.search(ir_ui_view.COMP_REGEX, "a__comp__"))

        self.assertIsNotNone(re.search(ir_ui_view.COMP_REGEX, "__comp__"))
        self.assertIsNotNone(re.search(ir_ui_view.COMP_REGEX, "__comp__ "))
        self.assertIsNotNone(re.search(ir_ui_view.COMP_REGEX, " __comp__ "))
        self.assertIsNotNone(re.search(ir_ui_view.COMP_REGEX, "__comp__.props"))
        self.assertIsNotNone(re.search(ir_ui_view.COMP_REGEX, "__comp__ .props"))
        self.assertIsNotNone(re.search(ir_ui_view.COMP_REGEX, "__comp__['props']"))
        self.assertIsNotNone(re.search(ir_ui_view.COMP_REGEX, "__comp__ ['props']"))
        self.assertIsNotNone(re.search(ir_ui_view.COMP_REGEX, "__comp__[\"props\"]"))
        self.assertIsNotNone(re.search(ir_ui_view.COMP_REGEX, "__comp__ [\"props\"]"))
        self.assertIsNotNone(re.search(ir_ui_view.COMP_REGEX, "    __comp__     [\"props\"]    "))
        self.assertIsNotNone(re.search(ir_ui_view.COMP_REGEX, "record ? __comp__ : false"))
        self.assertIsNotNone(re.search(ir_ui_view.COMP_REGEX, "!__comp__.props.resId"))
        self.assertIsNotNone(re.search(ir_ui_view.COMP_REGEX, "{{ __comp__ }}"))


@common.tagged('at_install', 'modifiers')
class ViewModifiers(ViewCase):

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_01_modifiers(self):
        def _test_modifiers(what, expected_vnames):
            if isinstance(what, dict):
                node = etree.Element('field', {k: str(v) for k, v in what.items()})
            else:
                node = etree.fromstring(what) if isinstance(what, str) else what
            modifiers = {attr: node.attrib[attr] for attr in node.attrib if attr in ir_ui_view.VIEW_MODIFIERS}
            vnames = set()
            for expr in modifiers.values():
                vnames |= view_validation.get_expression_field_names(expr) - {'id'}
            assert vnames == expected_vnames, f"{vnames!r} != {expected_vnames!r}"

        str_true = "True"

        _test_modifiers('<field name="a"/>', set())
        _test_modifiers('<field name="a" invisible="1"/>', set())
        _test_modifiers('<field name="a" readonly="1"/>', set())
        _test_modifiers('<field name="a" required="1"/>', set())
        _test_modifiers('<field name="a" invisible="0"/>', set())
        _test_modifiers('<field name="a" readonly="0"/>', set())
        _test_modifiers('<field name="a" required="0"/>', set())
        # TODO: Order is not guaranteed
        _test_modifiers('<field name="a" invisible="1" required="1"/>',
            set(),
        )
        _test_modifiers('<field name="a" invisible="1" required="0"/>',
            set(),
        )
        _test_modifiers('<field name="a" invisible="0" required="1"/>',
            set(),
        )
        _test_modifiers("""<field name="a" invisible="b == 'c'"/>""",
            {"b"},
        )
        _test_modifiers("""<field name="a" invisible="b == 'c'"/>""",
            {"b"},
        )
        _test_modifiers("""<field name="a" invisible="b == 'c'"/>""",
            {"b"},
        )
        _test_modifiers("""<field name="a" invisible="(b == 'c' or e == 'f')"/>""",
            {"b", "e"},
        )
        _test_modifiers("""<field name="a" invisible="b == 'c'"/>""",
            {"b"},
        )
        _test_modifiers("""<field name="a" invisible="user_id == uid"/>""",
            {"user_id"},
        )
        _test_modifiers("""<field name="a" invisible="(user_id == other_field)"/>""",
            {"user_id", "other_field"},
        )
        _test_modifiers("""<field name="a" invisible="a == parent.b"/>""",
            {"a", "parent.b"},
        )
        _test_modifiers("""<field name="a" invisible="a == context.get('b')"/>""",
            {"a"},
        )
        _test_modifiers("""<field name="a" invisible="a == context['b']"/>""",
            {"a"},
        )
        _test_modifiers("""<field name="a" invisible="company_id == allowed_company_ids[0]"/>""",
            {"company_id"},
        )
        _test_modifiers("""<field name="a" invisible="company_id == (field_1 or False)"/>""",
            {"company_id", "field_1"},
        )

        # fields in a list view
        tree = etree.fromstring('''
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
        ''')
        _test_modifiers(tree[0][0], set())
        _test_modifiers(tree[1], set())
        _test_modifiers(tree[2], set())
        _test_modifiers(tree[3], set())
        _test_modifiers(tree[4], {"b"})
        _test_modifiers(tree[5], {"b"})

        # The dictionary is supposed to be the result of fields_get().
        _test_modifiers({}, set())
        _test_modifiers({"invisible": str_true}, set())
        _test_modifiers({"invisible": False}, set())

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_03_modifier_attribute_is_boolean(self):
        arch = """
            <form string="View">
                <field name="model"/>
                <field name="name" readonly="%s"/>
            </form>
        """
        self.assertValid(arch % '1')
        self.assertValid(arch % '0')
        self.assertValid(arch % 'True')
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
        arch = self.View.with_context(foo=True).get_view(view.id)['arch']
        field_node = etree.fromstring(arch).xpath('//field[@name="name"]')[0]
        self.assertEqual(field_node.get('invisible'), "context.get('foo')")
        self.assertEqual(field_node.get('readonly'), "context.get('bar')")
        self.assertEqual(field_node.get('required'), "context.get('baz')")

    def test_05_modifier_attribute_priority(self):
        view = self.assertValid("""
            <form string="View">
                <field name="type" invisible="1"/>
                <field name="name" invisible="context.get('foo') and type == 'list'"/>
            </form>
        """)
        for type_value, context, expected in [
            ('list', {}, False),
            ('form', {}, False),
            ('list', {'foo': True}, True),
            ('form', {'foo': True}, False),
        ]:
            arch = self.View.with_context(**context).get_view(view.id)['arch']
            field_node = etree.fromstring(arch).xpath('//field[@name="name"]')[0]
            result = field_node.get('invisible')
            result = safe_eval.safe_eval(result, {'context': context, 'type': type_value})
            self.assertEqual(bool(result), expected, f"With context: {context}")

    @mute_logger('odoo.addons.base.models.ir_ui_view')
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

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_11_attrs_field(self):
        arch = """
            <form string="View">
                <field name="name"/>%s
                <field name="inherit_id"
                       readonly="model == 'ir.ui.view'"/>
            </form>
        """
        view = self.assertValid(arch % '<field name="model"/>')
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertFalse(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))

        view = self.assertValid(arch % '')
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))

    @mute_logger('odoo.addons.base.models.ir_ui_view')
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

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_13_attrs_states_invisible_to_modifier(self):
        view = self.View.create({
            'name': 'foo',
            'model': 'ir.module.module',
            'arch': """
                <form string="View">
                    <group invisible="state != 'finished'">
                        <field name="category_id" invisible="not state" />
                        <field name="state" invisible="name not in ['qweb-pdf', 'qweb-html', 'qweb-text']"/>
                        <field name="name" invisible="name != 'bidule' and category_id != uid and state not in ('draf', 'finished')"/>
                    </group>
                </form>
            """,
        })
        arch = self.env['ir.module.module'].get_view(view_id=view.id)['arch']
        tree = etree.fromstring(arch)

        invisible = tree.xpath('//group')[0].get('invisible')
        self.assertEqual(invisible, "state != 'finished'")

        invisible = tree.xpath('//field[@name="category_id"]')[0].get('invisible')
        self.assertEqual(invisible, "not state")

        invisible = tree.xpath('//field[@name="state"]')[0].get('invisible')
        self.assertEqual(invisible, "name not in ['qweb-pdf', 'qweb-html', 'qweb-text']")

        invisible = tree.xpath('//field[@name="name"]')[0].get('invisible')
        self.assertEqual(invisible, "name != 'bidule' and category_id != uid and state not in ('draf', 'finished')")

    @mute_logger('odoo.addons.base.models.ir_ui_view')
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
        view = self.assertValid(arch % ('', '<field name="model"/>'))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertFalse(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))

        view = self.assertValid(arch % ('', ''))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))

        view = self.assertValid(arch % ('<field name="model"/>', ''))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))

    @mute_logger('odoo.addons.base.models.ir_ui_view')
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
        view = self.assertValid(arch % ('<field name="model"/>', ''))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertFalse(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))

        view = self.assertValid(arch % ('', ''))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))
        self.assertFalse(etree.fromstring(view_arch).xpath('//field/form/field[@name="model"][@invisible][@readonly]'))

        view = self.assertValid(arch % ('', '<field name="model"/>'))
        view_arch = view.get_views([(view.id, 'form')])['views']['form']['arch']
        self.assertTrue(etree.fromstring(view_arch).xpath('//field[@name="model"][@invisible][@readonly]'))
        self.assertFalse(etree.fromstring(view_arch).xpath('//field/form/field[@name="model"][@invisible][@readonly]'))

    def test_16_attrs_groups_behavior(self):
        view = self.View.create({
            'name': 'foo',
            'model': 'res.partner',
            'arch': """
                <form>
                    <field name="name"/>
                    <field name="company_id" groups="base.group_system"/>
                    <div id="foo"/>
                    <div id="bar" groups="base.group_system"/>
                </form>
            """,
        })
        user_demo = self.user_demo
        # Make sure demo doesn't have the base.group_system
        self.assertFalse(user_demo.has_group('base.group_system'))
        arch = self.env['res.partner'].with_user(user_demo).get_view(view_id=view.id)['arch']
        tree = etree.fromstring(arch)
        self.assertTrue(tree.xpath('//field[@name="name"]'))
        self.assertFalse(tree.xpath('//field[@name="company_id"]'))
        self.assertTrue(tree.xpath('//div[@id="foo"]'))
        self.assertFalse(tree.xpath('//div[@id="bar"]'))

        user_admin = self.env.ref('base.user_admin')
        # Make sure admin has the base.group_system
        self.assertTrue(user_admin.has_group('base.group_system'))
        arch = self.env['res.partner'].with_user(user_admin).get_view(view_id=view.id)['arch']
        tree = etree.fromstring(arch)
        self.assertTrue(tree.xpath('//field[@name="name"]'))
        self.assertTrue(tree.xpath('//field[@name="company_id"]'))
        self.assertTrue(tree.xpath('//div[@id="foo"]'))
        self.assertTrue(tree.xpath('//div[@id="bar"]'))

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_17_attrs_groups_validation(self):
        test_group = self.env['res.groups'].create({'name': 'test_group'})
        self.env['ir.model.data'].create({
            'module': 'base',
            'name': 'test_group',
            'model': 'res.groups',
            'res_id': test_group.id,
        })

        def validate(arch, add_field_with_groups=False, parent=False, model='ir.ui.view'):
            parent = 'parent.' if parent else ''
            view = self.assertValid(arch % {'attrs': f"""decoration-info="{parent}name == 'foo'" """}, model=model)
            result = self.env[model]._get_view_cache(view_id=view.id)
            tree = etree.fromstring(result['arch'])
            group_definitions = self.env['res.groups']._get_group_definitions()

            if add_field_with_groups is False:
                nodes = tree.xpath('//field[@name="name"][@invisible][@readonly]')
                self.assertEqual(len(nodes), 0, arch)
            else:
                nodes = tree.xpath("//field[@name='name'][@invisible='True'][@readonly='True']")
                self.assertEqual(len(nodes), 1, arch)
                groups_key = nodes[0].get('__groups_key__')
                group_repr = str(group_definitions.from_key(groups_key)) if groups_key else ''
                self.assertEqual(group_repr, add_field_with_groups, arch)

        arch = """
            <form string="View">
                <field name="name"/>
                <field name="inherit_id" %(attrs)s/>
            </form>
        """
        self.assertValid(arch % {'attrs': """invisible="name == 'foo'" """})
        self.assertValid(arch % {'attrs': """domain="[('name', '!=', name)]" """})
        self.assertValid(arch % {'attrs': """context="{'default_name': name}" """})
        self.assertValid(arch % {'attrs': """decoration-info="name == 'foo'" """})

        # add missing field with needed groups
        validate("""
            <form string="View">
                <field name="name"/>
                <field name="inherit_id" %(attrs)s/>
            </form>
        """, add_field_with_groups=False)

        # add missing field
        validate("""
            <form string="View">
                <field name="inherit_id" %(attrs)s/>
            </form>
        """, add_field_with_groups='')

        # add the field for all combinations
        validate("""
            <form string="View">
                <field name="name" groups="base.group_public"/>
                <field name="inherit_id" %(attrs)s/>
            </form>
        """, add_field_with_groups='')

        # don't add field because the inherit_id is not accessible by any user (group_user != group_portal)
        validate("""
            <form string="View">
                <group groups="base.group_user">
                    <field name="name" groups="base.group_public"/>
                    <field name="inherit_id" groups="base.group_portal" %(attrs)s/>
                </group>
            </form>
        """, add_field_with_groups=False)

        # add missing field with needed groups
        validate("""
            <form string="View">
                <field name="inherit_id" groups="base.test_group" %(attrs)s/>
            </form>
        """, add_field_with_groups="'base.test_group'")

        # add missing field because the existing field group does not match
        validate("""
            <form string="View">
                <field name="name" groups="base.test_group"/>
                <field name="inherit_id" %(attrs)s/>
            </form>
        """, add_field_with_groups='')

        # Add missing field because the field name has defined groups.
        validate("""
            <form string="View">
                <field name="name" groups="base.test_group"/>
                <field name="inherit_children_ids">
                    <list editable="bottom">
                        <field name="inherit_id" %(attrs)s/>
                    </list>
                </field>
            </form>
        """, add_field_with_groups='', parent=True)

        # Don't need to add field if the dependent field is in the same groups
        validate("""
            <form string="View">
                <field name="name" groups="base.test_group"/>
                <field name="inherit_children_ids">
                    <list editable="bottom">
                        <field name="inherit_id" groups="base.test_group" %(attrs)s/>
                    </list>
                </field>
            </form>
        """, add_field_with_groups=False, parent=True)

        validate("""
            <form string="View">
                <field name="name"/>
                <field name="inherit_children_ids">
                    <list editable="bottom">
                        <field name="inherit_id" groups="base.test_group" %(attrs)s/>
                    </list>
                </field>
            </form>
        """, add_field_with_groups=False, parent=True)

        validate("""
            <form string="View">
                <field name="name"/>
                <field name="inherit_id" %(attrs)s groups="base.test_group"/>
            </form>
        """, add_field_with_groups=False)

        validate("""
            <form string="View">
                <field name="name" groups="base.test_group"/>
                <field name="inherit_id" groups="base.test_group" %(attrs)s/>
            </form>
        """, add_field_with_groups=False)

        validate("""
            <form string="View">
                <field name="name" groups="base.group_portal"/>
                <field name="name" groups="base.test_group"/>
                <field name="inherit_id" groups="base.test_group" %(attrs)s/>
            </form>
        """, add_field_with_groups=False)

        # Add the missing field only for 'base.group_multi_company' because the
        # other field is valid.
        validate("""
            <form string="View">
                <field name="name" groups="base.test_group"/>
                <field name="inherit_id" groups="base.test_group" %(attrs)s/>
                <field name="inherit_id" groups="base.group_multi_company" %(attrs)s/>
            </form>
        """, add_field_with_groups="'base.group_multi_company'")

        # All situations have the field name, not need to add one as invisible.
        validate("""
            <form string="View">
                <field name="name" groups="base.test_group"/>
                <field name="name" groups="base.group_portal"/>
                <field name="inherit_id" groups="base.test_group" %(attrs)s/>
                <field name="inherit_id" groups="base.group_portal" %(attrs)s/>
            </form>
        """, add_field_with_groups=False)

        validate("""
            <form string="View">
                <field name="name" groups="base.group_portal,base.test_group"/>
                <field name="inherit_id" groups="base.test_group" %(attrs)s/>
            </form>
        """, add_field_with_groups=False)

        # add the missing field to have 'name' when inherit_id is present in the view.
        validate("""
            <form string="View">
                <field name="name" groups="base.test_group"/>
                <field name="inherit_id" groups="base.group_multi_company,base.test_group" %(attrs)s/>
            </form>
        """, add_field_with_groups="'base.group_multi_company' | 'base.test_group'")

        # Should not add the field because when 'inherit_id' is present, 'name' is present
        validate("""
            <form string="View">
                <field name="name" groups="base.test_group"/>
                <div groups="base.group_multi_company,base.group_system">
                    <field name="inherit_id" groups="base.test_group" %(attrs)s/>
                </div>
            </form>
        """, add_field_with_groups=False)

        # The view has base.group_system, implied base.group_erp_manager
        validate("""
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="inherit_id" groups="base.group_erp_manager" %(attrs)s/>
            </form>
        """, add_field_with_groups=False)

        # don't add the field because the field 'name' is already present
        # when the view have 'base.group_erp_manager' in access rigths.
        validate("""
            <form string="View">
                <field name="name" groups="base.group_erp_manager"/>
                <field name="inherit_children_ids">
                    <list editable="bottom">
                        <field name="inherit_id" groups="base.group_multi_company" %(attrs)s/>
                    </list>
                </field>
            </form>
        """, add_field_with_groups=False, parent=True)

        # add missing field with the same group of the needed
        validate("""
            <form string="View">
                <field name="name" groups="base.test_group"/>
                <field name="inherit_id" groups="base.group_multi_company" %(attrs)s/>
            </form>
        """, add_field_with_groups="'base.group_multi_company'")

        validate("""
            <form string="View">
                <field name="name" groups="base.test_group"/>
                <field name="inherit_children_ids">
                    <list editable="bottom">
                        <field name="inherit_id" groups="base.group_multi_company" %(attrs)s/>
                    </list>
                </field>
            </form>
        """, add_field_with_groups="'base.group_multi_company'", parent=True)

        validate("""
            <form string="View">
                <group groups="base.test_group">
                    <field name="name"/>
                </group>
                <field name="inherit_id" %(attrs)s/>
            </form>
        """, add_field_with_groups='')

        validate("""
            <form string="View">
                <group groups="base.test_group">
                    <field name="name"/>
                    <field name="inherit_id" %(attrs)s/>
                </group>
            </form>
        """, add_field_with_groups=False)

        validate("""
            <form string="View">
                <group groups="base.test_group">
                    <field name="name"/>
                    <field name="inherit_id" %(attrs)s groups="base.group_multi_currency,base.group_multi_company"/>
                </group>
            </form>
        """, add_field_with_groups=False)

        validate("""
            <form string="View">
                <group groups="base.test_group">
                    <field name="name"/>
                </group>
                <group groups="base.test_group">
                    <field name="inherit_id" %(attrs)s/>
                </group>
            </form>
        """, add_field_with_groups=False)

        # view access right has base.group_system implied base.group_erp_manager
        validate("""
            <form string="View">
                <group groups="base.group_erp_manager">
                    <field name="name"/>
                </group>
                <group groups="base.test_group">
                    <field name="inherit_id" %(attrs)s/>
                </group>
            </form>
        """, add_field_with_groups=False)

        validate("""
            <form string="View">
                <group groups="base.test_group">
                    <field name="name"/>
                </group>
                <group groups="base.group_multi_company">
                    <field name="inherit_id" %(attrs)s/>
                </group>
            </form>
        """, add_field_with_groups="'base.group_multi_company'")

        validate("""
            <form string="View">
                <field name="name" groups="base.test_group"/>
                <field name="inherit_children_ids" groups="base.test_group">
                    <list editable="bottom">
                        <field name="inherit_id" %(attrs)s/>
                    </list>
                </field>
            </form>
        """, add_field_with_groups=False, parent=True)

        validate("""
            <form string="View">
                <field name="name" groups="base.group_erp_manager"/>
                <field name="inherit_children_ids" groups="base.test_group">
                    <list editable="bottom">
                        <field name="inherit_id" %(attrs)s/>
                    </list>
                </field>
            </form>
        """, add_field_with_groups=False, parent=True)

        validate("""
            <form string="View">
                <field name="name" groups="base.test_group"/>
                <field name="inherit_children_ids" groups="base.group_multi_company">
                    <list editable="bottom">
                        <field name="inherit_id" %(attrs)s/>
                    </list>
                </field>
            </form>
        """, add_field_with_groups="'base.group_multi_company'", parent=True)

        validate("""
            <form string="View">
                <field name="name" groups="!base.test_group"/>
                <field name="inherit_id" %(attrs)s/>
            </form>
        """, add_field_with_groups='')

        validate("""
            <form string="View">
                <field name="name"/>
                <field name="inherit_id" groups="!base.test_group" %(attrs)s/>
            </form>
        """, add_field_with_groups=False)

        validate("""
            <form string="View">
                <field name="name" groups="!base.test_group"/>
                <field name="name" groups="base.test_group"/>
                <field name="inherit_id" groups="base.test_group" %(attrs)s/>
            </form>
        """, add_field_with_groups=False)

        validate("""
            <form string="View">
                <field name="name" groups="!base.test_group"/>
                <field name="name" groups="base.test_group"/>
                <field name="inherit_id" groups="!base.test_group" %(attrs)s/>
            </form>
        """, add_field_with_groups=False)

        validate("""
            <form string="View">
                <field name="name" groups="!base.test_group"/>
                <field name="name" groups="base.test_group"/>
                <field name="inherit_id" groups="base.group_portal" %(attrs)s/>
            </form>
        """, add_field_with_groups=False)

        # Add field because the field 'name' can be hide from the other
        # negative group
        validate("""
            <form string="View">
                <field name="name" groups="!base.group_multi_company,!base.test_group"/>
                <field name="inherit_id" groups="!base.group_multi_company" %(attrs)s/>
            </form>
        """, add_field_with_groups="~'base.group_multi_company'")

        # don't need to add field with an additional the negative group
        validate("""
            <form string="View">
                <field name="name" groups="!base.group_multi_company"/>
                <field name="inherit_id" groups="!base.group_multi_company,!base.test_group" %(attrs)s/>
            </form>
        """, add_field_with_groups=False)

        # add field with the negative mandatory group (the group is added in order
        # to only be present in the view when it is needed.)
        validate("""
            <form string="View">
                <field name="name" groups="!base.group_user"/>
                <field name="inherit_id" groups="!base.group_multi_company" %(attrs)s/>
            </form>
        """, add_field_with_groups="~'base.group_multi_company'")

        # fail because the access rights is group_system, no body can see the inherit_id
        # # don't need to add field, the negative group is a subset of the mandatory group
        validate("""
            <form string="View">
                <field name="name" groups="!base.test_group"/>
                <field name="inherit_id" groups="!base.group_user" %(attrs)s/>
            </form>
        """, add_field_with_groups=False)

        # add missing field with the mandatory group. The field present in view has a
        # restricted group opposing the desired visibility.
        validate("""
            <form string="View">
                <group groups="base.group_multi_company">
                    <field name="name" groups="!base.test_group"/>
                </group>
                <group groups="base.group_multi_company">
                    <field name="inherit_id" %(attrs)s/>
                </group>
            </form>
        """, add_field_with_groups="'base.group_multi_company'")

        # add missing field with the mandatory group. The field present in view has a
        # restricted (negative) group opposing the desired visibility.
        validate("""
            <form string="View">
                <field name="name" groups="base.group_multi_company"/>
                <field name="inherit_id" groups="!base.group_multi_company" %(attrs)s/>
            </form>
        """, add_field_with_groups="~'base.group_multi_company'")

        # don't need to add field (because we can see all time: !base.test_group <> base.test_group).
        validate("""
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
        """, add_field_with_groups=False)

        # No missing combination because '!base.test_group' | 'base.test_group' => *
        validate("""
            <form string="View">
                <field name="name" groups="!base.test_group"/>
                <field name="name" groups="base.test_group"/>
                <field name="inherit_id" %(attrs)s groups="base.group_multi_company"/>
            </form>
        """, add_field_with_groups=False)

        # No missing combination because '!base.test_group' | 'base.test_group' => *
        validate("""
            <form string="View">
                <field name="name" groups="base.group_multi_company"/>
                <field name="name" groups="!base.test_group"/>
                <field name="name" groups="base.test_group"/>
                <field name="inherit_id" %(attrs)s groups="base.group_multi_company"/>
                <field name="inherit_id" %(attrs)s groups="base.test_group"/>
                <field name="inherit_id" %(attrs)s groups="!base.test_group"/>
                <field name="inherit_id" %(attrs)s groups="base.group_public"/>
            </form>
        """, add_field_with_groups=False)

    def test_18_test_missing_group(self):
        group_a = self.env['res.groups'].create({'name': 'test_a'})
        data = self.env["ir.model.data"].create({
            'module': 'base',
            'name': 'group_test_a',
            'model': 'res.groups',
            'res_id': group_a.id,
        })

        view = self.View.create({
            'name': 'foo',
            'model': 'res.partner',
            'arch': """
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
        })

        data.unlink()
        group_a.unlink()

        user_demo = self.user_demo
        # Make sure demo doesn't have the base.group_system
        self.assertFalse(user_demo.has_group('base.group_system'))
        arch = self.env['res.partner'].with_user(user_demo).get_view(view_id=view.id)['arch']
        tree = etree.fromstring(arch)
        self.assertTrue(tree.xpath('//div[@id="foo"]'))
        self.assertTrue(tree.xpath('//div[@id="bar"]'))
        self.assertFalse(tree.xpath('//div[@id="stuff"]'))

        user_admin = self.env.ref('base.user_admin')
        # Make sure admin has the base.group_system
        self.assertTrue(user_admin.has_group('base.group_system'))
        arch = self.env['res.partner'].with_user(user_admin).get_view(view_id=view.id)['arch']
        tree = etree.fromstring(arch)
        self.assertFalse(tree.xpath('//div[@id="foo"]'))
        self.assertTrue(tree.xpath('//div[@id="bar"]'))
        self.assertFalse(tree.xpath('//div[@id="stuff"]'))

    def test_create_inherit_view_with_xpath_without_expr(self):
        """Test that creating inherited view containing <xpath> node without the 'expr' attribute."""

        parent_view = self.env.ref('base.view_partner_form')
        inherit_arch = """
            <xpath position="replace">
                <field name="name"/>
            </xpath>
        """

        with self.assertRaises(ValidationError):
            self.env['ir.ui.view'].create({
                'name': 'test.xpath.without.expr',
                'inherit_id': parent_view.id,
                'arch': inherit_arch,
            })
