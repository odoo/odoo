# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.tests import Form
from odoo.addons.mrp.tests.common import TestMrpCommon


class TestMrpProductionChaining(TestMrpCommon):
    #########
    # UTILS #
    #########
    def _create_bom(self, product_to_build, products_to_use):
        return self.env['mrp.bom'].create({
            'product_id': product_to_build.id,
            'product_tmpl_id': product_to_build.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': product_to_use.id, 'product_qty': 1})
                for product_to_use in products_to_use
            ]}
        )[0]

    def _create_product(self, manufacture=False):
        return self.env['product.product'].create({
            'name': 'Super product',
            'type': 'product',
            'route_ids': [
                (4, self.env.ref('mrp.route_warehouse0_manufacture').id, 0),
                (4, self.env.ref('stock.route_warehouse0_mto').id, 0)
            ] if manufacture else []
        })

    def _create_mo(self, bom, date_deadline=False, date_planned_start=False, planned_duration=False):
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = bom.product_id
        mo_form.bom_id = bom
        mo_form.date_deadline = date_deadline
        mo_form.date_planned_start = date_planned_start or datetime.now() + timedelta(days=100)
        mo_form.product_qty = 1
        if planned_duration:
            mo_form.date_planned_finished = mo_form.date_planned_start + planned_duration
        mo = mo_form.save()
        return mo

    #########
    # TESTS #
    #########

    def test_mrp_production_chaining_1(self):
        """Simple case, only one child MO."""
        now = datetime.now()

        component = self._create_product()
        child_product = self._create_product(manufacture=True)
        parent_product = self._create_product(manufacture=True)

        child_bom = self._create_bom(child_product, component)
        parent_bom = self._create_bom(parent_product, child_product)

        parent_mrp_production = self._create_mo(
            parent_bom, date_deadline=now + timedelta(days=8),
            date_planned_start=now + timedelta(days=7),
            planned_duration=timedelta(days=3))
        parent_mrp_production.company_id.manufacturing_lead = 2

        self.assertEqual(len(parent_mrp_production.children_mrp_production_ids), 0)
        parent_mrp_production.action_confirm()
        self.assertEqual(len(parent_mrp_production.children_mrp_production_ids), 1)

        child_mrp_production = parent_mrp_production.children_mrp_production_ids

        self.assertAlmostEqual(child_mrp_production.date_deadline, now + timedelta(days=3), delta=timedelta(hours=1))
        self.assertAlmostEqual(child_mrp_production.date_planned_start, now + timedelta(days=2), delta=timedelta(hours=1))

    def test_mrp_production_chaining_2(self):
        """Try to confirm 2 ``mrp.production`` at the same time."""
        now = datetime.now()

        component = self._create_product()
        child_product = self._create_product(manufacture=True)
        parent_product_1 = self._create_product(manufacture=True)
        parent_product_2 = self._create_product(manufacture=True)

        child_bom = self._create_bom(child_product, component)
        parent_bom_1 = self._create_bom(parent_product_1, child_product)
        parent_bom_2 = self._create_bom(parent_product_2, child_product)

        parent_mrp_production_1 = self._create_mo(
            parent_bom_1, date_deadline=now + timedelta(days=8),
            date_planned_start=now + timedelta(days=7),
            planned_duration=timedelta(days=3))
        parent_mrp_production_1.company_id.manufacturing_lead = 2

        parent_mrp_production_2 = self._create_mo(
            parent_bom_2, date_deadline=now + timedelta(days=15),
            date_planned_start=now + timedelta(days=10),
            planned_duration=timedelta(days=2))
        parent_mrp_production_2.company_id.manufacturing_lead = 2

        self.assertEqual(len(parent_mrp_production_1.children_mrp_production_ids), 0)
        self.assertEqual(len(parent_mrp_production_2.children_mrp_production_ids), 0)

        (parent_mrp_production_1 | parent_mrp_production_2).action_confirm()

        self.assertEqual(len(parent_mrp_production_1.children_mrp_production_ids), 1)
        self.assertEqual(len(parent_mrp_production_2.children_mrp_production_ids), 1)

        child_mrp_production_1 = parent_mrp_production_1.children_mrp_production_ids
        child_mrp_production_2 = parent_mrp_production_2.children_mrp_production_ids

        self.assertAlmostEqual(child_mrp_production_1.date_deadline, now + timedelta(days=3), delta=timedelta(hours=1))
        self.assertAlmostEqual(child_mrp_production_1.date_planned_start, now + timedelta(days=2), delta=timedelta(hours=1))
        self.assertAlmostEqual(child_mrp_production_2.date_deadline, now + timedelta(days=11), delta=timedelta(hours=1))
        self.assertAlmostEqual(child_mrp_production_2.date_planned_start, now + timedelta(days=6), delta=timedelta(hours=1))

    def test_mrp_production_chaining_3(self):
        """If we change the dates of a parent, we should update the children."""
        now = datetime.now()

        component = self._create_product()
        child_product = self._create_product(manufacture=True)
        parent_product = self._create_product(manufacture=True)

        child_bom = self._create_bom(child_product, component)
        parent_bom = self._create_bom(parent_product, child_product)

        parent_mrp_production = self._create_mo(parent_bom)
        parent_mrp_production.company_id.manufacturing_lead = 2
        parent_mrp_production.action_confirm()

        child_mrp_production = parent_mrp_production.children_mrp_production_ids
        child_mrp_production.state = 'draft'

        self.assertEqual(child_mrp_production.reschedule_date_deadline, False)
        self.assertEqual(child_mrp_production.reschedule_dates_planned, False)

        mrp_order_form = Form(parent_mrp_production)
        mrp_order_form.date_planned_start = now + timedelta(days=12)
        mrp_order_form.save()

        self.assertEqual(child_mrp_production.reschedule_date_deadline, True)
        self.assertEqual(child_mrp_production.reschedule_dates_planned, True)

        child_mrp_production.action_update_dates_based_on_parent()

        self.assertEqual(child_mrp_production.reschedule_date_deadline, False)
        self.assertEqual(child_mrp_production.reschedule_dates_planned, False)

        mrp_order_form = Form(parent_mrp_production)
        mrp_order_form.date_deadline = now + timedelta(days=15)
        mrp_order_form.save()

        self.assertEqual(child_mrp_production.reschedule_date_deadline, True)
        self.assertEqual(child_mrp_production.reschedule_dates_planned, False)

    def test_mrp_production_chaining_4(self):
        """If we cancel a parent MO, we must cancel the children if they are in state draft."""
        component = self._create_product()
        child_product = self._create_product(manufacture=True)
        parent_product = self._create_product(manufacture=True)

        child_bom = self._create_bom(child_product, component)
        parent_bom = self._create_bom(parent_product, child_product)

        parent_mrp_production = self._create_mo(parent_bom)
        parent_mrp_production.company_id.manufacturing_lead = 2
        parent_mrp_production.action_confirm()

        child_mrp_production = parent_mrp_production.children_mrp_production_ids
        child_mrp_production.state = 'draft'

        parent_mrp_production.action_cancel()
        self.assertEqual(child_mrp_production.state, 'cancel')

    def test_mrp_production_chaining_5(self):
        """If we cancel a parent MO, we must cancel the children if they are in state draft."""
        component = self._create_product()
        child_product = self._create_product(manufacture=True)
        parent_product = self._create_product(manufacture=True)

        child_bom = self._create_bom(child_product, component)
        parent_bom = self._create_bom(parent_product, child_product)

        parent_mrp_production = self._create_mo(parent_bom)
        parent_mrp_production.company_id.manufacturing_lead = 2
        parent_mrp_production.action_confirm()

        child_mrp_production = parent_mrp_production.children_mrp_production_ids
        child_mrp_production.state = 'done'

        parent_mrp_production.action_cancel()
        self.assertEqual(child_mrp_production.state, 'done')
