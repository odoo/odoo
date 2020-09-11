# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestAccessRights(TestSaleCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company_data['default_user_salesman_2'] = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'default_user_salesman_2',
            'login': 'default_user_salesman_2.comp%s' % cls.company_data['company'].id,
            'email': 'default_user_salesman_2@example.com',
            'signature': '--\nMark',
            'notification_type': 'email',
            'groups_id': [(6, 0, cls.env.ref('sales_team.group_sale_salesman').ids)],
            'company_ids': [(6, 0, cls.company_data['company'].ids)],
            'company_id': cls.company_data['company'].id,
        })

        # Create the SO with a specific salesperson
        cls.order = cls.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': cls.partner_a.id,
            'user_id': cls.company_data['default_user_salesman'].id
        })

    def test_access_sales_manager(self):
        """ Test sales manager's access rights """
        SaleOrder = self.env['sale.order'].with_context(tracking_disable=True)
        # Manager can see the SO which is assigned to another salesperson
        self.order.read()
        # Manager can change a salesperson of the SO
        self.order.write({'user_id': self.company_data['default_user_salesman'].id})
        # Manager can create the SO for other salesperson
        sale_order = SaleOrder.create({
            'partner_id': self.partner_a.id,
            'user_id': self.company_data['default_user_salesman'].id
        })
        self.assertIn(sale_order.id, SaleOrder.search([]).ids, 'Sales manager should be able to create the SO of other salesperson')
        # Manager can confirm the SO
        sale_order.action_confirm()
        # Manager can not delete confirmed SO
        with self.assertRaises(UserError):
            sale_order.unlink()
        # Manager can delete the SO of other salesperson if SO is in 'draft' or 'cancel' state
        self.order.unlink()
        self.assertNotIn(self.order.id, SaleOrder.search([]).ids, 'Sales manager should be able to delete the SO')

        # Manager can create a Sales Team
        india_channel = self.env['crm.team'].with_context(tracking_disable=True).create({
            'name': 'India',
        })
        self.assertIn(india_channel.id, self.env['crm.team'].search([]).ids, 'Sales manager should be able to create a Sales Team')
        # Manager can edit a Sales Team
        india_channel.write({'name': 'new_india'})
        self.assertEqual(india_channel.name, 'new_india', 'Sales manager should be able to edit a Sales Team')
        # Manager can delete a Sales Team
        india_channel.unlink()
        self.assertNotIn(india_channel.id, self.env['crm.team'].search([]).ids, 'Sales manager should be able to delete a Sales Team')

    def test_access_sales_person(self):
        """ Test Salesperson's access rights """
        # Salesperson can see only their own sales order
        with self.assertRaises(AccessError):
            self.order.with_user(self.company_data['default_user_salesman_2']).read()
        # Now assign the SO to themselves
        self.order.write({'user_id': self.company_data['default_user_salesman_2'].id})
        self.order.with_user(self.company_data['default_user_salesman_2']).read()
        # Salesperson can change a Sales Team of SO
        self.order.with_user(self.company_data['default_user_salesman_2']).write({'team_id': self.company_data['default_sale_team'].id})
        # Salesperson can't create the SO of other salesperson
        with self.assertRaises(AccessError):
            self.env['sale.order'].with_user(self.company_data['default_user_salesman_2']).create({
                'partner_id': self.partner_a.id,
                'user_id': self.company_data['default_user_salesman'].id
            })
        # Salesperson can't delete the SO
        with self.assertRaises(AccessError):
            self.order.with_user(self.company_data['default_user_salesman_2']).unlink()
        # Salesperson can confirm the SO
        self.order.with_user(self.company_data['default_user_salesman_2']).action_confirm()

    def test_access_portal_user(self):
        """ Test portal user's access rights """
        # Portal user can see the confirmed SO for which they are assigned as a customer
        with self.assertRaises(AccessError):
            self.order.with_user(self.company_data['default_user_portal']).read()

        self.order.partner_id = self.company_data['default_user_portal'].partner_id
        self.order.action_confirm()
        # Portal user can't edit the SO
        with self.assertRaises(AccessError):
            self.order.with_user(self.company_data['default_user_portal']).write({'team_id': self.company_data['default_sale_team'].id})
        # Portal user can't create the SO
        with self.assertRaises(AccessError):
            self.env['sale.order'].with_user(self.company_data['default_user_portal']).create({
                'partner_id': self.partner_a.id,
            })
        # Portal user can't delete the SO which is in 'draft' or 'cancel' state
        self.order.action_cancel()
        with self.assertRaises(AccessError):
            self.order.with_user(self.company_data['default_user_portal']).unlink()

    def test_access_employee(self):
        """ Test classic employee's access rights """
        # Employee can't see any SO
        with self.assertRaises(AccessError):
            self.order.with_user(self.company_data['default_user_employee']).read()
        # Employee can't edit the SO
        with self.assertRaises(AccessError):
            self.order.with_user(self.company_data['default_user_employee']).write({'team_id': self.company_data['default_sale_team'].id})
        # Employee can't create the SO
        with self.assertRaises(AccessError):
            self.env['sale.order'].with_user(self.company_data['default_user_employee']).create({
                'partner_id': self.partner_a.id,
            })
        # Employee can't delete the SO
        with self.assertRaises(AccessError):
            self.order.with_user(self.company_data['default_user_employee']).unlink()

@tagged('post_install', '-at_install')
class TestAccessRightsControllers(HttpCase):

    def test_access_controller(self):

        portal_so = self.env.ref("sale.portal_sale_order_2").sudo()
        portal_so._portal_ensure_token()
        token = portal_so.access_token

        private_so = self.env.ref("sale.sale_order_1")

        self.authenticate(None, None)

        # Test public user can't print an order without a token
        req = self.url_open(
            url='/my/orders/%s?report_type=pdf' % portal_so.id,
            allow_redirects=False,
        )
        self.assertEqual(req.status_code, 302)

        # or with a random token
        req = self.url_open(
            url='/my/orders/%s?access_token=%s&report_type=pdf' % (
                portal_so.id,
                "foo",
            ),
            allow_redirects=False,
        )
        self.assertEqual(req.status_code, 302)

        # but works fine with the right token
        req = self.url_open(
            url='/my/orders/%s?access_token=%s&report_type=pdf' % (
                portal_so.id,
                token,
            ),
            allow_redirects=False,
        )
        self.assertEqual(req.status_code, 200)

        self.authenticate("portal", "portal")

        # do not need the token when logged in
        req = self.url_open(
            url='/my/orders/%s?report_type=pdf' % portal_so.id,
            allow_redirects=False,
        )
        self.assertEqual(req.status_code, 200)

        # but still can't access another order
        req = self.url_open(
            url='/my/orders/%s?report_type=pdf' % private_so.id,
            allow_redirects=False,
        )
        self.assertEqual(req.status_code, 302)
