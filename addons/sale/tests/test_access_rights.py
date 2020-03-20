# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from .test_sale_common import TestCommonSaleNoChart


@tagged('post_install', '-at_install')
class TestAccessRights(TestCommonSaleNoChart):

    def setUp(self):
        super(TestAccessRights, self).setUp()

        Users = self.env['res.users'].with_context(no_reset_password=True)

        group_user = self.env.ref('sales_team.group_sale_salesman')
        # Create a users
        self.user_manager = Users.create({
            'name': 'Andrew Manager',
            'login': 'manager',
            'email': 'a.m@example.com',
            'groups_id': [(6, 0, [self.env.ref('sales_team.group_sale_manager').id])]
        })
        self.user_salesperson = Users.create({
            'name': 'Mark User',
            'login': 'user',
            'email': 'm.u@example.com',
            'groups_id': [(6, 0, [group_user.id])]
        })
        self.user_salesperson_1 = Users.create({
            'name': 'Noemie User',
            'login': 'noemie',
            'email': 'n.n@example.com',
            'groups_id': [(6, 0, [group_user.id])]
        })
        self.user_portal = Users.create({
            'name': 'Chell Gladys',
            'login': 'chell',
            'email': 'chell@gladys.portal',
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])]
        })
        self.user_employee = Users.create({
            'name': 'Bert Tartignole',
            'login': 'bert',
            'email': 'b.t@example.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])]
        })

        # Create a Sales Team
        self.sales_channel = self.env['crm.team'].with_context(tracking_disable=True).create({
            'name': 'Test Channel',
        })

        # Create the SO with a specific salesperson
        self.order = self.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner_customer_usd.id,
        })

    def test_access_sales_manager(self):
        """ Test sales manager's access rights """
        SaleOrder = self.env['sale.order'].with_context(tracking_disable=True)
        # Manager can see the SO which is assigned to another salesperson
        self.order.with_user(self.user_manager).read()
        # Manager can change a salesperson of the SO
        self.order.with_user(self.user_manager).write({'user_id': self.user_salesperson_1.id})
        # Manager can create the SO for other salesperson
        sale_order = SaleOrder.with_user(self.user_manager).create({
            'partner_id': self.partner_customer_usd.id,
            'user_id': self.user_salesperson_1.id
        })
        self.assertIn(sale_order.id, SaleOrder.search([]).ids, 'Sales manager should be able to create the SO of other salesperson')
        # Manager can confirm the SO
        sale_order.with_user(self.user_manager).action_confirm()
        # Manager can not delete confirmed SO
        with self.assertRaises(UserError):
            sale_order.with_user(self.user_manager).unlink()
        # Manager can delete the SO of other salesperson if SO is in 'draft' or 'cancel' state
        self.order.with_user(self.user_manager).unlink()
        self.assertNotIn(self.order.id, SaleOrder.search([]).ids, 'Sales manager should be able to delete the SO')

        # Manager can create a Sales Team
        india_channel = self.env['crm.team'].with_context(tracking_disable=True).with_user(self.user_manager).create({
            'name': 'India',
        })
        self.assertIn(india_channel.id, self.env['crm.team'].search([]).ids, 'Sales manager should be able to create a Sales Team')
        # Manager can edit a Sales Team
        india_channel.with_user(self.user_manager).write({'name': 'new_india'})
        self.assertEqual(india_channel.name, 'new_india', 'Sales manager should be able to edit a Sales Team')
        # Manager can delete a Sales Team
        india_channel.with_user(self.user_manager).unlink()
        self.assertNotIn(india_channel.id, self.env['crm.team'].search([]).ids, 'Sales manager should be able to delete a Sales Team')

    def test_access_sales_person(self):
        """ Test Salesperson's access rights """
        # Salesperson can see only their own sales order
        with self.assertRaises(AccessError):
            self.order.with_user(self.user_salesperson_1).read()
        # Now assign the SO to themselves
        self.order.write({'user_id': self.user_salesperson_1.id})
        self.order.with_user(self.user_salesperson_1).read()
        # Salesperson can change a Sales Team of SO
        self.order.with_user(self.user_salesperson_1).write({'team_id': self.sales_channel.id})
        # Salesperson can't create the SO of other salesperson
        with self.assertRaises(AccessError):
            self.env['sale.order'].with_user(self.user_salesperson_1).create({
                'partner_id': self.partner_customer_usd.id,
                'user_id': self.user_salesperson.id
            })
        # Salesperson can't delete the SO
        with self.assertRaises(AccessError):
            self.order.with_user(self.user_salesperson_1).unlink()
        # Salesperson can confirm the SO
        self.order.with_user(self.user_salesperson_1).action_confirm()

    def test_access_portal_user(self):
        """ Test portal user's access rights """
        # Portal user can see the confirmed SO for which they are assigned as a customer
        with self.assertRaises(AccessError):
            self.order.with_user(self.user_portal).read()

        self.order.write({'partner_id': self.user_portal.partner_id.id})
        self.order.action_confirm()
        # Portal user can't edit the SO
        with self.assertRaises(AccessError):
            self.order.with_user(self.user_portal).write({'team_id': self.sales_channel.id})
        # Portal user can't create the SO
        with self.assertRaises(AccessError):
            self.env['sale.order'].with_user(self.user_portal).create({
                'partner_id': self.partner_customer_usd.id,
            })
        # Portal user can't delete the SO which is in 'draft' or 'cancel' state
        self.order.action_cancel()
        with self.assertRaises(AccessError):
            self.order.with_user(self.user_portal).unlink()

    def test_access_employee(self):
        """ Test classic employee's access rights """
        # Employee can't see any SO
        with self.assertRaises(AccessError):
            self.order.with_user(self.user_employee).read()
        # Employee can't edit the SO
        with self.assertRaises(AccessError):
            self.order.with_user(self.user_employee).write({'team_id': self.sales_channel.id})
        # Employee can't create the SO
        with self.assertRaises(AccessError):
            self.env['sale.order'].with_user(self.user_employee).create({
                'partner_id': self.partner_customer_usd.id,
            })
        # Employee can't delete the SO
        with self.assertRaises(AccessError):
            self.order.with_user(self.user_employee).unlink()
