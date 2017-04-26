# -*- encoding: utf-8 -*-
from functools import partial
import itertools

import unittest

from lxml import etree as ET
from lxml.builder import E

from psycopg2 import IntegrityError

from openerp.osv.orm import modifiers_tests
from openerp.exceptions import ValidationError
from openerp.tests import common
import openerp.tools

Field = E.field

class ViewXMLID(common.TransactionCase):
    def test_model_data_id(self):
        """ Check whether views know their xmlid record. """
        view = self.env.ref('base.view_company_form')
        self.assertTrue(view)
        self.assertTrue(view.model_data_id)
        self.assertEqual(view.model_data_id.complete_name, 'base.view_company_form')

class ViewCase(common.TransactionCase):
    def setUp(self):
        super(ViewCase, self).setUp()
        self.addTypeEqualityFunc(ET._Element, self.assertTreesEqual)
        self.Views = self.registry('ir.ui.view')

    def browse(self, id, context=None):
        return self.Views.browse(self.cr, self.uid, id, context=context)
    def create(self, value, context=None):
        return self.Views.create(self.cr, self.uid, value, context=context)

    def read_combined(self, id):
        return self.Views.read_combined(
            self.cr, self.uid,
            id, ['arch'],
            context={'check_view_ids': self.Views.search(self.cr, self.uid, [])}
        )

    def assertTreesEqual(self, n1, n2, msg=None):
        self.assertEqual(n1.tag, n2.tag, msg)
        self.assertEqual((n1.text or '').strip(), (n2.text or '').strip(), msg)
        self.assertEqual((n1.tail or '').strip(), (n2.tail or '').strip(), msg)

        # Because lxml uses ordereddicts in which order is important to
        # equality (!?!?!?!)
        self.assertEqual(dict(n1.attrib), dict(n2.attrib), msg)

        for c1, c2 in itertools.izip_longest(n1, n2):
            self.assertEqual(c1, c2, msg)


class TestNodeLocator(common.TransactionCase):
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
            'priority': 5, # higher than default views
        })
        self.ids[name] = view_id
        return view_id

    def setUp(self):
        super(TestViewInheritance, self).setUp()

        self.model = 'ir.ui.view.custom'
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

    def test_no_recursion(self):
        r1 = self.makeView('R1')
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.View.write(self.cr, self.uid, r1, {'inherit_id': r1})

        r2 = self.makeView('R2', r1)
        r3 = self.makeView('R3', r2)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.View.write(self.cr, self.uid, r2, {'inherit_id': r3})

        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.View.write(self.cr, self.uid, r1, {'inherit_id': r3})

        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.View.write(self.cr, self.uid, r1, {
                'inherit_id': r1,
                'arch': self.arch_for('itself', parent=True),
            })

class TestApplyInheritanceSpecs(ViewCase):
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
            self.base_arch,
            E.form(Field(name="replacement"), string="Title"))

    def test_delete(self):
        spec = Field(name="target", position="replace")

        self.View.apply_inheritance_specs(self.cr, self.uid,
                                          self.base_arch,
                                          spec, None)

        self.assertEqual(
            self.base_arch,
            E.form(string="Title"))

    def test_insert_after(self):
        spec = Field(
                Field(name="inserted"),
                name="target", position="after")

        self.View.apply_inheritance_specs(self.cr, self.uid,
                                          self.base_arch,
                                          spec, None)

        self.assertEqual(
            self.base_arch,
            E.form(
                Field(name="target"),
                Field(name="inserted"),
                string="Title"
            ))

    def test_insert_before(self):
        spec = Field(
                Field(name="inserted"),
                name="target", position="before")

        self.View.apply_inheritance_specs(self.cr, self.uid,
                                          self.base_arch,
                                          spec, None)

        self.assertEqual(
            self.base_arch,
            E.form(
                Field(name="inserted"),
                Field(name="target"),
                string="Title"))

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
            self.base_arch,
            E.form(
                Field(
                    Field(name="inserted"),
                    Field(name="inserted 2"),
                    name="target"),
                string="Title"))

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
            self.base_arch,
            E.form(
                Field(
                    Field(name="inserted 0"),
                    Field(name="inserted 1"),
                    Field(name="inserted 2"),
                    Field(name="inserted 3"),
                    name="target"),
                string="Title"))

    @openerp.tools.mute_logger('openerp.addons.base.ir.ir_ui_view')
    def test_invalid_position(self):
        spec = Field(
                Field(name="whoops"),
                name="target", position="serious_series")

        with self.assertRaises(ValueError):
            self.View.apply_inheritance_specs(self.cr, self.uid,
                                              self.base_arch,
                                              spec, None)

    @openerp.tools.mute_logger('openerp.addons.base.ir.ir_ui_view')
    def test_incorrect_version(self):
        # Version ignored on //field elements, so use something else
        arch = E.form(E.element(foo="42"))
        spec = E.element(
            Field(name="placeholder"),
            foo="42", version="7.0")

        with self.assertRaises(ValueError):
            self.View.apply_inheritance_specs(self.cr, self.uid,
                                              arch,
                                              spec, None)

    @openerp.tools.mute_logger('openerp.addons.base.ir.ir_ui_view')
    def test_target_not_found(self):
        spec = Field(name="targut")

        with self.assertRaises(ValueError):
            self.View.apply_inheritance_specs(self.cr, self.uid,
                                              self.base_arch,
                                              spec, None)

