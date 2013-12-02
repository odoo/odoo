# -*- encoding: utf-8 -*-
from functools import partial
from lxml import etree as ET
from lxml.builder import E
import unittest2

from openerp.tests import common
from openerp.osv.orm import except_orm
from openerp.tools import mute_logger

Field = E.field


class TestNodeLocator(common.BaseCase):
    """
    The node locator returns None when it can not find a node, and the first
    match when it finds something (no jquery-style node sets)
    """
    def setUp(self):
        super(TestNodeLocator, self).setUp()
        self.Views = self.registry('ir.ui.view')

    def test_no_match_xpath(self):
        """
        xpath simply uses the provided @expr pattern to find a node
        """
        node = self.Views.locate_node(
            E.root(E.foo(), E.bar(), E.baz()),
            E.xpath(expr="//qux"))
        self.assertIsNone(node)

    def test_match_xpath(self):
        bar = E.bar()
        node = self.Views.locate_node(
            E.root(E.foo(), bar, E.baz()),
            E.xpath(expr="//bar"))
        self.assertIs(node, bar)


    def test_no_match_field(self):
        """
        A field spec will match by @name against all fields of the view
        """
        node = self.Views.locate_node(
            E.root(E.foo(), E.bar(), E.baz()),
            Field(name="qux"))
        self.assertIsNone(node)

        node = self.Views.locate_node(
            E.root(Field(name="foo"), Field(name="bar"), Field(name="baz")),
            Field(name="qux"))
        self.assertIsNone(node)

    def test_match_field(self):
        bar = Field(name="bar")
        node = self.Views.locate_node(
            E.root(Field(name="foo"), bar, Field(name="baz")),
            Field(name="bar"))
        self.assertIs(node, bar)


    def test_no_match_other(self):
        """
        Non-xpath non-fields are matched by node name first
        """
        node = self.Views.locate_node(
            E.root(E.foo(), E.bar(), E.baz()),
            E.qux())
        self.assertIsNone(node)

    def test_match_other(self):
        bar = E.bar()
        node = self.Views.locate_node(
            E.root(E.foo(), bar, E.baz()),
            E.bar())
        self.assertIs(bar, node)

    def test_attribute_mismatch(self):
        """
        Non-xpath non-field are filtered by matching attributes on spec and
        matched nodes
        """
        node = self.Views.locate_node(
            E.root(E.foo(attr='1'), E.bar(attr='2'), E.baz(attr='3')),
            E.bar(attr='5'))
        self.assertIsNone(node)

    def test_attribute_filter(self):
        match = E.bar(attr='2')
        node = self.Views.locate_node(
            E.root(E.bar(attr='1'), match, E.root(E.bar(attr='3'))),
            E.bar(attr='2'))
        self.assertIs(node, match)

    def test_version_mismatch(self):
        """
        A @version on the spec will be matched against the view's version
        """
        node = self.Views.locate_node(
            E.root(E.foo(attr='1'), version='4'),
            E.foo(attr='1', version='3'))
        self.assertIsNone(node)

class TestViewInheritance(common.TransactionCase):
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
        return ET.tostring(element)

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
        view_id = self.View.create(self.cr, self.uid, {
            'model': self.model,
            'name': name,
            'arch': arch or self.arch_for(name, parent=parent),
            'inherit_id': parent,
        })
        self.ids[name] = view_id
        return view_id

    def setUp(self):
        super(TestViewInheritance, self).setUp()

        self.model = 'dummy'
        self.View = self.registry('ir.ui.view')
        self._init = self.View.pool._init
        self.View.pool._init = False
        self.ids = {}

        a = self.makeView("A")
        a1 = self.makeView("A1", a)
        a11 = self.makeView("A11", a1)
        self.makeView("A111", a11)
        self.makeView("A12", a1)
        a2 = self.makeView("A2", a)
        self.makeView("A21", a2)
        a22 = self.makeView("A22", a2)
        self.makeView("A221", a22)

        b = self.makeView('B', arch=self.arch_for("B", 'tree'))
        self.makeView('B1', b, arch=self.arch_for("B1", 'tree', parent=b))
        c = self.makeView('C', arch=self.arch_for("C", 'tree'))
        self.View.write(self.cr, self.uid, c, {'priority': 1})

    def tearDown(self):
        self.View.pool._init = self._init
        super(TestViewInheritance, self).tearDown()

    def test_get_inheriting_views_arch(self):
        self.assertEqual(self.View.get_inheriting_views_arch(
            self.cr, self.uid, self.ids['A'], self.model), [
            (self.arch_for('A1', parent=True), self.ids['A1']),
            (self.arch_for('A2', parent=True), self.ids['A2']),
        ])

        self.assertEqual(self.View.get_inheriting_views_arch(
            self.cr, self.uid, self.ids['A21'], self.model),
            [])

        self.assertEqual(self.View.get_inheriting_views_arch(
            self.cr, self.uid, self.ids['A11'], self.model),
            [(self.arch_for('A111', parent=True), self.ids['A111'])])

    def test_default_view(self):
        default = self.View.default_view(
            self.cr, self.uid, model=self.model, view_type='form')
        self.assertEqual(default, self.ids['A'])

        default_tree = self.View.default_view(
            self.cr, self.uid, model=self.model, view_type='tree')
        self.assertEqual(default_tree, self.ids['C'])

    def test_no_default_view(self):
        self.assertFalse(
            self.View.default_view(
                self.cr, self.uid, model='does.not.exist', view_type='form'))

        self.assertFalse(
            self.View.default_view(
                self.cr, self.uid, model=self.model, view_type='graph'))

