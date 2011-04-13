import copy
import xml.etree.ElementTree
import mock

import unittest2
import simplejson

import base.controllers.main
import openerpweb.nonliterals
import openerpweb.openerpweb

def field_attrs(fields_view_get, fieldname):
    (field,) =  filter(lambda f: f['attrs'].get('name') == fieldname,
                       fields_view_get['arch']['children'])
    return field['attrs']

#noinspection PyCompatibility
class DomainsAndContextsTest(unittest2.TestCase):
    def setUp(self):
        self.view = base.controllers.main.View()

    def test_convert_literal_domain(self):
        e = xml.etree.ElementTree.Element(
            'field', domain="  [('somefield', '=', 3)]  ")
        self.view.parse_domains_and_contexts(e, None)

        self.assertEqual(
            e.get('domain'),
            [('somefield', '=', 3)])

    def test_convert_complex_domain(self):
        e = xml.etree.ElementTree.Element(
            'field',
            domain="[('account_id.type','in',['receivable','payable']),"
                   "('reconcile_id','=',False),"
                   "('reconcile_partial_id','=',False),"
                   "('state', '=', 'valid')]"
        )
        self.view.parse_domains_and_contexts(e, None)

        self.assertEqual(
            e.get('domain'),
            [('account_id.type', 'in', ['receivable', 'payable']),
             ('reconcile_id', '=', False),
             ('reconcile_partial_id', '=', False),
             ('state', '=', 'valid')]
        )

    def test_retrieve_nonliteral_domain(self):
        session = mock.Mock(spec=openerpweb.openerpweb.OpenERPSession)
        session.domains_store = {}
        domain_string = ("[('month','=',(datetime.date.today() - "
                         "datetime.timedelta(365/12)).strftime('%%m'))]")
        e = xml.etree.ElementTree.Element(
            'field', domain=domain_string)

        self.view.parse_domains_and_contexts(e, session)

        self.assertIsInstance(e.get('domain'), openerpweb.nonliterals.Domain)
        self.assertEqual(
            openerpweb.nonliterals.Domain(
                session, key=e.get('domain').key).get_domain_string(),
            domain_string)

    def test_convert_literal_context(self):
        e = xml.etree.ElementTree.Element(
            'field', context="  {'some_prop':  3}  ")
        self.view.parse_domains_and_contexts(e, None)

        self.assertEqual(
            e.get('context'),
            {'some_prop': 3})

    def test_convert_complex_context(self):
        e = xml.etree.ElementTree.Element(
            'field',
            context="{'account_id.type': ['receivable','payable'],"
                     "'reconcile_id': False,"
                     "'reconcile_partial_id': False,"
                     "'state': 'valid'}"
        )
        self.view.parse_domains_and_contexts(e, None)

        self.assertEqual(
            e.get('context'),
            {'account_id.type': ['receivable', 'payable'],
             'reconcile_id': False,
             'reconcile_partial_id': False,
             'state': 'valid'}
        )

    def test_retrieve_nonliteral_context(self):
        session = mock.Mock(spec=openerpweb.openerpweb.OpenERPSession)
        session.contexts_store = {}
        context_string = ("{'month': (datetime.date.today() - "
                         "datetime.timedelta(365/12)).strftime('%%m')}")
        e = xml.etree.ElementTree.Element(
            'field', context=context_string)

        self.view.parse_domains_and_contexts(e, session)

        self.assertIsInstance(e.get('context'), openerpweb.nonliterals.Context)
        self.assertEqual(
            openerpweb.nonliterals.Context(
                session, key=e.get('context').key).get_context_string(),
            context_string)

