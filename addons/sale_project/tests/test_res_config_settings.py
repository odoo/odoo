# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged

from .common import TestSaleProjectCommon


@tagged('post_install', '-at_install')
class TestResConfigSettings(TestSaleProjectCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner_b.id,
            'partner_invoice_id': cls.partner_b.id,
            'partner_shipping_id': cls.partner_b.id,
            'order_line': [
                Command.create({
                    'product_id': cls.product_milestone.id,
                    'product_uom_qty': 3,
                }),
                Command.create({
                    'product_id': cls.product_delivery_manual1.id,
                    'product_uom_qty': 2,
                })
            ]
        })
        cls.product_milestone_sale_line = cls.sale_order.order_line.filtered(lambda sol: sol.product_id == cls.product_milestone)
        cls.product_delivery_manual1_sale_line = cls.sale_order.order_line.filtered(lambda sol: sol.product_id == cls.product_delivery_manual1)
        cls.sale_order.action_confirm()

        cls.milestone = cls.env['project.milestone'].create({
            'name': 'Test Milestone',
            'sale_line_id': cls.product_milestone_sale_line.id,
            'project_id': cls.project_global.id,
        })

    def test_disable_and_enable_project_milestone_feature(self):
        self.assertTrue(self.env.user.has_group('project.group_project_milestone'), 'The Project Milestones feature should be enabled.')

        self.set_project_milestone_feature(False)
        self.assertFalse(self.env.user.has_group('project.group_project_milestone'), 'The Project Milestones feature should be disabled.')
        product_milestones = self.product_milestone + self.product_milestone2
        self.assertEqual(
            product_milestones.mapped('service_policy'),
            ['delivered_manual'] * 2,
            'Both milestone products should become a manual product when the project milestones feature is disabled')
        self.assertEqual(
            product_milestones.mapped('service_type'),
            ['manual'] * 2,
            'Both milestone products should become a manual product when the project milestones feature is disabled')
        self.assertEqual(
            self.product_milestone_sale_line.qty_delivered_method,
            'manual',
            'The quantity delivered method of SOL containing milestone product should be changed to manual when the project milestones feature is disabled')

        # Since the quantity delivered manual is manual then the user can manually change the quantity delivered
        self.product_milestone_sale_line.qty_delivered = 2

        # Enable the project milestones feature
        self.set_project_milestone_feature(True)

        self.assertEqual(
            self.product_milestone.service_policy,
            'delivered_milestones',
            'The product has been updated and considered as milestones product since a SOL containing this product is linked to a milestone.')
        self.assertEqual(
            self.product_milestone.service_type,
            'milestones',
            'The product has been updated and considered as milestones product since a SOL containing this product is linked to a milestone.')
        self.assertEqual(
            self.product_milestone2.service_policy,
            'delivered_manual',
            'The product should not be updated since we cannot assume this product was a milestone when the feature'
            ' was enabled because no SOL with this product is linked to a milestone.')
        self.assertEqual(
            self.product_milestone2.service_type,
            'manual',
            'The product should not be updated since we cannot assume this product was a milestone when the feature'
            ' was enabled because no SOL with this product is linked to a milestone.')
        self.assertEqual(
            self.product_milestone_sale_line.qty_delivered_method,
            'manual',
            'The quantity delivered method of SOL containing milestone product should keep the same quantity delivered method even if the project milestones feature is renabled.')
        self.assertEqual(self.product_milestone_sale_line.qty_delivered, 2, 'The quantity delivered should be the one set by the user.')
