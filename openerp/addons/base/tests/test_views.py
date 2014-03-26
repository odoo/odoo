# -*- encoding: utf-8 -*-
from functools import partial

import unittest2

from lxml import etree as ET
from lxml.builder import E

from openerp.tests import common

Field = E.field

class ViewCase(common.TransactionCase):
    def setUp(self):
        super(ViewCase, self).setUp()
        self.addTypeEqualityFunc(ET._Element, self.assertTreesEqual)

    def assertTreesEqual(self, n1, n2, msg=None):
        self.assertEqual(n1.tag, n2.tag)
        self.assertEqual((n1.text or '').strip(), (n2.text or '').strip(), msg)
        self.assertEqual((n1.tail or '').strip(), (n2.tail or '').strip(), msg)

        # Because lxml uses ordereddicts in which order is important to
        # equality (!?!?!?!)
        self.assertEqual(dict(n1.attrib), dict(n2.attrib), msg)

        for c1, c2 in zip(n1, n2):
            self.assertTreesEqual(c1, c2, msg)


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

class TestApplyInheritedArchs(ViewCase):
    """ Applies a sequence of modificator archs to a base view
    """

class TestViewCombined(ViewCase):
    """
    Test fallback operations of View.read_combined:
    * defaults mapping
    * ?
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
        View = self.registry('ir.ui.view')
        self.registry('res.lang').load_lang(self.cr, self.uid, 'fr_FR')
        orig_text = "Copyright copyrighter"
        translated_text = u"Copyrighter, tous droits réservés"
        self.text_para.text = orig_text 
        self.registry('ir.translation').create(self.cr, self.uid, {
            'name': 'website',
            'type': 'view',
            'lang': 'fr_FR',
            'src': orig_text,
            'value': translated_text,
        })
        sarch = View.translate_qweb(self.cr, self.uid, None, self.arch, 'fr_FR')

        self.text_para.text = translated_text
        self.assertEqual(sarch, self.arch)

class TestTemplating(ViewCase):
    def setUp(self):
        import openerp.modules
        super(TestTemplating, self).setUp()
        self._pool = openerp.modules.registry.RegistryManager.get(common.DB)
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
                        'data-oe-source-id': str(id)
                    }),
                E.item({
                    'order': '1',
                    'data-oe-model': 'ir.ui.view',
                    'data-oe-id': str(id),
                    'data-oe-field': 'arch',
                    'data-oe-xpath': '/root[1]/item[1]'
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
                        {'order': '2', 'data-oe-source-id': str(id)},
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

    def test_view_inheritance(self):
        Views = self.registry('ir.ui.view')

        v1 = Views.create(self.cr, self.uid, {
            'name': "bob",
            'model': 'ir.ui.view',
            'arch': """
                <form string="Base title" version="7.0">
                    <separator string="separator" colspan="4"/>
                    <footer>
                        <button name="action_next" type="object" string="Next button"/>
                        or
                        <button string="Skip" special="cancel" />
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
                    <separator string="separator" position="replace">
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
                    E.button(name="action_next", type="object", string="New button"),
                    thing="bob"
                ),
                string="Replacement title", version="7.0"))

    def test_view_inheritance_divergent_models(self):
        Views = self.registry('ir.ui.view')

        v1 = Views.create(self.cr, self.uid, {
            'name': "bob",
            'model': 'ir.ui.view.custom',
            'arch': """
                <form string="Base title" version="7.0">
                    <separator string="separator" colspan="4"/>
                    <footer>
                        <button name="action_next" type="object" string="Next button"/>
                        or
                        <button string="Skip" special="cancel" />
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
                    <separator string="separator" position="replace">
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