class AttrsNormalizationTest(unittest2.TestCase):
    def setUp(self):
        self.view = base.controllers.main.View()

    def test_identity(self):
        base_view = """
            <form string="Title">
                <group>
                    <field name="some_field"/>
                    <field name="some_other_field"/>
                </group>
                <field name="stuff"/>
            </form>
        """

        pristine = xml.etree.ElementTree.fromstring(base_view)
        transformed = self.view.transform_view(base_view, None)

        self.assertEqual(
             xml.etree.ElementTree.tostring(transformed),
             xml.etree.ElementTree.tostring(pristine)
        )
    def test_transform_states(self):
        element = xml.etree.ElementTree.Element(
            'field', states="open,closed")
        self.view.normalize_attrs(element, {})

        self.assertIsNone(element.get('states'))
        self.assertEqual(
            simplejson.loads(element.get('attrs')),
            {'invisible': [['state', 'not in', ['open', 'closed']]]})

    def test_transform_invisible(self):
        element = xml.etree.ElementTree.Element(
            'field', invisible="context.get('invisible_country', False)")

        empty_context = copy.deepcopy(element)
        self.view.normalize_attrs(empty_context, {})
        self.assertEqual(empty_context.get('invisible'), None)

        full_context = copy.deepcopy(element)
        self.view.normalize_attrs(full_context, {'invisible_country': True})
        self.assertEqual(full_context.get('invisible'), '1')

    def test_transform_invisible_list_column(self):
        req = mock.Mock()
        req.context =  {'set_editable':True, 'set_visible':True,
                        'gtd_visible':True, 'user_invisible':True}
        req.session.evaluation_context = \
            openerpweb.openerpweb.OpenERPSession().evaluation_context
        req.session.model('project.task').fields_view_get.return_value = {
            'arch': '''
            <tree colors="grey:state in ('cancelled','done');blue:state == 'pending';red:date_deadline and (date_deadline&lt;current_date) and (state in ('draft','pending','open'))" string="Tasks">
                <field name="sequence" invisible="not context.get('seq_visible', False)"/>
                <field name="user_id" invisible="context.get('user_invisible', False)"/>
                <field name="delegated_user_id" invisible="context.get('show_delegated', True)"/>
                <field name="total_hours" invisible="1"/>
                <field name="date_deadline" invisible="context.get('deadline_visible',True)"/>
                <field name="type_id" invisible="context.get('set_visible',False)"/>
            </tree>
        '''}
        parsed_view = base.controllers.main.View().fields_view_get(
            req, 'project.task', 42, 'tree')

        self.assertTrue(field_attrs(parsed_view, 'sequence')['invisible'])
        self.assertTrue(field_attrs(parsed_view, 'user_id')['invisible'])
        self.assertTrue(
            field_attrs(parsed_view, 'delegated_user_id')['invisible'])
        self.assertTrue(field_attrs(parsed_view, 'total_hours')['invisible'])
        self.assertTrue(
            field_attrs(parsed_view, 'date_deadline')['invisible'])
        self.assertTrue(field_attrs(parsed_view, 'type_id')['invisible'])

class ListViewTest(unittest2.TestCase):
    def setUp(self):
        self.view = base.controllers.main.ListView()
        self.request = mock.Mock()
        self.request.context = {'set_editable': True}
    def test_no_editable_editable_context(self):
        self.request.session.model('fake').fields_view_get.return_value = \
            {'arch': '<tree><field name="foo"/></tree>'}
        view = self.view.fields_view_get(self.request, 'fake', False)

        self.assertEqual(view['arch']['attrs']['editable'],
                         'bottom')
    def test_editable_top_editable_context(self):
        self.request.session.model('fake').fields_view_get.return_value = \
            {'arch': '<tree editable="top"><field name="foo"/></tree>'}
        view = self.view.fields_view_get(self.request, 'fake', False)

        self.assertEqual(view['arch']['attrs']['editable'],
                         'top')

    def test_editable_bottom_editable_context(self):
        self.request.session.model('fake').fields_view_get.return_value = \
            {'arch': '<tree editable="bottom"><field name="foo"/></tree>'}
        view = self.view.fields_view_get(self.request, 'fake', False)

        self.assertEqual(view['arch']['attrs']['editable'],
                         'bottom')

    def test_color_nocolor(self):
        self.assertEqual(
            self.view.process_colors(
                {'arch': {'attrs': {}, 'children': []}}, {}, {}),
            None)
    def test_color_literal(self):
        self.assertEqual(
            self.view.process_colors(
                {'arch': {'attrs': {'colors': 'black:1'}}, 'children': []},
                {}, {}),
            'black')
    def test_color_miss(self):
        self.assertEqual(
            self.view.process_colors(
                {'arch': {'attrs': {'colors': "grey:state in ('cancelled','done');blue:state in ('pending')"}},
                 'children': []
                }, {'state': 'open'}, {}),
            None)
    def test_color_compute(self):
        self.assertEqual(
            self.view.process_colors(
                {'arch': {'attrs': {'colors': "grey:state in ('cancelled','done');blue:state in ('pending')"}},
                 'children': []
                }, {'state': 'done'}, {}),
            'grey')
    def test_color_multiple(self):
        self.assertEqual(
            self.view.process_colors(
                {'arch': {'attrs': {'colors': "grey:state in ('cancelled','done');blue:state in ('done')"}},
                 'children': []
                }, {'state': 'done'}, {}),
            'maroon')
