# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo.tests.common import SavepointCase


class TestUomField(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestUomField, cls).setUpClass()
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.product = cls.env['product.product'].create({
            'name': 'Product A',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })

    def test_unit_1(self):
        self.assertEqual(self.uom_unit.decimal_places, 3)

        line = self.env['test_uom.line'].create({
            'product_id': self.product.id,
            'uom_id': self.uom_unit.id,
            'qty': 1,
        })
        self.assertEqual(line.qty, 1)


        line = self.env['test_uom.line'].create({
            'product_id': self.product.id,
            'uom_id': self.uom_unit.id,
            'qty': 1.004,
        })
        self.assertEqual(line.qty, 1.004)

        line = self.env['test_uom.line'].create({
            'product_id': self.product.id,
            'uom_id': self.uom_unit.id,
            'qty': 1.0004,
        })
        self.assertEqual(line.qty, 1)

    def test_different_rounding_and_decimal_places_1(self):
        """Work with a uom having a rouding of 0.5 and thus a decimal places of 1"""
        self.uom_unit.rounding = 0.5

        line = self.env['test_uom.line'].create({
            'product_id': self.product.id,
            'uom_id': self.uom_unit.id,
            'qty': 0.999,
        })
        self.assertEqual(line.qty, 1)

        line = self.env['test_uom.line'].create({
            'product_id': self.product.id,
            'uom_id': self.uom_unit.id,
            'qty': 1.49,
        })
        self.assertEqual(line.qty, 1.5)

        line = self.env['test_uom.line'].create({
            'product_id': self.product.id,
            'uom_id': self.uom_unit.id,
            'qty': 1.501,
        })
        self.assertEqual(line.qty, 1.5)

    def test_qweb_field_unit_1(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': u"""
                <t t-name="base.dummy"><root><span t-field="line.qty" /></root></t>
            """
        })

        line = self.env['test_uom.line'].create({
            'product_id': self.product.id,
            'uom_id': self.uom_unit.id,
            'qty': 1,
        })
        text = etree.fromstring(view1.render(values={'line': line})).find('span').text
        self.assertEqual(text, u'1.000')

        line = self.env['test_uom.line'].create({
            'product_id': self.product.id,
            'uom_id': self.uom_unit.id,
            'qty': 1.004,
        })
        text = etree.fromstring(view1.render(values={'line': line})).find('span').text
        self.assertEqual(text, u'1.004')

        line = self.env['test_uom.line'].create({
            'product_id': self.product.id,
            'uom_id': self.uom_unit.id,
            'qty': 1.0004,
        })
        text = etree.fromstring(view1.render(values={'line': line})).find('span').text
        self.assertEqual(text, u'1.000')

    def test_qweb_field_different_rounding_and_decimal_places_1(self):
        """Work with a uom having a rouding of 0.5 and thus a decimal places of 1"""
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': u"""
                <t t-name="base.dummy"><root><span t-field="line.qty" /></root></t>
            """
        })
        self.uom_unit.rounding = 0.5

        line = self.env['test_uom.line'].create({
            'product_id': self.product.id,
            'uom_id': self.uom_unit.id,
            'qty': 0.999,
        })
        text = etree.fromstring(view1.render(values={'line': line})).find('span').text
        self.assertEqual(text, u'1.0')

        line = self.env['test_uom.line'].create({
            'product_id': self.product.id,
            'uom_id': self.uom_unit.id,
            'qty': 1.49,
        })
        text = etree.fromstring(view1.render(values={'line': line})).find('span').text
        self.assertEqual(text, u'1.5')

        line = self.env['test_uom.line'].create({
            'product_id': self.product.id,
            'uom_id': self.uom_unit.id,
            'qty': 1.501,
        })
        text = etree.fromstring(view1.render(values={'line': line})).find('span').text
        self.assertEqual(text, u'1.5')
