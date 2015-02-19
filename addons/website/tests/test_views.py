# -*- coding: utf-8 -*-
import itertools

import unittest2
from lxml import etree as ET, html
from lxml.html import builder as h

from openerp.tests import common

def attrs(**kwargs):
    return dict(('data-oe-%s' % key, str(value)) for key, value in kwargs.iteritems())
class TestViewSaving(common.TransactionCase):
    def eq(self, a, b):
        self.assertEqual(a.tag, b.tag)
        self.assertEqual(a.attrib, b.attrib)
        self.assertEqual((a.text or '').strip(), (b.text or '').strip())
        self.assertEqual((a.tail or '').strip(), (b.tail or '').strip())
        for ca, cb in itertools.izip_longest(a, b):
            self.eq(ca, cb)

    def setUp(self):
        super(TestViewSaving, self).setUp()
        self.arch = h.DIV(
            h.DIV(
                h.H3("Column 1"),
                h.UL(
                    h.LI("Item 1"),
                    h.LI("Item 2"),
                    h.LI("Item 3"))),
            h.DIV(
                h.H3("Column 2"),
                h.UL(
                    h.LI("Item 1"),
                    h.LI(h.SPAN("My Company", attrs(model='res.company', id=1, field='name', type='char'))),
                    h.LI(h.SPAN("+00 00 000 00 0 000", attrs(model='res.company', id=1, field='phone', type='char')))
                ))
        )
        self.view_id = self.env['ir.ui.view'].create({
            'name': "Test View",
            'type': 'qweb',
            'arch': ET.tostring(self.arch, encoding='utf-8').decode('utf-8')
        }).id

    def test_embedded_extraction(self):
        fields = self.env['ir.ui.view'].extract_embedded_fields(
            self.arch)

        expect = [
            h.SPAN("My Company", attrs(model='res.company', id=1, field='name', type='char')),
            h.SPAN("+00 00 000 00 0 000", attrs(model='res.company', id=1, field='phone', type='char')),
        ]
        for actual, expected in itertools.izip_longest(fields, expect):
            self.eq(actual, expected)

    def test_embedded_save(self):
        embedded = h.SPAN("+00 00 000 00 0 000", attrs(
            model='res.company', id=1, field='phone', type='char'))

        self.env['ir.ui.view'].save_embedded_field(embedded)

        company = self.env['res.company'].browse(1)
        self.assertEqual(company.phone, "+00 00 000 00 0 000")

    @unittest2.skip("save conflict for embedded (saved by third party or previous version in page) not implemented")
    def test_embedded_conflict(self):
        e1 = h.SPAN("My Company", attrs(model='res.company', id=1, field='name'))
        e2 = h.SPAN("Leeroy Jenkins", attrs(model='res.company', id=1, field='name'))

        View = self.env['ir.ui.view']

        View.save_embedded_field(e1)
        # FIXME: more precise exception
        with self.assertRaises(Exception):
            View.save_embedded_field(e2)

    def test_embedded_to_field_ref(self):
        View = self.env['ir.ui.view']
        embedded = h.SPAN("My Company", attrs(expression="bob"))
        self.eq(
            View.to_field_ref(embedded),
            h.SPAN({'t-field': 'bob'})
        )

    def test_to_field_ref_keep_attributes(self):
        View = self.env['ir.ui.view']

        att = attrs(expression="bob", model="res.company", id=1, field="name")
        att['id'] = "whop"
        att['class'] = "foo bar"
        embedded = h.SPAN("My Company", att)

        self.eq(View.to_field_ref(embedded),
                h.SPAN({'t-field': 'bob', 'class': 'foo bar', 'id': 'whop'}))

    def test_replace_arch(self):
        replacement = h.P("Wheee")

        result = self.env['ir.ui.view'].replace_arch_section(
            self.view_id, None, replacement)

        self.eq(result, h.DIV("Wheee"))

    def test_replace_arch_2(self):
        replacement = h.DIV(h.P("Wheee"))

        result = self.env['ir.ui.view'].replace_arch_section(
            self.view_id, None, replacement)

        self.eq(result, replacement)

    def test_fixup_arch(self):
        replacement = h.H1("I am the greatest title alive!")

        result = self.env['ir.ui.view'].replace_arch_section(
            self.view_id, '/div/div[1]/h3',
            replacement)

        self.eq(result, h.DIV(
            h.DIV(
                h.H3("I am the greatest title alive!"),
                h.UL(
                    h.LI("Item 1"),
                    h.LI("Item 2"),
                    h.LI("Item 3"))),
            h.DIV(
                h.H3("Column 2"),
                h.UL(
                    h.LI("Item 1"),
                    h.LI(h.SPAN("My Company", attrs(model='res.company', id=1, field='name', type='char'))),
                    h.LI(h.SPAN("+00 00 000 00 0 000", attrs(model='res.company', id=1, field='phone', type='char')))
                ))
        ))

    def test_multiple_xpath_matches(self):
        with self.assertRaises(ValueError):
            self.env['ir.ui.view'].replace_arch_section(
                self.view_id, '/div/div/h3',
                h.H6("Lol nope"))

    def test_save(self):
        Company = self.env['res.company']
        View = self.env['ir.ui.view']

        replacement = ET.tostring(h.DIV(
            h.H3("Column 2"),
            h.UL(
                h.LI("wob wob wob"),
                h.LI(h.SPAN("Acme Corporation", attrs(model='res.company', id=1, field='name', expression="bob", type='char'))),
                h.LI(h.SPAN("+12 3456789", attrs(model='res.company', id=1, field='phone', expression="edmund", type='char'))),
            )
        ), encoding='utf-8')
        View.save(res_id=self.view_id, value=replacement,
                  xpath='/div/div[2]')

        company = Company.browse(1)
        self.assertEqual(company.name, "Acme Corporation")
        self.assertEqual(company.phone, "+12 3456789")
        self.eq(
            ET.fromstring(View.browse(self.view_id).arch.encode('utf-8')),
            h.DIV(
                h.DIV(
                    h.H3("Column 1"),
                    h.UL(
                        h.LI("Item 1"),
                        h.LI("Item 2"),
                        h.LI("Item 3"))),
                h.DIV(
                    h.H3("Column 2"),
                    h.UL(
                        h.LI("wob wob wob"),
                        h.LI(h.SPAN({'t-field': "bob"})),
                        h.LI(h.SPAN({'t-field': "edmund"}))
                    ))
            )
        )

    def test_save_only_embedded(self):
        Company = self.env['res.company']
        company_id = 1
        Company.browse(company_id).write({'name': "Foo Corporation"})

        node = html.tostring(h.SPAN(
            "Acme Corporation",
            attrs(model='res.company', id=company_id, field="name", expression='bob', type='char')))

        self.env['ir.ui.view'].save(res_id=company_id,value=node)

        company = Company.browse(company_id)
        self.assertEqual(company.name, "Acme Corporation")


    def test_field_tail(self):
        View = self.env['ir.ui.view']
        replacement = ET.tostring(
            h.LI(h.SPAN("+12 3456789", attrs(
                        model='res.company', id=1, type='char',
                        field='phone', expression="edmund")),
                 "whop whop"
        ), encoding="utf-8")
        View.save(res_id = self.view_id, value=replacement,
                  xpath='/div/div[2]/ul/li[3]')

        self.eq(
            ET.fromstring(View.browse(self.view_id).arch.encode('utf-8')),
            h.DIV(
                h.DIV(
                    h.H3("Column 1"),
                    h.UL(
                        h.LI("Item 1"),
                        h.LI("Item 2"),
                        h.LI("Item 3"))),
                h.DIV(
                    h.H3("Column 2"),
                    h.UL(
                        h.LI("Item 1"),
                        h.LI(h.SPAN("My Company", attrs(model='res.company', id=1, field='name', type='char'))),
                        h.LI(h.SPAN({'t-field': "edmund"}), "whop whop"),
                    ))
            )
        )