class TestApplyInheritanceSpecs(common.TransactionCase):
    """ Applies a sequence of inheritance specification nodes to a base
    architecture. IO state parameters (cr, uid, model, context) are used for
    error reporting

    The base architecture is altered in-place.
    """
    def setUp(self):
        super(TestApplyInheritanceSpecs, self).setUp()
        self.View = self.registry('ir.ui.view')
        self.base_arch = E.form(
            Field(name="target"),
            string="Title")

    def test_replace(self):
        spec = Field(
                Field(name="replacement"),
                name="target", position="replace")

        self.View.apply_inheritance_specs(self.cr, self.uid,
                                          self.base_arch,
                                          spec, None)

        self.assertEqual(
            ET.tostring(self.base_arch),
            ET.tostring(E.form(Field(name="replacement"), string="Title")))

    def test_delete(self):
        spec = Field(name="target", position="replace")

        self.View.apply_inheritance_specs(self.cr, self.uid,
                                          self.base_arch,
                                          spec, None)

        self.assertEqual(
            ET.tostring(self.base_arch),
            ET.tostring(E.form(string="Title")))

    def test_insert_after(self):
        spec = Field(
                Field(name="inserted"),
                name="target", position="after")

        self.View.apply_inheritance_specs(self.cr, self.uid,
                                          self.base_arch,
                                          spec, None)

        self.assertEqual(
            ET.tostring(self.base_arch),
            ET.tostring(E.form(
                Field(name="target"),
                Field(name="inserted"),
                string="Title"
            )))

    def test_insert_before(self):
        spec = Field(
                Field(name="inserted"),
                name="target", position="before")

        self.View.apply_inheritance_specs(self.cr, self.uid,
                                          self.base_arch,
                                          spec, None)

        self.assertEqual(
            ET.tostring(self.base_arch),
            ET.tostring(E.form(
                Field(name="inserted"),
                Field(name="target"),
                string="Title")))

    def test_insert_inside(self):
        default = Field(Field(name="inserted"), name="target")
        spec = Field(Field(name="inserted 2"), name="target", position='inside')

        self.View.apply_inheritance_specs(self.cr, self.uid,
                                          self.base_arch,
                                          default, None)
        self.View.apply_inheritance_specs(self.cr, self.uid,
                                          self.base_arch,
                                          spec, None)

        self.assertEqual(
            ET.tostring(self.base_arch),
            ET.tostring(E.form(
                Field(
                    Field(name="inserted"),
                    Field(name="inserted 2"),
                    name="target"),
                string="Title")))

    def test_unpack_data(self):
        spec = E.data(
                Field(Field(name="inserted 0"), name="target"),
                Field(Field(name="inserted 1"), name="target"),
                Field(Field(name="inserted 2"), name="target"),
                Field(Field(name="inserted 3"), name="target"),
            )

        self.View.apply_inheritance_specs(self.cr, self.uid,
                                          self.base_arch,
                                          spec, None)

        self.assertEqual(
            ET.tostring(self.base_arch),
            ET.tostring(E.form(
                Field(
                    Field(name="inserted 0"),
                    Field(name="inserted 1"),
                    Field(name="inserted 2"),
                    Field(name="inserted 3"),
                    name="target"),
                string="Title")))

    def test_invalid_position(self):
        spec = Field(
                Field(name="whoops"),
                name="target", position="serious_series")

        with self.assertRaises(AttributeError):
            self.View.apply_inheritance_specs(self.cr, self.uid,
                                              self.base_arch,
                                              spec, None)

    def test_incorrect_version(self):
        # Version ignored on //field elements, so use something else
        arch = E.form(E.element(foo="42"))
        spec = E.element(
            Field(name="placeholder"),
            foo="42", version="7.0")

        with self.assertRaises(AttributeError):
            self.View.apply_inheritance_specs(self.cr, self.uid,
                                              arch,
                                              spec, None)

    def test_target_not_found(self):
        spec = Field(name="targut")

        with self.assertRaises(AttributeError):
            self.View.apply_inheritance_specs(self.cr, self.uid,
                                              self.base_arch,
                                              spec, None)

class TestApplyInheritedArchs(common.TransactionCase):
    """ Applies a sequence of modificator archs to a base view
    """

class TestViewCombined(common.TransactionCase):
    """
    Test fallback operations of View.read_combined:
    * defaults mapping
    * ?
    """

