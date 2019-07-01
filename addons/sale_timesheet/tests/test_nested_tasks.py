# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo.addons.sale.tests.test_sale_order import TestSaleOrder
from odoo.tests.common import tagged

from unittest import skip

@tagged('max')
class TestNestedTaskUpdate(TestSaleOrder):

    @classmethod
    def setUpClass(cls):
        super(TestNestedTaskUpdate, cls).setUpClass()
        cls.user = cls.env['res.users'].search([('id', '!=', cls.partner_customer_usd.user_id.id)], limit=1)

    #----------------------------------
    #
    # When creating tasks that have a parent_id, they pick some values from  their parent
    #
    #----------------------------------

    def test_creating_subtask_user_id_on_parent_dont_go_on_child(self):
        parent = self.env['project.task'].create({'name': 'parent', 'user_id': self.user.id})
        child = self.env['project.task'].create({'name': 'child', 'parent_id': parent.id, 'user_id': False})
        self.assertFalse(child.user_id)

    def test_creating_subtask_partner_id_on_parent_goes_on_child(self):
        parent = self.env['project.task'].create({'name': 'parent', 'partner_id': self.user.partner_id.id})
        child = self.env['project.task'].create({'name': 'child', 'partner_id': False, 'parent_id': parent.id})
        self.assertEqual(child.partner_id, self.user.partner_id)

    def test_creating_subtask_email_from_on_parent_goes_on_child(self):
        parent = self.env['project.task'].create({'name': 'parent', 'email_from': 'a@c.be'})
        child = self.env['project.task'].create({'name': 'child', 'parent_id': parent.id})
        self.assertEqual(child.email_from, 'a@c.be')

    def test_creating_subtask_sale_line_id_on_parent_goes_on_child_if_same_partner_in_values(self):
        parent = self.env['project.task'].create({'name': 'parent', 'partner_id': self.partner_customer_usd.id, 'sale_line_id': self.sol_serv_order.id})
        child = self.env['project.task'].create({'name': 'child', 'partner_id': self.partner_customer_usd.id, 'parent_id': parent.id})
        self.assertEqual(child.sale_line_id, parent.sale_line_id)
        parent.write({'sale_line_id': False})
        self.assertEqual(child.sale_line_id, self.sol_serv_order)

    def test_creating_subtask_sale_line_id_on_parent_goes_on_child_with_partner_if_not_in_values(self):
        parent = self.env['project.task'].create({'name': 'parent', 'partner_id': self.partner_customer_usd.id, 'sale_line_id': self.sol_serv_order.id})
        child = self.env['project.task'].create({'name': 'child', 'parent_id': parent.id})
        self.assertEqual(child.partner_id, parent.partner_id)
        self.assertEqual(child.sale_line_id, parent.sale_line_id)

    def test_creating_subtask_sale_line_id_on_parent_dont_go_on_child_if_other_partner(self):
        parent = self.env['project.task'].create({'name': 'parent', 'partner_id': self.partner_customer_usd.id, 'sale_line_id': self.sol_serv_order.id})
        child = self.env['project.task'].create({'name': 'child', 'partner_id': self.user.partner_id.id, 'parent_id': parent.id})
        self.assertFalse(child.sale_line_id)
        self.assertNotEqual(child.partner_id, parent.partner_id)

    #----------------------------------------
    #
    #   When writing on a parent task, some values adapt on their children
    #
    #----------------------------------------

    def test_write_user_id_on_parent_write_on_child(self):
        parent = self.env['project.task'].create({'name': 'parent', 'user_id': False})
        child = self.env['project.task'].create({'name': 'child', 'user_id': False, 'parent_id': parent.id})
        self.assertFalse(child.user_id)
        parent.write({'user_id': self.user.id})
        self.assertEqual(child.user_id, parent.user_id)
        parent.write({'user_id': False})
        self.assertEqual(child.user_id, self.user)

    def test_write_partner_id_on_parent_write_on_child(self):
        parent = self.env['project.task'].create({'name': 'parent', 'partner_id': False})
        child = self.env['project.task'].create({'name': 'child', 'partner_id': False, 'parent_id': parent.id})
        self.assertFalse(child.partner_id)
        parent.write({'partner_id': self.user.partner_id.id})
        self.assertEqual(child.partner_id, parent.partner_id)
        parent.write({'partner_id': False})
        self.assertEqual(child.partner_id, self.user.partner_id)

    def test_write_email_from_on_parent_write_on_child(self):
        parent = self.env['project.task'].create({'name': 'parent'})
        child = self.env['project.task'].create({'name': 'child', 'parent_id': parent.id})
        self.assertFalse(child.email_from)
        parent.write({'email_from': 'a@c.be'})
        self.assertEqual(child.email_from, parent.email_from)
        parent.write({'email_from': ''})
        self.assertEqual(child.email_from, 'a@c.be')

    def test_write_sale_line_id_on_parent_write_on_child_if_same_partner(self):
        parent = self.env['project.task'].create({'name': 'parent', 'partner_id': self.partner_customer_usd.id})
        child = self.env['project.task'].create({'name': 'child', 'parent_id': parent.id, 'partner_id': self.partner_customer_usd.id})
        self.assertFalse(child.sale_line_id)
        parent.write({'sale_line_id': self.sol_serv_order.id})
        self.assertEqual(child.sale_line_id, parent.sale_line_id)
        parent.write({'sale_line_id': False})
        self.assertEqual(child.sale_line_id, self.sol_serv_order)

    def test_write_sale_line_id_on_parent_write_on_child_with_partner_if_not_set(self):
        parent = self.env['project.task'].create({'name': 'parent', 'partner_id': self.partner_customer_usd.id})
        child = self.env['project.task'].create({'name': 'child', 'parent_id': parent.id})
        self.assertFalse(child.sale_line_id)
        parent.write({'sale_line_id': self.sol_serv_order.id})
        self.assertEqual(child.sale_line_id, parent.sale_line_id)
        self.assertEqual(child.partner_id, self.partner_customer_usd)
        parent.write({'sale_line_id': False})
        self.assertEqual(child.sale_line_id, self.sol_serv_order)

    def test_write_sale_line_id_on_parent_dont_write_on_child_if_other_partner(self):
        parent = self.env['project.task'].create({'name': 'parent', 'partner_id': self.partner_customer_usd.id})
        child = self.env['project.task'].create({'name': 'child', 'parent_id': parent.id, 'partner_id': self.user.partner_id.id})
        self.assertFalse(child.sale_line_id)
        parent.write({'sale_line_id': self.sol_serv_order.id})
        self.assertFalse(child.sale_line_id)

    #----------------------------------
    #
    #   When linking two existent task, some values go on the child
    #
    #----------------------------------

    def test_linking_user_id_on_parent_dont_write_on_child(self):
        parent = self.env['project.task'].create({'name': 'parent', 'user_id': self.user.id})
        child = self.env['project.task'].create({'name': 'child', 'user_id': False})
        self.assertFalse(child.user_id)
        child.write({'parent_id': parent.id})
        self.assertFalse(child.user_id)

    def test_linking_partner_id_on_parent_write_on_child(self):
        parent = self.env['project.task'].create({'name': 'parent', 'partner_id': self.user.partner_id.id})
        child = self.env['project.task'].create({'name': 'child', 'partner_id': False})
        self.assertFalse(child.partner_id)
        child.write({'parent_id': parent.id})
        self.assertEqual(child.partner_id, self.user.partner_id)

    def test_linking_email_from_on_parent_write_on_child(self):
        parent = self.env['project.task'].create({'name': 'parent', 'email_from': 'a@c.be'})
        child = self.env['project.task'].create({'name': 'child', 'email_from': False})
        self.assertFalse(child.email_from)
        child.write({'parent_id': parent.id})
        self.assertEqual(child.email_from, 'a@c.be')

    def test_linking_sale_line_id_on_parent_write_on_child_if_same_partner(self):
        parent = self.env['project.task'].create({'name': 'parent', 'partner_id': self.partner_customer_usd.id, 'sale_line_id': self.sol_serv_order.id})
        child = self.env['project.task'].create({'name': 'child', 'partner_id': self.partner_customer_usd.id})
        self.assertFalse(child.sale_line_id)
        child.write({'parent_id': parent.id})
        self.assertEqual(child.sale_line_id, parent.sale_line_id)
        parent.write({'sale_line_id': False})
        self.assertEqual(child.sale_line_id, self.sol_serv_order)

    def test_linking_sale_line_id_on_parent_write_on_child_with_partner_if_not_set(self):
        parent = self.env['project.task'].create({'name': 'parent', 'partner_id': self.partner_customer_usd.id, 'sale_line_id': self.sol_serv_order.id})
        child = self.env['project.task'].create({'name': 'child', 'partner_id': False})
        self.assertFalse(child.sale_line_id)
        self.assertFalse(child.partner_id)
        child.write({'parent_id': parent.id})
        self.assertEqual(child.partner_id, parent.partner_id)
        self.assertEqual(child.sale_line_id, parent.sale_line_id)

    def test_linking_sale_line_id_on_parent_write_dont_child_if_other_partner(self):
        parent = self.env['project.task'].create({'name': 'parent', 'partner_id': self.partner_customer_usd.id, 'sale_line_id': self.sol_serv_order.id})
        child = self.env['project.task'].create({'name': 'child', 'partner_id': self.user.partner_id.id})
        self.assertFalse(child.sale_line_id)
        self.assertNotEqual(child.partner_id, parent.partner_id)
        child.write({'parent_id': parent.id})
        self.assertFalse(child.sale_line_id)

    def test_writing_on_parent_with_multiple_tasks(self):
        parent = self.env['project.task'].create({'name': 'parent', 'user_id': False})
        children_values = [{'name': 'child%s' % i, 'user_id': False, 'parent_id': parent.id} for i in range(5)]
        children = self.env['project.task'].create(children_values)
        # test writing user_id
        for child in children:
            self.assertFalse(child.user_id)
        parent.write({'user_id': self.user.id})
        for child in children:
            self.assertEqual(child.user_id, self.user)
        # test writing sale_line_id
        for child in children:
            self.assertFalse(child.sale_line_id)
        parent.write({'sale_line_id': self.sol_serv_order.id})
        for child in children:
            self.assertEqual(child.sale_line_id, self.sol_serv_order)

    def test_linking_on_parent_with_multiple_tasks(self):
        parent = self.env['project.task'].create({'name': 'parent', 'partner_id': self.partner_customer_usd.id, 'sale_line_id': self.sol_serv_order.id, 'user_id': self.user.id})
        children_values = [{'name': 'child%s' % i, 'user_id': False} for i in range(5)]
        children = self.env['project.task'].create(children_values)
        # test writing user_id and sale_line_id

        for child in children:
            self.assertFalse(child.user_id)
            self.assertFalse(child.sale_line_id)

        children.write({'parent_id': parent.id})

        for child in children:
            self.assertEqual(child.sale_line_id, self.sol_serv_order)
            self.assertFalse(child.user_id)