class TestApplyInheritanceWrapSpecs(ViewCase):
    def setUp(self):
        super(TestApplyInheritanceWrapSpecs, self).setUp()
        self.View = self.registry('ir.ui.view')
        self.base_arch = E.template(E.div(E.p("Content")))

    def apply_spec(self, spec):
        self.View.apply_inheritance_specs(self.cr, self.uid,
                                          self.base_arch,
                                          spec, None)

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

class TestApplyInheritedArchs(ViewCase):
    """ Applies a sequence of modificator archs to a base view
    """

class TestNoModel(ViewCase):
    def test_create_view_nomodel(self):
        View = self.registry('ir.ui.view')
        view_id = View.create(self.cr, self.uid, {
            'name': 'dummy',
            'arch': '<template name="foo"/>',
            'inherit_id': False,
            'type': 'qweb',
        })
        fields = ['name', 'arch', 'type', 'priority', 'inherit_id', 'model']
        [view] = View.read(self.cr, self.uid, [view_id], fields)
        self.assertEqual(view, {
            'id': view_id,
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
        self.env['res.lang'].load_lang('fr_FR')
        ARCH = '<template name="foo">%s</template>'
        TEXT_EN = "Copyright copyrighter"
        TEXT_FR = u"Copyrighter, tous droits réservés"
        view = self.env['ir.ui.view'].create({
            'name': 'dummy',
            'arch': ARCH % TEXT_EN,
            'inherit_id': False,
            'type': 'qweb',
        })
        self.env['ir.translation'].create({
            'type': 'model',
            'name': 'ir.ui.view,arch_db',
            'res_id': view.id,
            'lang': 'fr_FR',
            'src': TEXT_EN,
            'value': TEXT_FR,
        })
        view = view.with_context(lang='fr_FR')
        self.assertEqual(view.arch, ARCH % TEXT_FR)

class TestTemplating(ViewCase):
    def setUp(self):
        import openerp.modules
        super(TestTemplating, self).setUp()
        self._pool = openerp.modules.registry.RegistryManager.get(common.get_db_name())
        self._init = self._pool._init
        # fuck off
        self._pool._init = False

    def tearDown(self):
        self._pool._init = self._init
        super(TestTemplating, self).tearDown()

    def test_branding_inherit(self):
        Views = self.registry('ir.ui.view')
        id = Views.create(self.cr, self.uid, {
            'name': "Base view",
            'type': 'qweb',
            'arch': """<root>
                <item order="1"/>
            </root>
            """
        })
        id2 = Views.create(self.cr, self.uid, {
            'name': "Extension",
            'type': 'qweb',
            'inherit_id': id,
            'arch': """<xpath expr="//item" position="before">
                <item order="2"/>
            </xpath>
            """
        })

        arch_string = Views.read_combined(
            self.cr, self.uid, id, fields=['arch'],
            context={'inherit_branding': True})['arch']

        arch = ET.fromstring(arch_string)
        Views.distribute_branding(arch)

        [initial] = arch.xpath('//item[@order=1]')
        self.assertEqual(
            str(id),
            initial.get('data-oe-id'),
            "initial should come from the root view")
        self.assertEqual(
            '/root[1]/item[1]',
            initial.get('data-oe-xpath'),
            "initial's xpath should be within the root view only")

        [second] = arch.xpath('//item[@order=2]')
        self.assertEqual(
            str(id2),
            second.get('data-oe-id'),
            "second should come from the extension view")

    def test_branding_distribute_inner(self):
        """ Checks that the branding is correctly distributed within a view
        extension
        """
        Views = self.registry('ir.ui.view')
        id = Views.create(self.cr, self.uid, {
            'name': "Base view",
            'type': 'qweb',
            'arch': """<root>
                <item order="1"/>
            </root>"""
        })
        id2 = Views.create(self.cr, self.uid, {
            'name': "Extension",
            'type': 'qweb',
            'inherit_id': id,
            'arch': """<xpath expr="//item" position="before">
                <item order="2">
                    <content t-att-href="foo">bar</content>
                </item>
            </xpath>"""
        })

        arch_string = Views.read_combined(
            self.cr, self.uid, id, fields=['arch'],
            context={'inherit_branding': True})['arch']

        arch = ET.fromstring(arch_string)
        Views.distribute_branding(arch)

        self.assertEqual(
            arch,
            E.root(
                E.item(
                    E.content("bar", {
                        't-att-href': "foo",
                        'data-oe-model': 'ir.ui.view',
                        'data-oe-id': str(id2),
                        'data-oe-field': 'arch',
                        'data-oe-xpath': '/xpath/item/content[1]',
                    }), {
                        'order': '2',
                    }),
                E.item({
                    'order': '1',
                    'data-oe-model': 'ir.ui.view',
                    'data-oe-id': str(id),
                    'data-oe-field': 'arch',
                    'data-oe-xpath': '/root[1]/item[1]',
                })
            )
        )

    def test_esc_no_branding(self):
        Views = self.registry('ir.ui.view')
        id = Views.create(self.cr, self.uid, {
            'name': "Base View",
            'type': 'qweb',
            'arch': """<root>
                <item><span t-esc="foo"/></item>
            </root>""",
        })

        arch_string = Views.read_combined(
            self.cr, self.uid, id, fields=['arch'],
            context={'inherit_branding': True})['arch']
        arch = ET.fromstring(arch_string)
        Views.distribute_branding(arch)

        self.assertEqual(arch, E.root(E.item(E.span({'t-esc': "foo"}))))

    def test_ignore_unbrand(self):
        Views = self.registry('ir.ui.view')
        id = Views.create(self.cr, self.uid, {
            'name': "Base view",
            'type': 'qweb',
            'arch': """<root>
                <item order="1" t-ignore="true">
                    <t t-esc="foo"/>
                </item>
            </root>"""
        })
        id2 = Views.create(self.cr, self.uid, {
            'name': "Extension",
            'type': 'qweb',
            'inherit_id': id,
            'arch': """<xpath expr="//item[@order='1']" position="inside">
                <item order="2">
                    <content t-att-href="foo">bar</content>
                </item>
            </xpath>"""
        })

        arch_string = Views.read_combined(
            self.cr, self.uid, id, fields=['arch'],
            context={'inherit_branding': True})['arch']

        arch = ET.fromstring(arch_string)
        Views.distribute_branding(arch)

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

class test_views(ViewCase):

    def test_nonexistent_attribute_removal(self):
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
        kw.setdefault('mode', 'extension' if kw.get('inherit_id') else 'primary')
        kw.setdefault('active', True)

        keys = sorted(kw.keys())
        fields = ','.join('"%s"' % (k.replace('"', r'\"'),) for k in keys)
        params = ','.join('%%(%s)s' % (k,) for k in keys)

        query = 'INSERT INTO ir_ui_view(%s) VALUES(%s) RETURNING id' % (fields, params)
        self.cr.execute(query, kw)
        return self.cr.fetchone()[0]

    def test_custom_view_validation(self):
        Views = self.registry('ir.ui.view')
        model = 'ir.actions.act_url'

        validate = partial(Views._validate_custom_views, self.cr, self.uid, model)

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
        Views = self.registry('ir.ui.view')

        v1 = Views.create(self.cr, self.uid, {
            'name': "bob",
            'model': 'ir.ui.view',
            'arch': """
                <form string="Base title" version="7.0">
                    <separator name="separator" string="Separator" colspan="4"/>
                    <footer>
                        <button name="action_next" type="object" string="Next button" class="btn-primary"/>
                        <button string="Skip" special="cancel" class="btn-default"/>
                    </footer>
                </form>
            """
        })
        v2 = Views.create(self.cr, self.uid, {
            'name': "edmund",
            'model': 'ir.ui.view',
            'inherit_id': v1,
            'arch': """
                <data>
                    <form position="attributes" version="7.0">
                        <attribute name="string">Replacement title</attribute>
                    </form>
                    <footer position="replace">
                        <footer>
                            <button name="action_next" type="object" string="New button"/>
                        </footer>
                    </footer>
                    <separator name="separator" position="replace">
                        <p>Replacement data</p>
                    </separator>
                </data>
            """
        })
        v3 = Views.create(self.cr, self.uid, {
            'name': 'jake',
            'model': 'ir.ui.view',
            'inherit_id': v1,
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

        view = self.registry('ir.ui.view').fields_view_get(
            self.cr, self.uid, v2, view_type='form', context={
                # fucking what?
                'check_view_ids': [v2, v3]
            })
        self.assertEqual(view['type'], 'form')
        self.assertEqual(
            ET.fromstring(
                view['arch'],
                parser=ET.XMLParser(remove_blank_text=True)
            ),
            E.form(
                E.p("Replacement data"),
                E.footer(
                    E.button(name="action_next", type="object", string="New button"),
                    thing="bob lolo bibi and co", otherthing="lolo"
                ),
                string="Replacement title", version="7.0"))

    def test_view_inheritance_divergent_models(self):
        Views = self.registry('ir.ui.view')

        v1 = Views.create(self.cr, self.uid, {
            'name': "bob",
            'model': 'ir.ui.view.custom',
            'arch': """
                <form string="Base title" version="7.0">
                    <separator name="separator" string="Separator" colspan="4"/>
                    <footer>
                        <button name="action_next" type="object" string="Next button" class="btn-primary"/>
                        <button string="Skip" special="cancel" class="btn-default"/>
                    </footer>
                </form>
            """
        })
        v2 = Views.create(self.cr, self.uid, {
            'name': "edmund",
            'model': 'ir.ui.view',
            'inherit_id': v1,
            'arch': """
                <data>
                    <form position="attributes" version="7.0">
                        <attribute name="string">Replacement title</attribute>
                    </form>
                    <footer position="replace">
                        <footer>
                            <button name="action_next" type="object" string="New button"/>
                        </footer>
                    </footer>
                    <separator name="separator" position="replace">
                        <p>Replacement data</p>
                    </separator>
                </data>
            """
        })
        v3 = Views.create(self.cr, self.uid, {
            'name': 'jake',
            'model': 'ir.ui.menu',
            'inherit_id': v1,
            'priority': 17,
            'arch': """
                <footer position="attributes">
                    <attribute name="thing">bob</attribute>
                </footer>
            """
        })

        view = self.registry('ir.ui.view').fields_view_get(
            self.cr, self.uid, v2, view_type='form', context={
                # fucking what?
                'check_view_ids': [v2, v3]
            })
        self.assertEqual(view['type'], 'form')
        self.assertEqual(
            ET.fromstring(
                view['arch'],
                parser=ET.XMLParser(remove_blank_text=True)
            ),
            E.form(
                E.p("Replacement data"),
                E.footer(
                    E.button(name="action_next", type="object", string="New button")),
                string="Replacement title", version="7.0"
            ))

    def test_modifiers(self):
        # implemeted elsewhere...
        modifiers_tests()

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
        view = self.browse(self.create({
            'inherit_id': None,
            'arch': '<qweb/>'
        }))
        self.assertEqual(view.mode, 'primary')

        view2 = self.browse(self.create({
            'inherit_id': view.id,
            'arch': '<qweb/>'
        }))
        self.assertEqual(view2.mode, 'extension')

    @openerp.tools.mute_logger('openerp.sql_db')
    def testModeExplicit(self):
        view = self.browse(self.create({
            'inherit_id': None,
            'arch': '<qweb/>'
        }))
        view2 = self.browse(self.create({
            'inherit_id': view.id,
            'mode': 'primary',
            'arch': '<qweb/>'
        }))
        self.assertEqual(view.mode, 'primary')

        with self.assertRaises(IntegrityError):
            self.create({
                'inherit_id': None,
                'mode': 'extension',
                'arch': '<qweb/>'
            })

    @openerp.tools.mute_logger('openerp.sql_db')
    def testPurePrimaryToExtension(self):
        """
        A primary view with inherit_id=None can't be converted to extension
        """
        view_pure_primary = self.browse(self.create({
            'inherit_id': None,
            'arch': '<qweb/>'
        }))
        with self.assertRaises(IntegrityError):
            view_pure_primary.write({'mode': 'extension'})

    def testInheritPrimaryToExtension(self):
        """
        A primary view with an inherit_id can be converted to extension
        """
        base = self.create({'inherit_id': None, 'arch': '<qweb/>'})
        view = self.browse(self.create({
            'inherit_id': base,
            'mode': 'primary',
            'arch': '<qweb/>'
        }))

        view.write({'mode': 'extension'})

    def testDefaultExtensionToPrimary(self):
        """
        An extension view can be converted to primary
        """
        base = self.create({'inherit_id': None, 'arch': '<qweb/>'})
        view = self.browse(self.create({
            'inherit_id': base,
            'arch': '<qweb/>'
        }))

        view.write({'mode': 'primary'})

class TestDefaultView(ViewCase):
    def testDefaultViewBase(self):
        self.create({
            'inherit_id': False,
            'priority': 10,
            'mode': 'primary',
            'arch': '<qweb/>',
        })
        v2 = self.create({
            'inherit_id': False,
            'priority': 1,
            'mode': 'primary',
            'arch': '<qweb/>',
        })

        default = self.Views.default_view(self.cr, self.uid, False, 'qweb')
        self.assertEqual(
            default, v2,
            "default_view should get the view with the lowest priority for "
            "a (model, view_type) pair"
        )

    def testDefaultViewPrimary(self):
        v1 = self.create({
            'inherit_id': False,
            'priority': 10,
            'mode': 'primary',
            'arch': '<qweb/>',
        })
        self.create({
            'inherit_id': False,
            'priority': 5,
            'mode': 'primary',
            'arch': '<qweb/>',
        })
        v3 = self.create({
            'inherit_id': v1,
            'priority': 1,
            'mode': 'primary',
            'arch': '<qweb/>',
        })

        default = self.Views.default_view(self.cr, self.uid, False, 'qweb')
        self.assertEqual(
            default, v3,
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

        self.a1 = self.create({
            'model': 'a',
            'arch': '<qweb><a1/></qweb>'
        })
        self.a2 = self.create({
            'model': 'a',
            'inherit_id': self.a1,
            'priority': 5,
            'arch': '<xpath expr="//a1" position="after"><a2/></xpath>'
        })
        self.a3 = self.create({
            'model': 'a',
            'inherit_id': self.a1,
            'arch': '<xpath expr="//a1" position="after"><a3/></xpath>'
        })
        # mode=primary should be an inheritance boundary in both direction,
        # even within a model it should not extend the parent
        self.a4 = self.create({
            'model': 'a',
            'inherit_id': self.a1,
            'mode': 'primary',
            'arch': '<xpath expr="//a1" position="after"><a4/></xpath>',
        })

        self.b1 = self.create({
            'model': 'b',
            'inherit_id': self.a3,
            'mode': 'primary',
            'arch': '<xpath expr="//a1" position="after"><b1/></xpath>'
        })
        self.b2 = self.create({
            'model': 'b',
            'inherit_id': self.b1,
            'arch': '<xpath expr="//a1" position="after"><b2/></xpath>'
        })

        self.c1 = self.create({
            'model': 'c',
            'inherit_id': self.a1,
            'mode': 'primary',
            'arch': '<xpath expr="//a1" position="after"><c1/></xpath>'
        })
        self.c2 = self.create({
            'model': 'c',
            'inherit_id': self.c1,
            'priority': 5,
            'arch': '<xpath expr="//a1" position="after"><c2/></xpath>'
        })
        self.c3 = self.create({
            'model': 'c',
            'inherit_id': self.c2,
            'priority': 10,
            'arch': '<xpath expr="//a1" position="after"><c3/></xpath>'
        })

        self.d1 = self.create({
            'model': 'd',
            'inherit_id': self.b1,
            'mode': 'primary',
            'arch': '<xpath expr="//a1" position="after"><d1/></xpath>'
        })

    def test_basic_read(self):
        arch = self.read_combined(self.a1)['arch']
        self.assertEqual(
            ET.fromstring(arch),
            E.qweb(
                E.a1(),
                E.a3(),
                E.a2(),
            ), arch)

    def test_read_from_child(self):
        arch = self.read_combined(self.a3)['arch']
        self.assertEqual(
            ET.fromstring(arch),
            E.qweb(
                E.a1(),
                E.a3(),
                E.a2(),
            ), arch)

    def test_read_from_child_primary(self):
        arch = self.read_combined(self.a4)['arch']
        self.assertEqual(
            ET.fromstring(arch),
            E.qweb(
                E.a1(),
                E.a4(),
                E.a3(),
                E.a2(),
            ), arch)

    def test_cross_model_simple(self):
        arch = self.read_combined(self.c2)['arch']
        self.assertEqual(
            ET.fromstring(arch),
            E.qweb(
                E.a1(),
                E.c3(),
                E.c2(),
                E.c1(),
                E.a3(),
                E.a2(),
            ), arch)

    def test_cross_model_double(self):
        arch = self.read_combined(self.d1)['arch']
        self.assertEqual(
            ET.fromstring(arch),
            E.qweb(
                E.a1(),
                E.d1(),
                E.b2(),
                E.b1(),
                E.a3(),
                E.a2(),
            ), arch)

class TestOptionalViews(ViewCase):
    """
    Tests ability to enable/disable inherited views, formerly known as
    inherit_option_id
    """

    def setUp(self):
        super(TestOptionalViews, self).setUp()
        self.v0 = self.create({
            'model': 'a',
            'arch': '<qweb><base/></qweb>',
        })
        self.v1 = self.create({
            'model': 'a',
            'inherit_id': self.v0,
            'active': True,
            'priority': 10,
            'arch': '<xpath expr="//base" position="after"><v1/></xpath>',
        })
        self.v2 = self.create({
            'model': 'a',
            'inherit_id': self.v0,
            'active': True,
            'priority': 9,
            'arch': '<xpath expr="//base" position="after"><v2/></xpath>',
        })
        self.v3 = self.create({
            'model': 'a',
            'inherit_id': self.v0,
            'active': False,
            'priority': 8,
            'arch': '<xpath expr="//base" position="after"><v3/></xpath>'
        })

    def test_applied(self):
        """ mandatory and enabled views should be applied
        """
        arch = self.read_combined(self.v0)['arch']
        self.assertEqual(
            ET.fromstring(arch),
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
        self.browse(self.v2).toggle()
        arch = self.read_combined(self.v0)['arch']
        self.assertEqual(
            ET.fromstring(arch),
            E.qweb(
                E.base(),
                E.v1(),
            )
        )

        self.browse(self.v3).toggle()
        arch = self.read_combined(self.v0)['arch']
        self.assertEqual(
            ET.fromstring(arch),
            E.qweb(
                E.base(),
                E.v1(),
                E.v3(),
            )
        )

        self.browse(self.v2).toggle()
        arch = self.read_combined(self.v0)['arch']
        self.assertEqual(
            ET.fromstring(arch),
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
