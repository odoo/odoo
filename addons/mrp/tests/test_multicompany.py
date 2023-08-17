# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common, Form
from odoo.exceptions import UserError


class TestMrpMulticompany(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        group_user = cls.env.ref('base.group_user')
        group_mrp_manager = cls.env.ref('mrp.group_mrp_manager')
        cls.company_a = cls.env['res.company'].create({'name': 'Company A'})
        cls.company_b = cls.env['res.company'].create({'name': 'Company B'})
        cls.warehouse_a = cls.env['stock.warehouse'].search([('company_id', '=', cls.company_a.id)], limit=1)
        cls.warehouse_b = cls.env['stock.warehouse'].search([('company_id', '=', cls.company_b.id)], limit=1)
        cls.stock_location_a = cls.warehouse_a.lot_stock_id
        cls.stock_location_b = cls.warehouse_b.lot_stock_id

        cls.user_a = cls.env['res.users'].create({
            'name': 'user company a with access to company b',
            'login': 'user a',
            'groups_id': [(6, 0, [group_user.id, group_mrp_manager.id])],
            'company_id': cls.company_a.id,
            'company_ids': [(6, 0, [cls.company_a.id, cls.company_b.id])]
        })
        cls.user_b = cls.env['res.users'].create({
            'name': 'user company a with access to company b',
            'login': 'user b',
            'groups_id': [(6, 0, [group_user.id, group_mrp_manager.id])],
            'company_id': cls.company_b.id,
            'company_ids': [(6, 0, [cls.company_a.id, cls.company_b.id])]
        })

    def test_bom_1(self):
        """Check it is not possible to use a product of Company B in a
        bom of Company A. """

        product_b = self.env['product.product'].create({
            'name': 'p1',
            'company_id': self.company_b.id,
        })
        with self.assertRaises(UserError):
            self.env['mrp.bom'].create({
                'product_id': product_b.id,
                'product_tmpl_id': product_b.product_tmpl_id.id,
                'company_id': self.company_a.id,
            })

    def test_bom_2(self):
        """Check it is not possible to use a product of Company B as a component
        in a bom of Company A. """

        product_a = self.env['product.product'].create({
            'name': 'p1',
            'company_id': self.company_a.id,
        })
        product_b = self.env['product.product'].create({
            'name': 'p2',
            'company_id': self.company_b.id,
        })
        with self.assertRaises(UserError):
            self.env['mrp.bom'].create({
                'product_id': product_a.id,
                'product_tmpl_id': product_b.product_tmpl_id.id,
                'company_id': self.company_a.id,
                'bom_line_ids': [(0, 0, {'product_id': product_b.id})]
            })

    def test_production_1(self):
        """Check it is not possible to confirm a production of Company B with
        product of Company A. """

        product_a = self.env['product.product'].create({
            'name': 'p1',
            'company_id': self.company_a.id,
        })
        mo = self.env['mrp.production'].create({
            'product_id': product_a.id,
            'product_uom_id': product_a.uom_id.id,
            'company_id': self.company_b.id,
        })
        with self.assertRaises(UserError):
            mo.action_confirm()

    def test_production_2(self):
        """Check that confirming a production in company b with user_a will create
        stock moves on company b. """

        product_a = self.env['product.product'].create({
            'name': 'p1',
            'company_id': self.company_a.id,
        })
        component_a = self.env['product.product'].create({
            'name': 'p2',
            'company_id': self.company_a.id,
        })
        self.env['mrp.bom'].create({
            'product_id': product_a.id,
            'product_tmpl_id': product_a.product_tmpl_id.id,
            'company_id': self.company_a.id,
            'bom_line_ids': [(0, 0, {'product_id': component_a.id})]
        })
        mo_form = Form(self.env['mrp.production'].with_user(self.user_a))
        mo_form.product_id = product_a
        mo = mo_form.save()
        mo.with_user(self.user_b).action_confirm()
        self.assertEqual(mo.move_raw_ids.company_id, self.company_a)
        self.assertEqual(mo.move_finished_ids.company_id, self.company_a)

    def test_product_produce_1(self):
        """Check that using a finished lot of company b in the produce wizard of a production
        of company a is not allowed """

        product = self.env['product.product'].create({
            'name': 'p1',
            'tracking': 'lot',
        })
        component = self.env['product.product'].create({
            'name': 'p2',
        })
        lot_b = self.env['stock.lot'].create({
            'product_id': product.id,
            'company_id': self.company_b.id,
        })
        self.env['mrp.bom'].create({
            'product_id': product.id,
            'product_tmpl_id': product.product_tmpl_id.id,
            'company_id': self.company_a.id,
            'bom_line_ids': [(0, 0, {'product_id': component.id})]
        })
        mo_form = Form(self.env['mrp.production'].with_user(self.user_a))
        mo_form.product_id = product
        # The mo must be confirmed, no longer in draft, in order for `lot_producing_id` to be visible in the view
        # <div class="o_row" invisible="state == 'draft' or product_tracking in ('none', False)">
        mo = mo_form.save()
        mo.action_confirm()
        mo_form = Form(mo)
        mo_form.lot_producing_id = lot_b
        mo = mo_form.save()
        with self.assertRaises(UserError):
            mo.with_user(self.user_b).action_confirm()

    def test_product_produce_2(self):
        """Check that using a component lot of company b in the produce wizard of a production
        of company a is not allowed """

        product = self.env['product.product'].create({
            'name': 'p1',
        })
        component = self.env['product.product'].create({
            'name': 'p2',
            'tracking': 'lot',
        })
        lot_b = self.env['stock.lot'].create({
            'product_id': component.id,
            'company_id': self.company_b.id,
        })
        self.env['mrp.bom'].create({
            'product_id': product.id,
            'product_tmpl_id': product.product_tmpl_id.id,
            'company_id': self.company_a.id,
            'bom_line_ids': [(0, 0, {'product_id': component.id})]
        })
        mo_form = Form(self.env['mrp.production'].with_user(self.user_a))
        mo_form.product_id = product
        mo = mo_form.save()
        mo.with_user(self.user_b).action_confirm()
        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()
        details_operation_form = Form(mo.move_raw_ids[0], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = lot_b
            ml.qty_done = 1
        details_operation_form.save()
        with self.assertRaises(UserError):
            mo.button_mark_done()


    def test_partner_1(self):
        """ On a product without company, as a user of Company B, check it is not possible to use a
        location limited to Company A as `property_stock_production` """

        shared_product = self.env['product.product'].create({
            'name': 'Shared Product',
            'company_id': False,
        })
        with self.assertRaises(UserError):
            shared_product.with_user(self.user_b).property_stock_production = self.stock_location_a
