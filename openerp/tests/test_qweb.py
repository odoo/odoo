# -*- coding: utf-8 -*-
from xml.dom import minidom as dom

import common

from ..tools import qweb

impl = dom.getDOMImplementation()
document = impl.createDocument(None, None, None)

class TestQWebTField(common.TransactionCase):
    def setUp(self):
        super(TestQWebTField, self).setUp()
        self.engine = qweb.QWebXml()

    def test_trivial(self):
        field = document.createElement('span')
        field.setAttribute('t-field', u'company.name')

        Companies = self.registry('res.company')
        company_id = Companies.create(self.cr, self.uid, {
            'name': "My Test Company"
        })
        root_company = Companies.browse(self.cr, self.uid, company_id)

        result = self.engine.render_node(field, {'company': root_company})

        self.assertEqual(
            result,
            '<span data-oe-model="res.company" data-oe-id="%d" '
                  'data-oe-field="name" data-oe-type="char" '
                  'data-oe-expression="company.name">%s</span>' % (
                company_id,
                "My Test Company",))

    def test_reject_crummy_tags(self):
        field = document.createElement('td')
        field.setAttribute('t-field', u'company.name')

        with self.assertRaisesRegexp(
                AssertionError,
                r'^RTE widgets do not work correctly'):
            self.engine.render_node(field, {'company': None})

    def test_reject_t_tag(self):
        field = document.createElement('t')
        field.setAttribute('t-field', u'company.name')

        with self.assertRaisesRegexp(
                AssertionError,
                r'^t-field can not be used on a t element'):
            self.engine.render_node(field, {'company': None})
