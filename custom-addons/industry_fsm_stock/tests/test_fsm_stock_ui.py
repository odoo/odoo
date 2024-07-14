# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import tagged, HttpCase


@tagged('post_install', '-at_install')
class TestFsmStockUI(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Customer Task',
            'email': 'customer@task.com',
            'phone': '42',
        })
        cls.user_admin = cls.env.ref('base.user_admin')
        cls.fsm_project = cls.env.ref('industry_fsm.fsm_project')
        today = fields.Date.context_today(cls.fsm_project)
        cls.task = cls.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Fsm task',
            'user_ids': cls.user_admin,
            'partner_id': cls.partner.id,
            'project_id': cls.fsm_project.id,
            'planned_date_begin': today,
            'date_deadline': today + relativedelta(days=1),
        })
        # We ensure that the products we are creating for the test are displayed first
        # so that the test is not affected by the paging and the presence of demo data.
        exiting_products = cls.env['product.product'].search([('priority', '!=', '0')])
        exiting_products.write({'priority': '0'})
        cls.product_not_lot, cls.product_lot = cls.env['product.product'].create([
            {
                'name': 'Product A',
                'invoice_policy': 'delivery',
                'list_price': 885.0,
                'type': 'product',
                'priority': '1',
            }, {
                'name': 'Product B',
                'list_price': 2950.0,
                'type': 'product',
                'invoice_policy': 'delivery',
                'taxes_id': False,
                'tracking': 'lot',
                'priority': '1',
            },
        ])
        cls.lot_id1 = cls.env['stock.lot'].create({
            'product_id': cls.product_lot.id,
            'name': 'Lot_1',
            'company_id': cls.env.company.id,
        })
        cls.warehouse_A = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)
        if not cls.warehouse_A:
            cls.warehouse_A, cls.warehouse_B = cls.env['stock.warehouse'].create([{
                'name': 'WH A', 'code': 'WHA',
                'company_id': cls.env.company.id,
                'partner_id': cls.env.company.partner_id.id,
            }, {
                'name': 'WH B', 'code': 'WHB',
                'company_id': cls.env.company.id,
                'partner_id': cls.env.company.partner_id.id,
            }])
        else:
            cls.warehouse_B = cls.env['stock.warehouse'].create({
                'name': 'WH B', 'code': 'WHB',
                'company_id': cls.env.company.id,
                'partner_id': cls.env.company.partner_id.id,
            })
        quants_vals_list = []
        for warehouse in [cls.warehouse_A, cls.warehouse_B]:
            quants_vals_list.append({
                'product_id': cls.product_not_lot.id,
                'inventory_quantity': 4,
                'location_id': warehouse.lot_stock_id.id,
            })
        for warehouse in [cls.warehouse_A, cls.warehouse_B]:
            quants_vals_list.append({
                'product_id': cls.product_lot.id,
                'inventory_quantity': 2,
                'lot_id': cls.lot_id1.id,
                'location_id': warehouse.lot_stock_id.id,
            })
        quants = cls.env['stock.quant'].with_context(inventory_mode=True).create(quants_vals_list)
        quants.action_apply_inventory()

    def test_ui(self):
        self.user_admin.write({'property_warehouse_id': self.warehouse_A.id})
        # The group and the TZ of the user_admin are set, for in case of a db installed without demo-data, these are not correctly set.
        self.user_admin.groups_id += self.env.ref('stock.group_production_lot')
        if not self.user_admin.tz:
            self.user_admin.tz = "Europe/Brussels"
        self.start_tour('/web', 'industry_fsm_stock_test_tour', login=self.user_admin.login)