class TestNoModel(common.TransactionCase):
    def test_create_view_nomodel(self):
        View = self.registry('ir.ui.view')
        view_id = View.create(self.cr, self.uid, {
            'name': 'dummy',
            'arch': '<form string=""/>',
            'inherit_id': False
        })
        fields = ['name', 'arch', 'type', 'priority', 'inherit_id', 'model']
        [view] = View.read(self.cr, self.uid, [view_id], fields)
        self.assertEqual(view, {
            'id': view_id,
            'name': 'dummy',
            'arch': '<form string=""/>',
            'type': 'form',
            'priority': 16,
            'inherit_id': False,
            'model': False,
        })

    arch = E.body(
        E.div(
            E.h1("Title"),
            id="header"),
        E.p("Welcome!"),
        E.div(
            E.hr(),
            E.p("Copyright copyrighter", {'class': 'legalese'}),
            id="footer"),
        {'class': "index"},)
    def test_fields_mess(self):
        """
        Try to call __view_look_dom_arch without a model provided, will need
        to be altered once it's broken up into sane components
        """
        View = self.registry('ir.ui.view')

        sarch, fields = View.postprocess_and_fields(
            self.cr, self.uid, None, self.arch, None)

        self.assertEqual(sarch, ET.tostring(self.arch, encoding='utf-8'))
        self.assertEqual(fields, {})

    def test_mess_translation(self):
        """
        Test if translations work correctly without a model
        """
        View = self.registry('ir.ui.view')
        self.registry('res.lang').load_lang(self.cr, self.uid, 'fr_FR')
        self.registry('ir.translation').create(self.cr, self.uid, {
            'name': '',
            'type': 'view',
            'lang': 'fr_FR',
            'src': 'Copyright copyrighter',
            'value': u"Copyrighter, tous droits réservés",
        })
        sarch, fields = View.postprocess_and_fields(
            self.cr, self.uid, None, self.arch, None, {'lang': 'fr_FR'})
        self.assertEqual(
            sarch,
            ET.tostring(self.arch, encoding='utf-8')
                .replace('Copyright copyrighter',
                         'Copyrighter, tous droits réservés'))
        self.assertEqual(fields, {})


class test_views(common.TransactionCase):

    @mute_logger('openerp.osv.orm', 'openerp.addons.base.ir.ir_ui_view')
    def test_00_init_check_views(self):
        Views = self.registry('ir.ui.view')

        self.assertTrue(Views.pool._init)

        error_msg = "The model name does not exist or the view architecture cannot be rendered"
        # test arch check is call for views without xmlid during registry initialization
        with self.assertRaisesRegexp(except_orm, error_msg):
            Views.create(self.cr, self.uid, {
                'name': 'Test View #1',
                'model': 'ir.ui.view',
                'arch': """<?xml version="1.0"?>
                            <tree>
                              <field name="test_1"/>
                            </tree>
                        """,
            })

        # same for inherited views
        with self.assertRaisesRegexp(except_orm, error_msg):
            # Views.pudb = True
            Views.create(self.cr, self.uid, {
                'name': 'Test View #2',
                'model': 'ir.ui.view',
                'inherit_id': self.browse_ref('base.view_view_tree').id,
                'arch': """<?xml version="1.0"?>
                            <xpath expr="//field[@name='name']" position="after">
                              <field name="test_2"/>
                            </xpath>
                        """,
            })

    def test_20_remove_unexisting_attribute(self):
        Views = self.registry('ir.ui.view')
        Views.create(self.cr, self.uid, {
            'name': 'Test View',
            'model': 'ir.ui.view',
            'inherit_id': self.browse_ref('base.view_view_tree').id,
            'arch': """<?xml version="1.0"?>
                        <xpath expr="//field[@name='name']" position="attributes">
                            <attribute name="non_existing_attribute"></attribute>
                        </xpath>
                    """,
        })

    def _insert_view(self, **kw):
        """Insert view into database via a query to passtrough validation"""
        kw.pop('id', None)

        keys = sorted(kw.keys())
        fields = ','.join('"%s"' % (k.replace('"', r'\"'),) for k in keys)
        params = ','.join('%%(%s)s' % (k,) for k in keys)

        query = 'INSERT INTO ir_ui_view(%s) VALUES(%s) RETURNING id' % (fields, params)
        self.cr.execute(query, kw)
        return self.cr.fetchone()[0]

    def test_10_validate_custom_views(self):
        Views = self.registry('ir.ui.view')
        model = 'ir.actions.act_url'

        validate = partial(Views._validate_custom_views, self.cr, self.uid, model)

        # validation of a single view
        vid = self._insert_view(
            name='base view',
            model=model,
            priority=1,
            arch="""<?xml version="1.0"?>
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
            arch="""<?xml version="1.0"?>
                        <xpath expr="//field[@name='url']" position="before">
                          <field name="name"/>
                        </xpath>
                    """,
        )
        self.assertTrue(validate())     # inherited view
