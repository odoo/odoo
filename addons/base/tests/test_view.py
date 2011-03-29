import xml.etree.ElementTree
import mock

import unittest2

import base.controllers.main
import openerpweb.nonliterals
import openerpweb.openerpweb

#noinspection PyCompatibility
class ViewTest(unittest2.TestCase):
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

    def test_convert_literal_domain(self):
        e = xml.etree.ElementTree.Element(
            'field', domain="[('somefield', '=', 3)]")
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
            'field', context="{'some_prop':  3}")
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
