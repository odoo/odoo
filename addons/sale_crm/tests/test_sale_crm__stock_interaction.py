# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import unittest
from odoo.addons.crm.tests import common as crm_common
from odoo.fields import Command
from odoo.tests.common import tagged, users
from odoo.tests import tagged, Form


@tagged('post_install', '-at_install')
class TestSaleCrmStockInteraction(crm_common.TestCrmCommon):
    @classmethod
    def setUpClass(cls):
        super(TestSaleCrmStockInteraction, cls).setUpClass()
        if not cls.env['ir.module.module'].search_count([('name', '=', 'stock'), ('state', '=', 'installed')]):
            raise unittest.SkipTest("Skipping test because 'stock' module is not installed")
        cls.lead_1.write({
            'user_id': cls.user_sales_salesman.id,
        })

    @users('user_sales_salesman')
    def test_picking_creation_from_new_quotation(self):
        lead = self.lead_1.with_user(self.env.user)
        lead_action = lead.action_sale_quotations_new()
        quotation = self.env['sale.order'].browse(lead_action['res_id'])

        product = self.env['product.product'].sudo().create({
            'name': 'Test Product',
        })

        with Form(quotation.with_context({
            'default_opportunity_id': lead.id,
        })) as quotation_form:
            quotation_form.partner_id = self.env.user.partner_id
            with quotation_form.order_line.new() as line_form:
                line_form.product_id = product
                line_form.product_uom_qty = 1
            quotation = quotation_form.save()
            quotation.action_confirm()

        self.assertTrue(quotation.picking_ids)
        picking = quotation.picking_ids[0]

        with Form(self.env['stock.picking'].with_context({
            'default_group_id': picking.group_id.id,
            'default_opportunity_id': lead.id,
            'default_origin': quotation.name,
            'default_partner_id': quotation.partner_id.id,
            'default_picking_type_id': picking.picking_type_id.id,
        })) as form_new_picking:
            with form_new_picking.move_ids_without_package.new() as form_new_move:
                form_new_move.product_id = product
                form_new_move.product_uom_qty = 1
            new_picking = form_new_picking.save()
            new_picking.action_confirm()

        self.assertEqual(picking.group_id, new_picking.group_id)
