# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from functools import partial
from itertools import izip_longest

from lxml import etree
from lxml.builder import E
from psycopg2 import IntegrityError

from odoo.osv.orm import modifiers_tests
from odoo.exceptions import ValidationError
from odoo.tests import common
from odoo.tools import mute_logger


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
        self.addTypeEqualityFunc(etree._Element, self.assertTreesEqual)
        self.View = self.env['ir.ui.view']

    def assertTreesEqual(self, n1, n2, msg=None):
        self.assertEqual(n1.tag, n2.tag, msg)
        self.assertEqual((n1.text or '').strip(), (n2.text or '').strip(), msg)
        self.assertEqual((n1.tail or '').strip(), (n2.tail or '').strip(), msg)

        # Because lxml uses ordereddicts in which order is important to
        # equality (!?!?!?!)
        self.assertEqual(dict(n1.attrib), dict(n2.attrib), msg)

        for c1, c2 in izip_longest(n1, n2):
            self.assertEqual(c1, c2, msg)


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
        return etree.tostring(element)

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
        self.view_ids[name] = view.id
        return view

    def setUp(self):
        super(TestViewInheritance, self).setUp()

        self.patch(self.registry, '_init', False)

        self.model = 'ir.ui.view.custom'
        self.view_ids = {}

        a = self.makeView("A")
        a1 = self.makeView("A1", a.id)
        a11 = self.makeView("A11", a1.id)
        self.makeView("A111", a11.id)
        self.makeView("A12", a1.id)
        a2 = self.makeView("A2", a.id)
        self.makeView("A21", a2.id)
        a22 = self.makeView("A22", a2.id)
        self.makeView("A221", a22.id)

        b = self.makeView('B', arch=self.arch_for("B", 'tree'))
        self.makeView('B1', b.id, arch=self.arch_for("B1", 'tree', parent=b))
        c = self.makeView('C', arch=self.arch_for("C", 'tree'))
        c.write({'priority': 1})

    def test_get_inheriting_views_arch(self):
        self.assertEqual(
            self.View.get_inheriting_views_arch(self.view_ids['A'], self.model), [
            (self.arch_for('A1', parent=True), self.view_ids['A1']),
            (self.arch_for('A2', parent=True), self.view_ids['A2']),
        ])

        self.assertEqual(
            self.View.get_inheriting_views_arch(self.view_ids['A21'], self.model),
            [])

        self.assertEqual(
            self.View.get_inheriting_views_arch(self.view_ids['A11'], self.model),
            [(self.arch_for('A111', parent=True), self.view_ids['A111'])])

    def test_default_view(self):
        default = self.View.default_view(model=self.model, view_type='form')
        self.assertEqual(default, self.view_ids['A'])

        default_tree = self.View.default_view(model=self.model, view_type='tree')
        self.assertEqual(default_tree, self.view_ids['C'])

    def test_no_default_view(self):
        self.assertFalse(self.View.default_view(model='does.not.exist', view_type='form'))
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

    def test_replace(self):
        spec = E.field(
                E.field(name="replacement"),
                name="target", position="replace")

        self.View.apply_inheritance_specs(self.base_arch, spec, None)

        self.assertEqual(
            self.base_arch,
            E.form(E.field(name="replacement"), string="Title"))

    def test_delete(self):
        spec = E.field(name="target", position="replace")

        self.View.apply_inheritance_specs(self.base_arch, spec, None)

        self.assertEqual(
            self.base_arch,
            E.form(string="Title"))

    def test_insert_after(self):
        spec = E.field(
                E.field(name="inserted"),
                name="target", position="after")

        self.View.apply_inheritance_specs(self.base_arch, spec, None)

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

        self.View.apply_inheritance_specs(self.base_arch, spec, None)

        self.assertEqual(
            self.base_arch,
            E.form(
                E.field(name="inserted"),
                E.field(name="target"),
                string="Title"))

    def test_insert_inside(self):
        default = E.field(E.field(name="inserted"), name="target")
        spec = E.field(E.field(name="inserted 2"), name="target", position='inside')

        self.View.apply_inheritance_specs(self.base_arch, default, None)
        self.View.apply_inheritance_specs(self.base_arch, spec, None)

        self.assertEqual(
            self.base_arch,
            E.form(
                E.field(
                    E.field(name="inserted"),
                    E.field(name="inserted 2"),
                    name="target"),
                string="Title"))

    def test_unpack_data(self):
        spec = E.data(
                E.field(E.field(name="inserted 0"), name="target"),
                E.field(E.field(name="inserted 1"), name="target"),
                E.field(E.field(name="inserted 2"), name="target"),
                E.field(E.field(name="inserted 3"), name="target"),
            )

        self.View.apply_inheritance_specs(self.base_arch, spec, None)

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

    @mute_logger('odoo.addons.base.ir.ir_ui_view')
    def test_invalid_position(self):
        spec = E.field(
                E.field(name="whoops"),
                name="target", position="serious_series")

        with self.assertRaises(ValueError):
            self.View.apply_inheritance_specs(self.base_arch, spec, None)

    @mute_logger('odoo.addons.base.ir.ir_ui_view')
    def test_incorrect_version(self):
        # Version ignored on //field elements, so use something else
        arch = E.form(E.element(foo="42"))
        spec = E.element(
            E.field(name="placeholder"),
            foo="42", version="7.0")

        with self.assertRaises(ValueError):
            self.View.apply_inheritance_specs(arch, spec, None)

    @mute_logger('odoo.addons.base.ir.ir_ui_view')
    def test_target_not_found(self):
        spec = E.field(name="targut")

        with self.assertRaises(ValueError):
            self.View.apply_inheritance_specs(self.base_arch, spec, None)


