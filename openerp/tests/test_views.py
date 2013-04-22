from lxml import etree as ET
from lxml.builder import E

from . import common

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
    def view_for(self, name):
        return ET.tostring(ET.Element('form', string=name))

    def makeView(self, name, parent=None):
        view_id = self.View.create(self.cr, self.uid, {
            'model': self.model,
            'name': name,
            'arch': self.view_for(name),
            'inherit_id': parent, })
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

    def tearDown(self):
        self.View.pool._init = self._init
        super(TestViewInheritance, self).tearDown()

    def test_get_children(self):
        self.assertEqual(self.View.get_inheriting_views_arch(
            self.cr, self.uid, self.ids['A'], self.model), [
            (self.view_for('A1'), self.ids['A1']),
            (self.view_for('A2'), self.ids['A2']),
        ])

        self.assertEqual(self.View.get_inheriting_views_arch(
            self.cr, self.uid, self.ids['A21'], self.model),
            [])

        self.assertEqual(self.View.get_inheriting_views_arch(
            self.cr, self.uid, self.ids['A11'], self.model),
            [(self.view_for('A111'), self.ids['A111'])])

    def test_iterate_descendents(self):
        descendents = list(self.View.iter(self.cr, self.uid, self.ids['A1'], self.model))
        self.assertEqual(descendents, [
            (self.ids[name], self.view_for(name))
            for name in ['A1', 'A11', 'A111', 'A12']
        ])
        descendents = list(self.View.iter(
            self.cr, self.uid, self.ids['A2'], self.model, exclude_base=True))
        self.assertEqual(descendents, [
            (self.ids[name], self.view_for(name))
            for name in ['A21', 'A22', 'A221']
        ])
