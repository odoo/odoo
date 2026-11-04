# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.base.tests.common import BaseUsersCommon
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestAccessRights(BaseUsersCommon, SaleCommon, MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.sale_user2 = cls.env['res.users'].create({
            'name': 'salesman_2',
            'login': 'salesman_2',
            'email': 'default_user_salesman_2@example.com',
            'signature': '--\nMark',
            'notification_type': 'email',
            'groups_id': [(6, 0, cls.group_sale_salesman.ids)],
        })

        # Create the SO with a specific salesperson
        cls.sale_order.user_id = cls.sale_user

    def test_access_sales_manager(self):
        """ Test sales manager's access rights """
        SaleOrder = self.env['sale.order'].with_user(self.sale_manager)
        so_as_sale_manager = SaleOrder.browse(self.sale_order.id)

        # Manager can see the SO which is assigned to another salesperson
        so_as_sale_manager.read()
        # Manager can change a salesperson of the SO
        so_as_sale_manager.write({'user_id': self.sale_user2.id})

        # Manager can create the SO for other salesperson
        sale_order = SaleOrder.create({
            'partner_id': self.partner.id,
            'user_id': self.sale_user.id
        })
        self.assertIn(
            sale_order.id, SaleOrder.search([]).ids,
            'Sales manager should be able to create the SO of other salesperson')
        # Manager can confirm the SO
        sale_order.action_confirm()
        # Manager can not delete confirmed SO
        with self.assertRaises(UserError), mute_logger('odoo.models.unlink'):
            sale_order.unlink()

        # Manager can delete the SO of other salesperson if SO is in 'draft' or 'cancel' state
        so_as_sale_manager.unlink()
        self.assertNotIn(
            so_as_sale_manager.id, SaleOrder.search([]).ids,
            'Sales manager should be able to delete the SO')

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_access_sales_person(self):
        """ Test Salesperson's access rights """
        SaleOrder = self.env['sale.order'].with_user(self.sale_user2)
        so_as_salesperson = SaleOrder.browse(self.sale_order.id)

        # Salesperson can see only their own sales order
        with self.assertRaises(AccessError):
            so_as_salesperson.read()

        # Now assign the SO to themselves
        # (using self.sale_order to do the change as superuser)
        self.sale_order.write({'user_id': self.sale_user2.id})

        # The salesperson is now able to read it
        so_as_salesperson.read()
        # Salesperson can change a Sales Team of SO
        so_as_salesperson.write({'team_id': self.sale_team.id})

        # Salesperson can't create a SO for other salesperson
        with self.assertRaises(AccessError):
            self.env['sale.order'].with_user(self.sale_user2).create({
                'partner_id': self.partner.id,
                'user_id': self.sale_user.id
            })

        # Salesperson can't delete Sale Orders
        with self.assertRaises(AccessError):
            so_as_salesperson.unlink()

        # Salesperson can confirm the SO
        so_as_salesperson.action_confirm()

        # Salesperson can't confirm the related move
        move_as_salesperson = so_as_salesperson._create_invoices().with_user(self.sale_user2)
        with self.assertRaises(AccessError):
            move_as_salesperson.action_post()

        move_as_salesperson.sudo().action_post()

        composer = self.env['account.move.send.wizard']\
            .with_user(self.sale_user2)\
            .with_context(active_model='account.move', active_ids=move_as_salesperson.ids)\
            .create({})

        # Salesperson can send & print
        with self.mock_mail_gateway(mail_unlink_sent=False):
            composer.action_send_and_print()

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_access_portal_user(self):
        """ Test portal user's access rights """
        SaleOrder = self.env['sale.order'].with_user(self.user_portal)
        so_as_portal_user = SaleOrder.browse(self.sale_order.id)

        # Portal user can see the confirmed SO for which they are assigned as a customer
        with self.assertRaises(AccessError):
            so_as_portal_user.read()

        self.sale_order.partner_id = self.user_portal.partner_id
        self.sale_order.action_confirm()
        # Portal user can't edit the SO
        with self.assertRaises(AccessError):
            so_as_portal_user.write({'team_id': self.sale_team.id})
        # Portal user can't create the SO
        with self.assertRaises(AccessError):
            SaleOrder.create({
                'partner_id': self.partner.id,
            })
        # Portal user can't delete the SO which is in 'draft' or 'cancel' state
        self.sale_order.action_cancel()
        with self.assertRaises(AccessError):
            so_as_portal_user.unlink()

    @mute_logger('odoo.addons.base.models.ir_model')
    def test_access_employee(self):
        """ Test classic employee's access rights """
        SaleOrder = self.env['sale.order'].with_user(self.user_internal)
        so_as_internal_user = SaleOrder.browse(self.sale_order.id)

        # Employee can't see any SO
        with self.assertRaises(AccessError):
            so_as_internal_user.read()
        # Employee can't edit the SO
        with self.assertRaises(AccessError):
            so_as_internal_user.write({'team_id': self.sale_team.id})
        # Employee can't create the SO
        with self.assertRaises(AccessError):
            SaleOrder.create({
                'partner_id': self.partner.id,
            })
        # Employee can't delete the SO
        with self.assertRaises(AccessError):
            so_as_internal_user.unlink()