class TestApplyInheritanceWrapSpecs(ViewCase):
    def setUp(self):
        super(TestApplyInheritanceWrapSpecs, self).setUp()
        self.base_arch = E.template(E.div(E.p("Content")))

    def apply_spec(self, spec):
        self.View.apply_inheritance_specs(self.base_arch, spec, None)

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
        self.env['res.lang'].load_lang('fr_FR')
        ARCH = '<template name="foo">%s</template>'
        TEXT_EN = "Copyright copyrighter"
        TEXT_FR = u"Copyrighter, tous droits réservés"
        view = self.View.create({
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
        super(TestTemplating, self).setUp()
        self.patch(self.registry, '_init', False)

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

        arch_string = view1.with_context(inherit_branding=True).read_combined(['arch'])['arch']

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

        arch_string = view1.with_context(inherit_branding=True).read_combined(['arch'])['arch']

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

    def test_esc_no_branding(self):
        view = self.View.create({
            'name': "Base View",
            'type': 'qweb',
            'arch': """<root>
                <item><span t-esc="foo"/></item>
            </root>""",
        })

        arch_string = view.with_context(inherit_branding=True).read_combined(['arch'])['arch']
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

        arch_string = view1.with_context(inherit_branding=True).read_combined(['arch'])['arch']

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

        keys = sorted(kw)
        fields = ','.join('"%s"' % (k.replace('"', r'\"'),) for k in keys)
        params = ','.join('%%(%s)s' % (k,) for k in keys)

        query = 'INSERT INTO ir_ui_view(%s) VALUES(%s) RETURNING id' % (fields, params)
        self.cr.execute(query, kw)
        return self.cr.fetchone()[0]

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
                <form string="Base title" version="7.0">
                    <separator name="separator" string="Separator" colspan="4"/>
                    <footer>
                        <button name="action_next" type="object" string="Next button" class="btn-primary"/>
                        <button string="Skip" special="cancel" class="btn-default"/>
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

        view = self.View.with_context(check_view_ids=[view2.id, view3.id]) \
                        .fields_view_get(view2.id, view_type='form')
        self.assertEqual(view['type'], 'form')
        self.assertEqual(
            etree.fromstring(
                view['arch'],
                parser=etree.XMLParser(remove_blank_text=True)
            ),
            E.form(
                E.p("Replacement data"),
                E.footer(
                    E.button(name="action_next", type="object", string="New button"),
                    thing="bob lolo bibi and co", otherthing="lolo"
                ),
                string="Replacement title", version="7.0"))

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
        view = self.View.with_context(check_view_ids=view2.ids).fields_view_get(view1.id)
        self.assertEqual(view['type'], 'form')
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
        view = self.View.with_context(check_view_ids=view2.ids).fields_view_get(view1.id)
        self.assertEqual(view['type'], 'form')
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
        view = self.View.with_context(check_view_ids=view2.ids).fields_view_get(view1.id)
        self.assertEqual(view['type'], 'form')
        self.assertEqual(
            view['arch'],
            '<form string="F">(a<p/>b<p/>c<div/>)</form>',
        )

    def test_view_inheritance_divergent_models(self):
        view1 = self.View.create({
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
        view2 = self.View.create({
            'name': "edmund",
            'model': 'ir.ui.view',
            'inherit_id': view1.id,
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
                        .fields_view_get(view2.id, view_type='form')
        self.assertEqual(view['type'], 'form')
        self.assertEqual(
            etree.fromstring(
                view['arch'],
                parser=etree.XMLParser(remove_blank_text=True)
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
        arch = self.a1.with_context(context).read_combined(['arch'])['arch']
        self.assertEqual(
            etree.fromstring(arch),
            E.qweb(
                E.a1(),
                E.a3(),
                E.a2(),
            ), arch)

    def test_read_from_child(self):
        context = {'check_view_ids': self.View.search([]).ids}
        arch = self.a3.with_context(context).read_combined(['arch'])['arch']
        self.assertEqual(
            etree.fromstring(arch),
            E.qweb(
                E.a1(),
                E.a3(),
                E.a2(),
            ), arch)

    def test_read_from_child_primary(self):
        context = {'check_view_ids': self.View.search([]).ids}
        arch = self.a4.with_context(context).read_combined(['arch'])['arch']
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
        arch = self.c2.with_context(context).read_combined(['arch'])['arch']
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
        arch = self.d1.with_context(context).read_combined(['arch'])['arch']
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
        arch = self.v0.with_context(context).read_combined(['arch'])['arch']
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
        self.v2.toggle()
        context = {'check_view_ids': self.View.search([]).ids}
        arch = self.v0.with_context(context).read_combined(['arch'])['arch']
        self.assertEqual(
            etree.fromstring(arch),
            E.qweb(
                E.base(),
                E.v1(),
            )
        )

        self.v3.toggle()
        context = {'check_view_ids': self.View.search([]).ids}
        arch = self.v0.with_context(context).read_combined(['arch'])['arch']
        self.assertEqual(
            etree.fromstring(arch),
            E.qweb(
                E.base(),
                E.v1(),
                E.v3(),
            )
        )

        self.v2.toggle()
        context = {'check_view_ids': self.View.search([]).ids}
        arch = self.v0.with_context(context).read_combined(['arch'])['arch']
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
        content1 = self.env['ir.qweb'].with_context(check_view_ids=[view1.id, view2.id]).render(view1.id)
        content2 = self.env['ir.qweb'].with_context(check_view_ids=[view1.id, view2.id]).render(view2.id)

        self.assertEqual(content1, content2)

        # render view and child view with an xmlid
        self.env.cr.execute("INSERT INTO ir_model_data(name, model, res_id, module)"
                            "VALUES ('dummy', 'ir.ui.view', %s, 'base')" % view1.id)
        self.env.cr.execute("INSERT INTO ir_model_data(name, model, res_id, module)"
                            "VALUES ('dummy_ext', 'ir.ui.view', %s, 'base')" % view2.id)

        content1 = self.env['ir.qweb'].with_context(check_view_ids=[view1.id, view2.id]).render('base.dummy')
        content2 = self.env['ir.qweb'].with_context(check_view_ids=[view1.id, view2.id]).render('base.dummy_ext')

        self.assertEqual(content1, content2)

        # render view and primary extension with an id
        content1 = self.env['ir.qweb'].with_context(check_view_ids=[view1.id, view2.id, view3.id]).render(view1.id)
        content3 = self.env['ir.qweb'].with_context(check_view_ids=[view1.id, view2.id, view3.id]).render(view3.id)

        self.assertNotEqual(content1, content3)

        # render view and primary extension with an xmlid
        self.env.cr.execute("INSERT INTO ir_model_data(name, model, res_id, module)"
                            "VALUES ('dummy_primary_ext', 'ir.ui.view', %s, 'base')" % view3.id)

        content1 = self.env['ir.qweb'].with_context(check_view_ids=[view1.id, view2.id, view3.id]).render('base.dummy')
        content3 = self.env['ir.qweb'].with_context(check_view_ids=[view1.id, view2.id, view3.id]).render('base.dummy_primary_ext')

        self.assertNotEqual(content1, content3)
