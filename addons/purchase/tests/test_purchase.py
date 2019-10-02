# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo.tests.common import SavepointCase
from odoo.tests import Form


class TestPurchase(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestPurchase, cls).setUpClass()
        cls.product_consu = cls.env['product.product'].create({
            'name': 'Product A',
            'type': 'consu',
        })
        cls.product_consu2 = cls.env['product.product'].create({
            'name': 'Product B',
            'type': 'consu',
        })
        cls.vendor = cls.env['res.partner'].create({'name': 'vendor1'})
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')

    def test_date_planned_1(self):
        """Set a date planned on a PO, see that it is set on the PO lines. Try to edit the date
        planned of the PO line, see that it is not possible. Unset the date planned on the PO and
        edit the date planned on the PO lines. Validate the PO and see that it isn't possible to
        set the date planned on the PO nor on the PO lines.
        """
        po = Form(self.env['purchase.order'])
        po.partner_id = self.vendor
        with po.order_line.new() as po_line:
            po_line.product_id = self.product_consu
            po_line.product_qty = 1
            po_line.price_unit = 100
        with po.order_line.new() as po_line:
            po_line.product_id = self.product_consu2
            po_line.product_qty = 10
            po_line.price_unit = 200
        po = po.save()

        # Check there is no date planned on the PO and the same date planned on both PO lines.
        self.assertEqual(po.date_planned, False)
        self.assertNotEqual(po.order_line[0].date_planned, False)
        self.assertAlmostEqual(po.order_line[0].date_planned, po.order_line[1].date_planned, delta=timedelta(seconds=10))

        orig_date_planned = po.order_line[0].date_planned

        # Set a date planned on a PO, see that it is set on the PO lines.
        new_date_planned = orig_date_planned + timedelta(hours=1)
        po.date_planned = new_date_planned
        self.assertAlmostEqual(po.order_line[0].date_planned, new_date_planned, delta=timedelta(seconds=10))
        self.assertAlmostEqual(po.order_line[1].date_planned, new_date_planned, delta=timedelta(seconds=10))

        # Try to edit the date planned of the PO line, see that it is not possible
        po = Form(po)
        with self.assertRaises(AssertionError):
            po.order_line.edit(0).date_planned = orig_date_planned
        with self.assertRaises(AssertionError):
            po.order_line.edit(1).date_planned = orig_date_planned
        po = po.save()

        self.assertAlmostEqual(po.order_line[0].date_planned, new_date_planned, delta=timedelta(seconds=10))
        self.assertAlmostEqual(po.order_line[1].date_planned, new_date_planned, delta=timedelta(seconds=10))

        # Unset the date planned on the PO and edit the date planned on the PO line.
        po = Form(po)
        po.date_planned = False
        with po.order_line.edit(0) as po_line:
            po_line.date_planned = orig_date_planned
        with po.order_line.edit(1) as po_line:
            po_line.date_planned = orig_date_planned
        po = po.save()

        self.assertAlmostEqual(po.order_line[0].date_planned, orig_date_planned, delta=timedelta(seconds=10))
        self.assertAlmostEqual(po.order_line[1].date_planned, orig_date_planned, delta=timedelta(seconds=10))

        # Validate the PO and see that it isn't possible to set the date planned on the PO
        # nor on the PO lines.
        po.button_confirm()
        po.button_done()

        po = Form(po)
        with self.assertRaises(AssertionError):
            po.date_planned = new_date_planned
        with self.assertRaises(AssertionError):
            with po.order_line.edit(0) as po_line:
                po_line.date_planned = orig_date_planned
        with self.assertRaises(AssertionError):
            with po.order_line.edit(1) as po_line:
                po_line.date_planned = orig_date_planned
        po.save()

    def test_purchase_order_sequence(self):
        PurchaseOrder = self.env['purchase.order'].with_context(tracking_disable=True)
        company = self.env.user.company_id
        self.env['ir.sequence'].search([
            ('code', '=', 'purchase.order'),
        ]).write({
            'use_date_range': True, 'prefix': 'PO/%(range_year)s/',
        })
        vals = {
            'partner_id': self.vendor.id,
            'company_id': company.id,
            'currency_id': company.currency_id.id,
            'date_order': '2019-01-01',
        }
        purchase_order = PurchaseOrder.create(vals.copy())
        self.assertTrue(purchase_order.name.startswith('PO/2019/'))
        vals['date_order'] = '2020-01-01'
        purchase_order = PurchaseOrder.create(vals.copy())
        self.assertTrue(purchase_order.name.startswith('PO/2020/'))
        # In EU/BXL tz, this is actually already 01/01/2020
        vals['date_order'] = '2019-12-31 23:30:00'
        purchase_order = PurchaseOrder.with_context(tz='Europe/Brussels').create(vals.copy())
        self.assertTrue(purchase_order.name.startswith('PO/2020/'))
