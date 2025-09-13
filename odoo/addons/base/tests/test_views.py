# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import ast
import json
import logging
import re
import time

from functools import partial

from lxml import etree
from lxml.builder import E
from psycopg2 import IntegrityError
from psycopg2.extras import Json

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import common, tagged
from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.tools import get_cache_key_counter, mute_logger, view_validation, safe_eval
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

    def assertValid(self, arch, name='valid view', inherit_id=False):
        return self.View.create({
            'name': name,
            'model': 'ir.ui.view',
            'inherit_id': inherit_id,
            'arch': arch,
        })

    def assertInvalid(self, arch, expected_message=None, name='invalid view', inherit_id=False):
        with mute_logger('odoo.addons.base.models.ir_ui_view'):
            with self.assertRaises(ValidationError) as catcher:
                with self.cr.savepoint():
                    self.View.create({
                        'name': name,
                        'model': 'ir.ui.view',
                        'inherit_id': inherit_id,
                        'arch': arch,
                    })
        message = str(catcher.exception.args[0])
        self.assertEqual(catcher.exception.context['name'], name)
        if expected_message:
            self.assertIn(expected_message, message)
        else:
            _logger.warning(message)

    def assertWarning(self, arch, expected_message=None, name='invalid view'):
        with self.assertLogs('odoo.addons.base.models.ir_ui_view', level="WARNING") as log_catcher:
            self.View.create({
                'name': name,
                'model': 'ir.ui.view',
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

        self.b = self.makeView('B', arch=self.arch_for("B", 'tree'))
        self.makeView('B1', self.b.id, arch=self.arch_for("B1", 'tree', parent=self.b))
        self.c = self.makeView('C', arch=self.arch_for("C", 'tree'))
        self.c.write({'priority': 1})

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

        default_tree = self.View.default_view(model=self.model, view_type='tree')
        self.assertEqual(default_tree, self.view_ids['C'].id)

    def test_no_default_view(self):
        self.assertFalse(self.View.default_view(model='no_model.exist', view_type='form'))
        self.assertFalse(self.View.default_view(model=self.model, view_type='graph'))

    def test_no_recursion(self):
        r1 = self.makeView('R1')
        with self.assertRaises(ValidationError), self.cr.savepoint():
            r1.write({'inherit_id': r1.id})

        r2 = self.makeView('R2', r1.id)
        r3 = self.makeView('R3', r2.id)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            r2.write({'inherit_id': r3.id})

        with self.assertRaises(ValidationError), self.cr.savepoint():
            r1.write({'inherit_id': r3.id})

        with self.assertRaises(ValidationError), self.cr.savepoint():
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

        with self.assertQueryCount(7):
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

        with self.assertQueryCount(6):
            self.assertValid("""
                <field name="name" position="replace"/>
            """, inherit_id=base_view.id)
        self.assertEqual(counter.hit, hit + 2)
        self.assertEqual(counter.miss, miss + 2)

    def test_view_validate_attrs_groups_query_count(self):
        _, _, counter = get_cache_key_counter(self.env['ir.model.data']._xmlid_lookup, 'base.group_system')
        hit, miss = counter.hit, counter.miss

        with self.assertQueryCount(4):
            base_view = self.assertValid("""
                <form string="View">
                    <field name="name" groups="base.group_system"/>
                    <field name="priority" groups="base.group_system"/>
                    <field name="inherit_id" groups="base.group_system"/>
                </form>
            """)
        self.assertEqual(counter.hit, hit)
        self.assertEqual(counter.miss, miss + 1)

        with self.assertQueryCount(4):
            self.assertValid("""
                <field name="name" position="replace">
                    <field name="key" groups="base.group_system"/>
                </field>
            """, inherit_id=base_view.id)
        self.assertEqual(counter.hit, hit + 1)
        self.assertEqual(counter.miss, miss + 1)


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


class TestApplyInheritedArchs(ViewCase):
    """ Applies a sequence of modificator archs to a base view
    """


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
                <item><span t-call="foo"/></item>
            </root>""",
        })

        arch_string = view.with_context(inherit_branding=True).get_combined_arch()
        arch = etree.fromstring(arch_string)
        self.View.distribute_branding(arch)

        self.assertEqual(arch, E.root(E.item(E.span({'t-call': "foo"}))))

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
            kw['arch_db'] = Json({'en_US': arch_db}) if self.env.lang == 'en_US' else Json({'en_US': arch_db, self.env.lang: arch_db})

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
                        <tree string="view">
                          <field name="url"/>
                        </tree>
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

    @mute_logger('odoo.addons.base.models.ir_ui_view')
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

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_invalid_subfield(self):
        arch = """
            <form string="View">
                <field name="name"/>
                <field name="inherit_children_ids">
                    <tree name="Children">
                        <field name="name"/>
                        <field name="not_a_field"/>
                    </tree>
                </field>
            </form>
        """
        self.assertInvalid(
            arch,
            '''Field "not_a_field" does not exist in model "ir.ui.view"''',
        )

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_context_in_view(self):
        arch = """
            <form string="View">
                <field name="name"/>%s
                <field name="inherit_id" context="{'stuff': model}"/>
            </form>
        """
        self.assertValid(arch % '<field name="model"/>')
        self.assertInvalid(
            arch % '',
            """Field 'model' used in context ({'stuff': model}) must be present in view but is missing.""",
        )

    @mute_logger('odoo.addons.base.models.ir_ui_view')
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
        self.assertValid(arch % ('', '<field name="model"/>'))
        self.assertInvalid(
            arch % ('', ''),
            """Field 'model' used in context ({'stuff': model}) must be present in view but is missing.""",
        )
        self.assertInvalid(
            arch % ('<field name="model"/>', ''),
            """Field 'model' used in context ({'stuff': model}) must be present in view but is missing.""",
        )

    @mute_logger('odoo.addons.base.models.ir_ui_view')
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
        self.assertValid(arch % ('<field name="model"/>', ''))
        self.assertInvalid(
            arch % ('', ''),
            """Field 'model' used in context ({'stuff': parent.model}) must be present in view but is missing.""",
        )
        self.assertInvalid(
            arch % ('', '<field name="model"/>'),
            """Field 'model' used in context ({'stuff': parent.model}) must be present in view but is missing.""",
        )

    @mute_logger('odoo.addons.base.models.ir_ui_view')
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
                </field>
            </form>
        """
        self.assertValid(arch % ('<field name="model"/>', '', ''))
        self.assertInvalid(
            arch % ('', '', ''),
            """Field 'model' used in context ({'stuff': parent.parent.model}) must be present in view but is missing.""",
        )
        self.assertInvalid(
            arch % ('', '<field name="model"/>', ''),
            """Field 'model' used in context ({'stuff': parent.parent.model}) must be present in view but is missing.""",
        )
        self.assertInvalid(
            arch % ('', '', '<field name="model"/>'),
            """Field 'model' used in context ({'stuff': parent.parent.model}) must be present in view but is missing.""",
        )

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_domain_id_case(self):
        # id is read by default and should be usable in domains
        self.assertValid("""
            <form string="View">
                <field name="inherit_id" domain="[('id', '=', False)]"/>
            </form>
        """)

    @mute_logger('odoo.addons.base.models.ir_ui_view')
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
        # self.assertInvalid(arch % ('<field name="name"/><field name="type"/>', "'tata' if name else 'tutu'", 'type'), 'xxxx')
        self.assertInvalid(
            arch % ('', '1', '0 if name else 1'),
            """Field 'name' used in domain of <field name="inherit_id"> ([(1, '=', 0 if name else 1)]) must be present in view but is missing""",
        )

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_domain_in_view(self):
        arch = """
            <form string="View">
                <field name="name"/>%s
                <field name="inherit_id" domain="[('model', '=', model)]"/>
            </form>
        """
        self.assertValid(arch % '<field name="model"/>')
        self.assertInvalid(
            arch % '',
            """Field 'model' used in domain of <field name="inherit_id"> ([('model', '=', model)]) must be present in view but is missing.""",
        )

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
            '''Unsearchable field 'xml_id' in path 'xml_id' in domain of <field name="inherit_id"> ([('xml_id', '=', 'test')])''',
        )

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_domain_field_no_comodel(self):
        self.assertInvalid("""
            <form string="View">
                <field name="name" domain="[('test', '=', 'test')]"/>
            </form>
        """, "Domain on non-relational field \"name\" makes no sense (domain:[('test', '=', 'test')])")

    @mute_logger('odoo.addons.base.models.ir_ui_view')
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
        self.assertInvalid(
            arch % ('', ''),
            """Field 'model' used in domain of <field name="inherit_id"> ([('model', '=', model)]) must be present in view but is missing.""",
        )
        self.assertInvalid(
            arch % ('<field name="model"/>', ''),
            """Field 'model' used in domain of <field name="inherit_id"> ([('model', '=', model)]) must be present in view but is missing.""",
        )

    @mute_logger('odoo.addons.base.models.ir_ui_view')
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
        self.assertValid(arch % ('<field name="model"/>', '', ''))
        self.assertValid(arch % ('', '', '<field name="model"/>'))
        self.assertInvalid(
            arch % ('', '', ''),
            """Field 'model' used in domain of <field name="inherit_id"> ([('model', '=', parent.model)]) must be present in view but is missing.""",
        )
        self.assertInvalid(
            arch % ('', '<field name="model"/>', ''),
            """Field 'model' used in domain of <field name="inherit_id"> ([('model', '=', parent.model)]) must be present in view but is missing.""",
        )

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_domain_on_field_in_view(self):
        field = self.env['ir.ui.view']._fields['inherit_id']
        self.patch(field, 'domain', "[('model', '=', model)]")

        arch = """
            <form string="View">
                <field name="name"/>%s
                <field name="inherit_id"/>
            </form>
        """
        self.assertValid(arch % '<field name="model"/>')
        self.assertInvalid(
            arch % '',
            """Field 'model' used in domain of python field 'inherit_id' ([('model', '=', model)]) must be present in view but is missing.""",
        )

    @mute_logger('odoo.addons.base.models.ir_ui_view')
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
        self.assertValid(arch % ('', '<field name="model"/>'))
        self.assertInvalid(
            arch % ('', ''),
            """Field 'model' used in domain of python field 'inherit_id' ([('model', '=', model)]) must be present in view but is missing.""",
        )
        self.assertInvalid(
            arch % ('<field name="model"/>', ''),
            """Field 'model' used in domain of python field 'inherit_id' ([('model', '=', model)]) must be present in view but is missing.""",
        )

    @mute_logger('odoo.addons.base.models.ir_ui_view')
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
        self.assertValid(arch % ('<field name="model"/>', ''))
        self.assertInvalid(
            arch % ('', ''),
            """Field 'model' used in domain of python field 'inherit_id' ([('model', '=', parent.model)]) must be present in view but is missing.""",
        )
        self.assertInvalid(
            arch % ('', '<field name="model"/>'),
            """Field 'model' used in domain of python field 'inherit_id' ([('model', '=', parent.model)]) must be present in view but is missing.""",
        )

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_domain_on_field_in_noneditable_subview(self):
        field = self.env['ir.ui.view']._fields['inherit_id']
        self.patch(field, 'domain', "[('model', '=', model)]")

        arch = """
            <form string="View">
                <field name="name"/>
                <field name="inherit_children_ids">
                    <tree string="Children"%s>
                        <field name="name"/>
                        <field name="inherit_id"/>
                    </tree>
                </field>
            </form>
        """
        self.assertValid(arch % '')
        self.assertInvalid(
            arch % ' editable="bottom"',
            """Field 'model' used in domain of python field 'inherit_id' ([('model', '=', model)]) must be present in view but is missing.""",
        )

    @mute_logger('odoo.addons.base.models.ir_ui_view')
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

    @mute_logger('odoo.addons.base.models.ir_ui_view')
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
        self.assertValid(arch % ' readonly="1"')
        self.assertInvalid(
            arch % '',
            """Field 'model' used in domain of python field 'inherit_id' ([('model', '=', model)]) must be present in view but is missing.""",
        )

    @mute_logger('odoo.addons.base.models.ir_ui_view')
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

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_group_by_in_filter(self):
        arch = """
            <search string="Search">
                <filter string="Date" name="month" domain="[]" context="{'group_by':'%s'}"/>
            </search>
        """
        self.assertValid(arch % 'name')
        self.assertInvalid(
            arch % 'invalid_field',
            """Unknown field "invalid_field" in "group_by" value in context="{'group_by':'invalid_field'}""",
        )

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_domain_invalid_in_filter(self):
        # invalid domain: it should be a list of tuples
        self.assertInvalid(
            """ <search string="Search">
                    <filter string="Dummy" name="draft" domain="['name', '=', 'dummy']"/>
                </search>
            """,
            '''Invalid domain of <filter name="draft">: "['name', '=', 'dummy']"''',
        )

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_searchpanel(self):
        arch = """
            <search>
                %s
                <searchpanel>
                    %s
                    <field name="groups_id" select="multi" domain="[('%s', '=', %s)]" enable_counters="1"/>
                </searchpanel>
            </search>
        """
        self.assertValid(arch % ('', '<field name="inherit_id"/>', 'view_access', 'inherit_id'))
        self.assertInvalid(
            arch % ('<field name="inherit_id"/>', '', 'view_access', 'inherit_id'),
            """Field 'inherit_id' used in domain of <field name="groups_id"> ([('view_access', '=', inherit_id)]) must be present in view but is missing.""",
        )
        self.assertInvalid(
            arch % ('', '<field name="inherit_id"/>', 'view_access', 'view_access'),
            """Field 'view_access' used in domain of <field name="groups_id"> ([('view_access', '=', view_access)]) must be present in view but is missing.""",
        )
        self.assertInvalid(
            arch % ('', '<field name="inherit_id"/>', 'inherit_id', 'inherit_id'),
            """Unknown field "res.groups.inherit_id" in domain of <field name="groups_id"> ([('inherit_id', '=', inherit_id)])""",
        )
        self.assertInvalid(
            arch % ('', '<field name="inherit_id" select="multi"/>', 'view_access', 'inherit_id'),
            """Field 'inherit_id' used in domain of <field name="groups_id"> ([('view_access', '=', inherit_id)]) is present in view but is in select multi.""",
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
        self.assertFalse(self.env['res.partner'].with_user(user_demo).env.user.has_group('base.group_system'))
        arch = self.env['res.partner'].with_user(user_demo).get_view(view_id=view.id)['arch']
        tree = etree.fromstring(arch)
        self.assertTrue(tree.xpath('//field[@name="name"]'))
        self.assertFalse(tree.xpath('//field[@name="company_id"]'))
        self.assertTrue(tree.xpath('//div[@id="foo"]'))
        self.assertFalse(tree.xpath('//div[@id="bar"]'))

        user_admin = self.env.ref('base.user_admin')
        # Make sure admin has the base.group_system
        self.assertTrue(self.env['res.partner'].with_user(user_admin).env.user.has_group('base.group_system'))
        arch = self.env['res.partner'].with_user(user_admin).get_view(view_id=view.id)['arch']
        tree = etree.fromstring(arch)
        self.assertTrue(tree.xpath('//field[@name="name"]'))
        self.assertTrue(tree.xpath('//field[@name="company_id"]'))
        self.assertTrue(tree.xpath('//div[@id="foo"]'))
        self.assertTrue(tree.xpath('//div[@id="bar"]'))

    def test_attrs_groups_validation(self):
        def validate(arch, valid=False, parent=False):
            parent = 'parent.' if parent else ''
            if valid:
                self.assertValid(arch % {'attrs': f"""invisible="{parent}name == 'foo'" """})
                self.assertValid(arch % {'attrs': f"""domain="[('name', '!=', {parent}name)]" """})
                self.assertValid(arch % {'attrs': f"""context="{{'default_name': {parent}name}}" """})
                self.assertValid(arch % {'attrs': f"""decoration-info="{parent}name == 'foo'" """})
            else:
                self.assertInvalid(
                    arch % {'attrs': f"""invisible="{parent}name == 'foo'" """},
                    f"""Field 'name' used in modifier 'invisible' ({parent}name == 'foo') is restricted to the group(s)""",
                )
                self.assertInvalid(
                    arch % {'attrs': f"""domain="[('name', '!=', {parent}name)]" """},
                    f"""Field 'name' used in domain of <field name="inherit_id"> ([('name', '!=', {parent}name)]) is restricted to the group(s)""",
                )
                self.assertInvalid(
                    arch % {'attrs': f"""context="{{'default_name': {parent}name}}" """},
                    f"""Field 'name' used in context ({{'default_name': {parent}name}}) is restricted to the group(s)""",
                )
                self.assertInvalid(
                    arch % {'attrs': f"""decoration-info="{parent}name == 'foo'" """},
                    f"""Field 'name' used in decoration-info="{parent}name == 'foo'" is restricted to the group(s)""",
                )


        # Assert using a field restricted to a group
        # in another field without the same group is invalid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="inherit_id" %(attrs)s/>
            </form>
        """, valid=False)

        # Assert using a parent field restricted to a group
        # in a child field without the same group is invalid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="inherit_children_ids">
                    <tree editable="bottom">
                        <field name="inherit_id" %(attrs)s/>
                    </tree>
                </field>
            </form>
        """, valid=False, parent=True)

        # Assert using a parent field restricted to a group
        # in a child field with the same group is valid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="inherit_children_ids">
                    <tree editable="bottom">
                        <field name="inherit_id" groups="base.group_system" %(attrs)s/>
                    </tree>
                </field>
            </form>
        """, valid=True, parent=True)

        # Assert using a parent field available for everyone
        # in a child field restricted to a group is valid
        validate("""
            <form string="View">
                <field name="name"/>
                <field name="inherit_children_ids">
                    <tree editable="bottom">
                        <field name="inherit_id" groups="base.group_system" %(attrs)s/>
                    </tree>
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

        # Assert using a field restricted to a group only
        # in other fields restricted to at least one different group is invalid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="inherit_id" groups="base.group_system" %(attrs)s/>
                <field name="inherit_id" groups="base.group_portal" %(attrs)s/>
            </form>
        """, valid=False)

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

        # Assert using a field available for 1 group only
        # in another field restricted 2 groups is invalid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="inherit_id" groups="base.group_portal,base.group_system" %(attrs)s/>
            </form>
        """, valid=False)

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
                    <tree editable="bottom">
                        <field name="inherit_id" groups="base.group_system" %(attrs)s/>
                    </tree>
                </field>
            </form>
        """, valid=True, parent=True)

        # Assert using a field restricted to a group
        # in another field restricted to a group not including the group for which the field is available is invalid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="inherit_id" groups="base.group_erp_manager" %(attrs)s/>
            </form>
        """, valid=False)

        # Assert using a parent field restricted to a group
        # in a child field restricted to a group not including the group for which the field is available is invalid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="inherit_children_ids">
                    <tree editable="bottom">
                        <field name="inherit_id" groups="base.group_erp_manager" %(attrs)s/>
                    </tree>
                </field>
            </form>
        """, valid=False, parent=True)

        # Assert using a field within a block restricted to a group
        # in another field not restricted to the same group is invalid
        validate("""
            <form string="View">
                <group groups="base.group_system">
                    <field name="name"/>
                </group>
                <field name="inherit_id" %(attrs)s/>
            </form>
        """, valid=False)

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

        # Assert using a field within a block restricted to a group
        # in another field within a block restricted to a group not including the group for which the field is available
        # is invalid
        validate("""
            <form string="View">
                <group groups="base.group_system">
                    <field name="name"/>
                </group>
                <group groups="base.group_erp_manager">
                    <field name="inherit_id" %(attrs)s/>
                </group>
            </form>
        """, valid=False)

        # Assert using a parent field restricted to a group
        # in a child field under a relational field restricted to the same group is valid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="inherit_children_ids" groups="base.group_system">
                    <tree editable="bottom">
                        <field name="inherit_id" %(attrs)s/>
                    </tree>
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
                    <tree editable="bottom">
                        <field name="inherit_id" %(attrs)s/>
                    </tree>
                </field>
            </form>
        """, valid=True, parent=True)

        # Assert using a parent field restricted to a group
        # in a child field under a relational field restricted
        # to a group not including the group for which the field is available is invalid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="inherit_children_ids" groups="base.group_erp_manager">
                    <tree editable="bottom">
                        <field name="inherit_id" %(attrs)s/>
                    </tree>
                </field>
            </form>
        """, valid=False, parent=True)

        # Assert using a field restricted to users not having a group
        # in another field not restricted to any group is invalid
        validate("""
            <form string="View">
                <field name="name" groups="!base.group_system"/>
                <field name="inherit_id" %(attrs)s/>
            </form>
        """, valid=False)

        # Assert using a field not restricted to any group
        # in another field restricted to users not having a group is valid
        validate("""
            <form string="View">
                <field name="name"/>
                <field name="inherit_id" groups="!base.group_system" %(attrs)s/>
            </form>
        """, valid=True)

        # Assert using a field restricted to users not having multiple groups
        # in another field restricted to users not having one of the group only is invalid
        # e.g.
        # if the user is portal, the field "name" will not be in the view
        # but the field "inherit_id" where "name" is used will be in the view
        # making it invalid.
        validate("""
            <form string="View">
                <field name="name" groups="!base.group_system,!base.group_portal"/>
                <field name="inherit_id" groups="!base.group_system" %(attrs)s/>
            </form>
        """, valid=False)

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
        # in another field for which the non group is not implied is invalid
        # e.g.
        # if the user is employee, the field "name" will not be in the view
        # but the field "inherit_id" where "name" is used will be in the view,
        # making it invalid.
        validate("""
            <form string="View">
                <field name="name" groups="!base.group_user"/>
                <field name="inherit_id" groups="!base.group_system" %(attrs)s/>
            </form>
        """, valid=False)

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

        # Assert using a field restricted to non-admins, itself in a block restricted to employees,
        # in another field restricted to a block restricted to employees
        # is invalid
        # e.g.
        # if the user is admin, the field "name" will not be in the view
        # but the field "inherit_id", where "name" is used, will be in the view,
        # threfore making it invalid
        validate("""
            <form string="View">
                <group groups="base.group_user">
                    <field name="name" groups="!base.group_system"/>
                </group>
                <group groups="base.group_user">
                    <field name="inherit_id" %(attrs)s/>
                </group>
            </form>
        """, valid=False)

        # Assert using a field restricted to a group
        # in another field restricted the opposite group is invalid
        # e.g.
        # if the user is admin, the field "name" will be in the view
        # but the field "inherit_id", where "name" is used, will not be in the view,
        # therefore making it invalid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="inherit_id" groups="!base.group_system" %(attrs)s/>
            </form>
        """, valid=False)

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

        # Assert using a field restricted to a 'base.group_no_one' in another
        # field with a group implied 'base.group_no_one' is invalid. The group
        # 'base.group_no_one' must be in the view because it's depending of the
        # session.
        validate("""
            <form string="View">
                <field name="name" groups="base.group_no_one"/>
                <field name="inherit_id" %(attrs)s groups="base.group_user"/>
            </form>
        """, valid=False)
        validate("""
            <form string="View">
                <field name="name" groups="base.group_no_one"/>
                <group groups="base.group_no_one">
                    <field name="inherit_id" %(attrs)s groups="base.group_user"/>
                </group>
            </form>
        """, valid=True)

    @mute_logger('odoo.addons.base.models.ir_ui_view')
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
        self.patch(type(self.env['res.partner']).name, 'groups', 'base.group_system')
        self.env.user.groups_id += self.env.ref('base.group_multi_company')
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
        self.assertInvalid('<form><button type="action"/></form>', 'Button must have a name')
        self.assertInvalid('<form><button special="dummy"/></form>', "Invalid special 'dummy' in button")
        self.assertInvalid(arch % 'base.partner_root', "base.partner_root is of type res.partner, expected a subclass of ir.actions.actions")

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_tree(self):
        arch = """
            <tree>
                <field name="name"/>
                <button type='object' name="action_archive"/>
                %s
            </tree>
        """
        self.assertValid(arch % '')
        self.assertInvalid(arch % '<group/>', "Tree child can only have one of field, button, control, groupby, widget, header tag (not group)")

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_tree_groupby(self):
        arch = """
            <tree>
                <field name="name"/>
                <groupby name="%s">
                    <button type="object" name="action_archive"/>
                </groupby>
            </tree>
        """
        self.assertValid(arch % ('model_data_id'))
        self.assertInvalid(arch % ('type'), "Field 'type' found in 'groupby' node can only be of type many2one, found selection")
        self.assertInvalid(arch % ('dummy'), "Field 'dummy' found in 'groupby' node does not exist in model ir.ui.view")

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_tree_groupby_many2one(self):
        arch = """
            <tree>
                <field name="name"/>
                %s
                <groupby name="model_data_id">
                    %s
                    <button type="object" name="action_archive" invisible="noupdate" string="Button1"/>
                </groupby>
            </tree>
        """
        self.assertValid(arch % ('', '<field name="noupdate"/>'))
        self.assertInvalid(
            arch % ('', ''),
            """Field 'noupdate' used in modifier 'invisible' (noupdate) must be present in view but is missing.""",
        )
        self.assertInvalid(
            arch % ('<field name="noupdate"/>', ''),
            '''Field "noupdate" does not exist in model "ir.ui.view"''',
        )
        self.assertInvalid(
            arch % ('', '<field name="noupdate"/><field name="fake_field"/>'),
            '''Field "fake_field" does not exist in model "ir.model.data"''',
        )

    @mute_logger('odoo.addons.base.models.ir_ui_view')
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
            """Name or id 'model' in <label for="..."> must be present in view but is missing.""",
        )

    def test_col_colspan_numerical(self):
        self.assertValid('<form><group col="5"></group></form>')
        self.assertInvalid(
            '<form><group col="alpha"></group></form>',
            "'col' value must be an integer (alpha)",
        )
        self.assertValid('<form><div colspan="5"></div></form>')
        self.assertInvalid(
            '<form><div colspan="alpha"></div></form>',
            "'colspan' value must be an integer (alpha)",
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
        self.assertValid('<form><button icon="fa-warning"/>text</form>')
        self.assertValid('<form><span class="fa fa-warning"/>text</form>')
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
                <field name="groups_id" domain="[('invalid_field', '=', 'dummy')]"/>
            </form>""",
            """Unknown field "res.groups.invalid_field" in domain of <field name="groups_id"> ([('invalid_field', '=', 'dummy')]))""",
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
                <field name="groups_id" domain="[('name', '=', name)]"/>
                <label for="groups_id"/>
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
        self.assertInvalid(
            """<field name="model" position="replace"/>""",
            """Field 'model' used in domain of <field name="inherit_id"> ([('model', '=', model)]) must be present in view but is missing.""",
            inherit_id=view0.id,
        )

        # moving an element should have no impact; this test checks that the
        # implementation does not flag the inner element to be validated, which
        # prevents to locate the corresponding element inside the arch
        self.assertValid(
            """<field name="groups_id" position="before">
                <label for="groups_id" position="move"/>
            </field>""",
            inherit_id=view2.id,
        )

        # modifying a view extension should validate the other views
        with mute_logger('odoo.addons.base.models.ir_ui_view'):
            with self.assertRaises(ValidationError):
                with self.cr.savepoint():
                    view1.arch = """<form position="inside">
                        <field name="type"/>
                    </form>"""

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
                    <field name="groups_id" class="canary"/>
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
        field_groups_id = tree.xpath('//field[@name="groups_id"]')[0]
        self.assertEqual(
            len(field_groups_id.xpath(".//*[@class='canary']")),
            0,
            "The view test_views_test_view_ref should not be in the views of the many2many field groups_id"
        )

    @mute_logger('odoo.addons.base.models.ir_ui_view')
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
        arch = "<kanban><templates><t t-name='kanban-box'>%s</t></templates></kanban>"

        self.assertValid(arch % ('<span t-esc="record.resId"/>'))
        self.assertValid(arch % ('<t t-debug=""/>'))

        self.assertInvalid(
            arch % ('<span t-on-click="x.doIt()"/>'),
            """Error while validating view near:

<kanban __validate__="1"><templates><t t-name="kanban-box"><span t-on-click="x.doIt()"/></t></templates></kanban>
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
        arch = "<kanban><templates><t t-name='kanban-box'>%s</t></templates></kanban>"

        self.assertInvalid(
            arch % ('<span data-tooltip="Test"/>'),
            """Error while validating view near:

<kanban __validate__="1"><templates><t t-name="kanban-box"><span data-tooltip="Test"/></t></templates></kanban>
Forbidden attribute used in arch (data-tooltip)."""
        )

        self.assertInvalid(
            arch % ('<span data-tooltip-template="test"/>'),
            """Error while validating view near:

<kanban __validate__="1"><templates><t t-name="kanban-box"><span data-tooltip-template="test"/></t></templates></kanban>
Forbidden attribute used in arch (data-tooltip-template)."""
        )

        self.assertInvalid(
            arch % ('<span t-att-data-tooltip="test"/>'),
            """Error while validating view near:

<kanban __validate__="1"><templates><t t-name="kanban-box"><span t-att-data-tooltip="test"/></t></templates></kanban>
Forbidden attribute used in arch (t-att-data-tooltip)."""
        )

        self.assertInvalid(
            arch % ('<span t-attf-data-tooltip-template="{{ test }}"/>'),
            """Error while validating view near:

<kanban __validate__="1"><templates><t t-name="kanban-box"><span t-attf-data-tooltip-template="{{ test }}"/></t></templates></kanban>
Forbidden attribute used in arch (t-attf-data-tooltip-template)."""
        )

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_forbidden_use_of___comp___in_kanban(self):
        arch = "<kanban><templates><t t-name='kanban-box'>%s</t></templates></kanban>"
        self.assertInvalid(
            arch % '<t t-esc="__comp__.props.resId"/>',
            """Error while validating view near:

<kanban __validate__="1"><templates><t t-name="kanban-box"><t t-esc="__comp__.props.resId"/></t></templates></kanban>
Forbidden use of `__comp__` in arch."""
        )


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
            view.write({'groups_id': [1]})

        view.write({'mode': 'primary'})
        view.write({'groups_id': [1]})

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
        self.v2.toggle_active()
        context = {'check_view_ids': self.View.search([]).ids}
        arch = self.v0.with_context(context).get_combined_arch()
        self.assertEqual(
            etree.fromstring(arch),
            E.qweb(
                E.base(),
                E.v1(),
            )
        )

        self.v3.toggle_active()
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

        self.v2.toggle_active()
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
            if not model._abstract and model.check_access_rights('read', False):
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
            for attr, expr in modifiers.items():
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

        # fields in a tree view
        tree = etree.fromstring('''
            <tree>
                <header>
                    <button name="a" invisible="1"/>
                </header>
                <field name="a"/>
                <field name="a" invisible="0"/>
                <field name="a" column_invisible="1"/>
                <field name="a" invisible="b == 'c'"/>
                <field name="a" invisible="(b == 'c')"/>
            </tree>
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
                <field name="name" invisible="context.get('foo') and type == 'tree'"/>
            </form>
        """)
        for type_value, context, expected in [
            ('tree', {}, False),
            ('form', {}, False),
            ('tree', {'foo': True}, True),
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
        self.assertValid(arch % '<field name="model"/>')
        self.assertInvalid(
            arch % '',
            """Field 'model' used in modifier 'readonly' (model == 'ir.ui.view') must be present in view but is missing""",
        )

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
                       readonly="bidule.get('truc') or context.get('truc')"/>
            </form>
        """
        self.assertInvalid(
            arch,
            """Field 'bidule' used in modifier 'readonly' (bidule.get('truc') or context.get('truc')) must be present in view but is missing.""",
        )

        arch = """
            <form string="View">
                <field name="name"/>
                <field name="model"/>
                <field name="inherit_id"
                       readonly="context.get('truc') or bidule.get('toto')"/>
            </form>
        """
        self.assertInvalid(
            arch,
            """must be present in view but is missing""",
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
        self.assertValid(arch % ('', '<field name="model"/>'))
        self.assertInvalid(
            arch % ('', ''),
            """Field 'model' used in modifier 'readonly' (model == 'ir.ui.view') must be present in view but is missing.""",
        )
        self.assertInvalid(
            arch % ('<field name="model"/>', ''),
            """Field 'model' used in modifier 'readonly' (model == 'ir.ui.view') must be present in view but is missing.""",
        )

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
        self.assertValid(arch % ('<field name="model"/>', ''))
        self.assertInvalid(
            arch % ('', ''),
            """Field 'model' used in modifier 'readonly' (parent.model == 'ir.ui.view') must be present in view but is missing.""",
        )
        self.assertInvalid(
            arch % ('', '<field name="model"/>'),
            """Field 'model' used in modifier 'readonly' (parent.model == 'ir.ui.view') must be present in view but is missing.""",
        )

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
        self.assertFalse(self.env['res.partner'].with_user(user_demo).env.user.has_group('base.group_system'))
        arch = self.env['res.partner'].with_user(user_demo).get_view(view_id=view.id)['arch']
        tree = etree.fromstring(arch)
        self.assertTrue(tree.xpath('//field[@name="name"]'))
        self.assertFalse(tree.xpath('//field[@name="company_id"]'))
        self.assertTrue(tree.xpath('//div[@id="foo"]'))
        self.assertFalse(tree.xpath('//div[@id="bar"]'))

        user_admin = self.env.ref('base.user_admin')
        # Make sure admin has the base.group_system
        self.assertTrue(self.env['res.partner'].with_user(user_admin).env.user.has_group('base.group_system'))
        arch = self.env['res.partner'].with_user(user_admin).get_view(view_id=view.id)['arch']
        tree = etree.fromstring(arch)
        self.assertTrue(tree.xpath('//field[@name="name"]'))
        self.assertTrue(tree.xpath('//field[@name="company_id"]'))
        self.assertTrue(tree.xpath('//div[@id="foo"]'))
        self.assertTrue(tree.xpath('//div[@id="bar"]'))

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_17_attrs_groups_validation(self):
        def validate(arch, valid=False, parent=False):
            parent = 'parent.' if parent else ''
            if valid:
                self.assertValid(arch % {'attrs': f"""invisible="{parent}name == 'foo'" """})
                self.assertValid(arch % {'attrs': f"""domain="[('name', '!=', {parent}name)]" """})
                self.assertValid(arch % {'attrs': f"""context="{{'default_name': {parent}name}}" """})
                self.assertValid(arch % {'attrs': f"""decoration-info="{parent}name == 'foo'" """})
            else:
                self.assertInvalid(
                    arch % {'attrs': f"""invisible="{parent}name == 'foo'" """},
                    f"""Field 'name' used in modifier 'invisible' ({parent}name == 'foo') is restricted to the group(s)""",
                )
                self.assertInvalid(
                    arch % {'attrs': f"""domain="[('name', '!=', {parent}name)]" """},
                    f"""Field 'name' used in domain of <field name="inherit_id"> ([('name', '!=', {parent}name)]) is restricted to the group(s)""",
                )
                self.assertInvalid(
                    arch % {'attrs': f"""context="{{'default_name': {parent}name}}" """},
                    f"""Field 'name' used in context ({{'default_name': {parent}name}}) is restricted to the group(s)""",
                )
                self.assertInvalid(
                    arch % {'attrs': f"""decoration-info="{parent}name == 'foo'" """},
                    f"""Field 'name' used in decoration-info="{parent}name == 'foo'" is restricted to the group(s)""",
                )


        # Assert using a field restricted to a group
        # in another field without the same group is invalid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="inherit_id" %(attrs)s/>
            </form>
        """, valid=False)

        # Assert using a parent field restricted to a group
        # in a child field without the same group is invalid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="inherit_children_ids">
                    <tree editable="bottom">
                        <field name="inherit_id" %(attrs)s/>
                    </tree>
                </field>
            </form>
        """, valid=False, parent=True)

        # Assert using a parent field restricted to a group
        # in a child field with the same group is valid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="inherit_children_ids">
                    <tree editable="bottom">
                        <field name="inherit_id" groups="base.group_system" %(attrs)s/>
                    </tree>
                </field>
            </form>
        """, valid=True, parent=True)

        # Assert using a parent field available for everyone
        # in a child field restricted to a group is valid
        validate("""
            <form string="View">
                <field name="name"/>
                <field name="inherit_children_ids">
                    <tree editable="bottom">
                        <field name="inherit_id" groups="base.group_system" %(attrs)s/>
                    </tree>
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

        # Assert using a field restricted to a group only
        # in other fields restricted to at least one different group is invalid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="inherit_id" groups="base.group_system" %(attrs)s/>
                <field name="inherit_id" groups="base.group_portal" %(attrs)s/>
            </form>
        """, valid=False)

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

        # Assert using a field available for 1 group only
        # in another field restricted 2 groups is invalid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="inherit_id" groups="base.group_portal,base.group_system" %(attrs)s/>
            </form>
        """, valid=False)

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
                    <tree editable="bottom">
                        <field name="inherit_id" groups="base.group_system" %(attrs)s/>
                    </tree>
                </field>
            </form>
        """, valid=True, parent=True)

        # Assert using a field restricted to a group
        # in another field restricted to a group not including the group for which the field is available is invalid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="inherit_id" groups="base.group_erp_manager" %(attrs)s/>
            </form>
        """, valid=False)

        # Assert using a parent field restricted to a group
        # in a child field restricted to a group not including the group for which the field is available is invalid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="inherit_children_ids">
                    <tree editable="bottom">
                        <field name="inherit_id" groups="base.group_erp_manager" %(attrs)s/>
                    </tree>
                </field>
            </form>
        """, valid=False, parent=True)

        # Assert using a field within a block restricted to a group
        # in another field not restricted to the same group is invalid
        validate("""
            <form string="View">
                <group groups="base.group_system">
                    <field name="name"/>
                </group>
                <field name="inherit_id" %(attrs)s/>
            </form>
        """, valid=False)

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

        # Assert using a field within a block restricted to a group
        # in another field within a block restricted to a group not including the group for which the field is available
        # is invalid
        validate("""
            <form string="View">
                <group groups="base.group_system">
                    <field name="name"/>
                </group>
                <group groups="base.group_erp_manager">
                    <field name="inherit_id" %(attrs)s/>
                </group>
            </form>
        """, valid=False)

        # Assert using a parent field restricted to a group
        # in a child field under a relational field restricted to the same group is valid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="inherit_children_ids" groups="base.group_system">
                    <tree editable="bottom">
                        <field name="inherit_id" %(attrs)s/>
                    </tree>
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
                    <tree editable="bottom">
                        <field name="inherit_id" %(attrs)s/>
                    </tree>
                </field>
            </form>
        """, valid=True, parent=True)

        # Assert using a parent field restricted to a group
        # in a child field under a relational field restricted
        # to a group not including the group for which the field is available is invalid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="inherit_children_ids" groups="base.group_erp_manager">
                    <tree editable="bottom">
                        <field name="inherit_id" %(attrs)s/>
                    </tree>
                </field>
            </form>
        """, valid=False, parent=True)

        # Assert using a field restricted to users not having a group
        # in another field not restricted to any group is invalid
        validate("""
            <form string="View">
                <field name="name" groups="!base.group_system"/>
                <field name="inherit_id" %(attrs)s/>
            </form>
        """, valid=False)

        # Assert using a field not restricted to any group
        # in another field restricted to users not having a group is valid
        validate("""
            <form string="View">
                <field name="name"/>
                <field name="inherit_id" groups="!base.group_system" %(attrs)s/>
            </form>
        """, valid=True)

        # Assert using a field restricted to users not having multiple groups
        # in another field restricted to users not having one of the group only is invalid
        # e.g.
        # if the user is portal, the field "name" will not be in the view
        # but the field "inherit_id" where "name" is used will be in the view
        # making it invalid.
        validate("""
            <form string="View">
                <field name="name" groups="!base.group_system,!base.group_portal"/>
                <field name="inherit_id" groups="!base.group_system" %(attrs)s/>
            </form>
        """, valid=False)

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
        # in another field for which the non group is not implied is invalid
        # e.g.
        # if the user is employee, the field "name" will not be in the view
        # but the field "inherit_id" where "name" is used will be in the view,
        # making it invalid.
        validate("""
            <form string="View">
                <field name="name" groups="!base.group_user"/>
                <field name="inherit_id" groups="!base.group_system" %(attrs)s/>
            </form>
        """, valid=False)

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

        # Assert using a field restricted to non-admins, itself in a block restricted to employees,
        # in another field restricted to a block restricted to employees
        # is invalid
        # e.g.
        # if the user is admin, the field "name" will not be in the view
        # but the field "inherit_id", where "name" is used, will be in the view,
        # threfore making it invalid
        validate("""
            <form string="View">
                <group groups="base.group_user">
                    <field name="name" groups="!base.group_system"/>
                </group>
                <group groups="base.group_user">
                    <field name="inherit_id" %(attrs)s/>
                </group>
            </form>
        """, valid=False)

        # Assert using a field restricted to a group
        # in another field restricted the opposite group is invalid
        # e.g.
        # if the user is admin, the field "name" will be in the view
        # but the field "inherit_id", where "name" is used, will not be in the view,
        # therefore making it invalid
        validate("""
            <form string="View">
                <field name="name" groups="base.group_system"/>
                <field name="inherit_id" groups="!base.group_system" %(attrs)s/>
            </form>
        """, valid=False)

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
