# -*- coding: utf-8 -*-
import cgi

from lxml import etree

from openerp.tests import common
from openerp.addons.base.ir import ir_qweb

class TestQWebTField(common.TransactionCase):
    def setUp(self):
        super(TestQWebTField, self).setUp()
        self.engine = self.registry('ir.qweb')

    def context(self, values):
        return ir_qweb.QWebContext(
            self.cr, self.uid, values, context={'inherit_branding': True})

    def test_trivial(self):
        field = etree.Element('span', {'t-field': u'company.name'})

        Companies = self.registry('res.company')
        company_id = Companies.create(self.cr, self.uid, {
            'name': "My Test Company"
        })
        result = self.engine.render_node(field, self.context({
            'company': Companies.browse(self.cr, self.uid, company_id),
        }))

        self.assertEqual(
            result,
            '<span data-oe-model="res.company" data-oe-id="%d" '
                  'data-oe-field="name" data-oe-type="char" '
                  'data-oe-expression="company.name">%s</span>' % (
                company_id,
                "My Test Company",))

    def test_i18n(self):
        field = etree.Element('span', {'t-field': u'company.name'})

        Companies = self.registry('res.company')
        s = u"Testing «ταБЬℓσ»: 1<2 & 4+1>3, now 20% off!"
        company_id = Companies.create(self.cr, self.uid, {
            'name': s,
        })
        result = self.engine.render_node(field, self.context({
            'company': Companies.browse(self.cr, self.uid, company_id),
        }))

        self.assertEqual(
            result,
            '<span data-oe-model="res.company" data-oe-id="%d" '
                  'data-oe-field="name" data-oe-type="char" '
                  'data-oe-expression="company.name">%s</span>' % (
                company_id,
                cgi.escape(s.encode('utf-8')),))

    def test_reject_crummy_tags(self):
        field = etree.Element('td', {'t-field': u'company.name'})

        with self.assertRaisesRegexp(
                AssertionError,
                r'^RTE widgets do not work correctly'):
            self.engine.render_node(field, self.context({
                'company': None
            }))

    def test_reject_t_tag(self):
        field = etree.Element('t', {'t-field': u'company.name'})

        with self.assertRaisesRegexp(
                AssertionError,
                r'^t-field can not be used on a t element'):
            self.engine.render_node(field, self.context({
                'company': None
            }))
