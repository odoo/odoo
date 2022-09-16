# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo.addons.account.tests.account_test_savepoint import AccountTestInvoicingCommon
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

    def test_on_change_quantity_description(self):
        """
        When a user changes the quantity of a product in a purchase order it
        should not change the description if the descritpion was changed by
        the user before
        """
        company = self.env.user.company_id
        vals = {
            'partner_id': self.vendor.id,
            'company_id': company.id,
        }
        po = Form(self.env['purchase.order'].create(vals))
        self.product_consu.write({'seller_ids': [
            (0, 0, {'name': self.vendor.id, 'product_code': 'ASUCODE'}),
        ]})
        with po.order_line.new() as pol:
            pol.product_id = self.product_consu
            pol.product_qty = 1
        pol.name = "New custom description"
        pol.product_qty += 1
        self.assertEqual(pol.name, "New custom description")

class TestPurchaseAccount(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

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

    def test_on_change_quantity_price_unit(self):
        """ When a user changes the quantity of a product in a purchase order it
        should only update the unit price if PO line has no invoice line. """

        supplierinfo_vals = {
            'name': self.vendor.id,
            'price': 10.0,
            'min_qty': 1,
            "product_id": self.product_consu.id,
            "product_tmpl_id": self.product_consu.product_tmpl_id.id,
        }

        supplierinfo = self.env["product.supplierinfo"].create(supplierinfo_vals)
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.vendor
        with po_form.order_line.new() as po_line_form:
            po_line_form.product_id = self.product_consu
            po_line_form.product_qty = 1
        po = po_form.save()
        po_line = po.order_line[0]

        self.assertEqual(10.0, po_line.price_unit, "Unit price should be set to 10.0 for 1 quantity")

        # Ensure price unit is updated when changing quantity on a un-confirmed PO
        supplierinfo.write({'min_qty': 2, 'price': 20.0})
        po_line.write({'product_qty': 2})
        po_line._onchange_quantity()
        self.assertEqual(20.0, po_line.price_unit, "Unit price should be set to 20.0 for 2 quantity")

        po.button_confirm()

        # Ensure price unit is updated when changing quantity on a confirmed PO
        supplierinfo.write({'min_qty': 3, 'price': 30.0})
        po_line.write({'product_qty': 3})
        po_line._onchange_quantity()
        self.assertEqual(30.0, po_line.price_unit, "Unit price should be set to 30.0 for 3 quantity")

        action = po.action_view_invoice()
        invoice_form = Form(self.env['account.move'].with_context(action['context']))
        invoice_form.save()

        # Ensure price unit is NOT updated when changing quantity on PO confirmed and line linked to an invoice line
        supplierinfo.write({'min_qty': 4, 'price': 40.0})
        po_line.write({'product_qty': 4})
        po_line._onchange_quantity()
        self.assertEqual(30.0, po_line.price_unit, "Unit price should be set to 30.0 for 3 quantity")

        with po_form.order_line.new() as po_line_form:
            po_line_form.product_id = self.product_consu
            po_line_form.product_qty = 1
        po = po_form.save()
        po_line = po.order_line[1]

        self.assertEqual(0.0, po_line.price_unit, "Unit price should be reset to 0 since the supplier supplies minimum of 4 quantities")

        # Ensure price unit is updated when changing quantity on PO confirmed and line NOT linked to an invoice line
        po_line.write({'product_qty': 4})
        po_line._onchange_quantity()
        self.assertEqual(40.0, po_line.price_unit, "Unit price should be set to 40.0 for 4 quantity")
