# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo.tests import Form, tagged

from .common import TestCommonSalePlanning

@tagged('post_install', '-at_install')
class TestSalePlanningProduct(TestCommonSalePlanning):

    def test_product_form(self):
        product_form = Form(self.env['product.product'])
        product_form.name = 'Home Help'
        product_form.type = 'service'
        product_form.planning_enabled = True
        product_form.planning_role_id = self.planning_role_junior

        product = product_form.save()

        self.assertEqual(product.type, 'service', 'Plannable services should have type \'service\'.')
        self.assertEqual(product.planning_enabled, True, 'Plannable services should be enabled.')
        self.assertEqual(product.planning_role_id, self.planning_role_junior, 'Plannable services should have a default role.')

    def test_product_form_failing(self):
        with self.assertRaises(AssertionError, msg='Plannable services should be a service product to be enabled.'):
            product_form = Form(self.env['product.product'])
            product_form.name = 'Home Help'
            product_form.type = 'consu'
            product_form.planning_enabled = True
            product_form.save()

        with self.assertRaises(AssertionError, msg='Plannable services should use an UoM within the %s category.' % self.env.ref('uom.uom_categ_wtime').name):
            product_form = Form(self.env['product.product'])
            product_form.name = 'Home Help'
            product_form.type = 'consu'
            product_form.planning_enabled = True
            product_form.uom_id = self.env.ref('uom.product_uom_cm')
            product_form.save()

        with self.assertRaises(AssertionError, msg="Should not accept a plannable service without a planning role. Planning Role is required"):
            product_form = Form(self.env['product.product'])
            product_form.name = 'Home Help'
            product_form.type = 'service'
            product_form.planning_enabled = True
            product_form.save()
