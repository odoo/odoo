# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tests.common import Form
from odoo import Command, fields


class TestPurchaseToInvoiceCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super(TestPurchaseToInvoiceCommon, cls).setUpClass()
        uom_unit = cls.env.ref('uom.product_uom_unit')
        uom_hour = cls.env.ref('uom.product_uom_hour')
        cls.product_order = cls.env['product.product'].create({
            'name': "Zed+ Antivirus",
            'standard_price': 235.0,
            'list_price': 280.0,
            'type': 'consu',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
            'purchase_method': 'purchase',
            'default_code': 'PROD_ORDER',
            'taxes_id': False,
        })
        cls.service_deliver = cls.env['product.product'].create({
            'name': "Cost-plus Contract",
            'standard_price': 200.0,
            'list_price': 180.0,
            'type': 'service',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
            'purchase_method': 'receive',
            'default_code': 'SERV_DEL',
            'taxes_id': False,
        })
        cls.service_order = cls.env['product.product'].create({
            'name': "Prepaid Consulting",
            'standard_price': 40.0,
            'list_price': 90.0,
            'type': 'service',
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
            'purchase_method': 'purchase',
            'default_code': 'PRE-PAID',
            'taxes_id': False,
        })
        cls.product_deliver = cls.env['product.product'].create({
            'name': "Switch, 24 ports",
            'standard_price': 55.0,
            'list_price': 70.0,
            'type': 'consu',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
            'purchase_method': 'receive',
            'default_code': 'PROD_DEL',
            'taxes_id': False,
        })

    @classmethod
    def init_purchase(cls, partner=None, confirm=False, products=None, taxes=None, company=False):
        date_planned = fields.Datetime.now() - timedelta(days=1)
        po_form = Form(cls.env['purchase.order'] \
                    .with_company(company or cls.env.company) \
                    .with_context(tracking_disable=True))
        po_form.partner_id = partner or cls.partner_a
        po_form.partner_ref = 'my_match_reference'

        for product in (products or []):
            with po_form.order_line.new() as line_form:
                line_form.product_id = product
                line_form.price_unit = product.list_price
                line_form.product_qty = 1
                line_form.product_uom = product.uom_id
                line_form.date_planned = date_planned
                if taxes:
                    line_form.tax_ids.clear()
                    for tax in taxes:
                        line_form.tax_ids.add(tax)

        rslt = po_form.save()

        if confirm:
            rslt.button_confirm()

        return rslt


@tagged('post_install', '-at_install')
class TestPurchaseToInvoice(TestPurchaseToInvoiceCommon):

    def test_vendor_bill_delivered(self):
        """Test if a order of product invoiced by delivered quantity can be
        correctly invoiced."""
        purchase_order = self.env['purchase.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner_a.id,
        })
        PurchaseOrderLine = self.env['purchase.order.line'].with_context(tracking_disable=True)
        pol_prod_deliver = PurchaseOrderLine.create({
            'name': self.product_deliver.name,
            'product_id': self.product_deliver.id,
            'product_qty': 10.0,
            'product_uom': self.product_deliver.uom_id.id,
            'price_unit': self.product_deliver.list_price,
            'order_id': purchase_order.id,
            'taxes_id': False,
        })
        pol_serv_deliver = PurchaseOrderLine.create({
            'name': self.service_deliver.name,
            'product_id': self.service_deliver.id,
            'product_qty': 10.0,
            'product_uom': self.service_deliver.uom_id.id,
            'price_unit': self.service_deliver.list_price,
            'order_id': purchase_order.id,
            'taxes_id': False,
        })
        purchase_order.button_confirm()

        self.assertEqual(purchase_order.invoice_status, "no")
        for line in purchase_order.order_line:
            self.assertEqual(line.qty_to_invoice, 0.0)
            self.assertEqual(line.qty_invoiced, 0.0)

        purchase_order.order_line.qty_received = 5
        self.assertEqual(purchase_order.invoice_status, "to invoice")
        for line in purchase_order.order_line:
            self.assertEqual(line.qty_to_invoice, 5)
            self.assertEqual(line.qty_invoiced, 0.0)

        purchase_order.action_create_invoice()
        self.assertEqual(purchase_order.invoice_status, "invoiced")
        for line in purchase_order.order_line:
            self.assertEqual(line.qty_to_invoice, 0.0)
            self.assertEqual(line.qty_invoiced, 5)

    def test_vendor_bill_ordered(self):
        """Test if a order of product invoiced by ordered quantity can be
        correctly invoiced."""
        purchase_order = self.env['purchase.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner_a.id,
        })
        PurchaseOrderLine = self.env['purchase.order.line'].with_context(tracking_disable=True)
        pol_prod_order = PurchaseOrderLine.create({
            'name': self.product_order.name,
            'product_id': self.product_order.id,
            'product_qty': 10.0,
            'product_uom': self.product_order.uom_id.id,
            'price_unit': self.product_order.list_price,
            'order_id': purchase_order.id,
            'taxes_id': False,
        })
        pol_serv_order = PurchaseOrderLine.create({
            'name': self.service_order.name,
            'product_id': self.service_order.id,
            'product_qty': 10.0,
            'product_uom': self.service_order.uom_id.id,
            'price_unit': self.service_order.list_price,
            'order_id': purchase_order.id,
            'taxes_id': False,
        })
        purchase_order.button_confirm()

        self.assertEqual(purchase_order.invoice_status, "to invoice")
        for line in purchase_order.order_line:
            self.assertEqual(line.qty_to_invoice, 10)
            self.assertEqual(line.qty_invoiced, 0.0)

        purchase_order.order_line.qty_received = 5
        self.assertEqual(purchase_order.invoice_status, "to invoice")
        for line in purchase_order.order_line:
            self.assertEqual(line.qty_to_invoice, 10)
            self.assertEqual(line.qty_invoiced, 0.0)

        purchase_order.action_create_invoice()
        self.assertEqual(purchase_order.invoice_status, "invoiced")
        for line in purchase_order.order_line:
            self.assertEqual(line.qty_to_invoice, 0.0)
            self.assertEqual(line.qty_invoiced, 10)

    def test_vendor_bill_delivered_return(self):
        """Test when return product, a order of product invoiced by delivered
        quantity can be correctly invoiced."""
        purchase_order = self.env['purchase.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner_a.id,
        })
        PurchaseOrderLine = self.env['purchase.order.line'].with_context(tracking_disable=True)
        pol_prod_deliver = PurchaseOrderLine.create({
            'name': self.product_deliver.name,
            'product_id': self.product_deliver.id,
            'product_qty': 10.0,
            'product_uom': self.product_deliver.uom_id.id,
            'price_unit': self.product_deliver.list_price,
            'order_id': purchase_order.id,
            'taxes_id': False,
        })
        pol_serv_deliver = PurchaseOrderLine.create({
            'name': self.service_deliver.name,
            'product_id': self.service_deliver.id,
            'product_qty': 10.0,
            'product_uom': self.service_deliver.uom_id.id,
            'price_unit': self.service_deliver.list_price,
            'order_id': purchase_order.id,
            'taxes_id': False,
        })
        purchase_order.button_confirm()

        purchase_order.order_line.qty_received = 10
        purchase_order.action_create_invoice()
        self.assertEqual(purchase_order.invoice_status, "invoiced")
        for line in purchase_order.order_line:
            self.assertEqual(line.qty_to_invoice, 0.0)
            self.assertEqual(line.qty_invoiced, 10)

        purchase_order.order_line.qty_received = 5
        self.assertEqual(purchase_order.invoice_status, "to invoice")
        for line in purchase_order.order_line:
            self.assertEqual(line.qty_to_invoice, -5)
            self.assertEqual(line.qty_invoiced, 10)
        purchase_order.action_create_invoice()
        self.assertEqual(purchase_order.invoice_status, "invoiced")
        for line in purchase_order.order_line:
            self.assertEqual(line.qty_to_invoice, 0.0)
            self.assertEqual(line.qty_invoiced, 5)

    def test_vendor_bill_ordered_return(self):
        """Test when return product, a order of product invoiced by ordered
        quantity can be correctly invoiced."""
        purchase_order = self.env['purchase.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner_a.id,
        })
        PurchaseOrderLine = self.env['purchase.order.line'].with_context(tracking_disable=True)
        pol_prod_order = PurchaseOrderLine.create({
            'name': self.product_order.name,
            'product_id': self.product_order.id,
            'product_qty': 10.0,
            'product_uom': self.product_order.uom_id.id,
            'price_unit': self.product_order.list_price,
            'order_id': purchase_order.id,
            'taxes_id': False,
        })
        pol_serv_order = PurchaseOrderLine.create({
            'name': self.service_order.name,
            'product_id': self.service_order.id,
            'product_qty': 10.0,
            'product_uom': self.service_order.uom_id.id,
            'price_unit': self.service_order.list_price,
            'order_id': purchase_order.id,
            'taxes_id': False,
        })
        purchase_order.button_confirm()

        purchase_order.order_line.qty_received = 10
        purchase_order.action_create_invoice()
        self.assertEqual(purchase_order.invoice_status, "invoiced")
        for line in purchase_order.order_line:
            self.assertEqual(line.qty_to_invoice, 0.0)
            self.assertEqual(line.qty_invoiced, 10)

        purchase_order.order_line.qty_received = 5
        self.assertEqual(purchase_order.invoice_status, "invoiced")
        for line in purchase_order.order_line:
            self.assertEqual(line.qty_to_invoice, 0.0)
            self.assertEqual(line.qty_invoiced, 10)

    def test_vendor_severals_bills_and_multicurrency(self):
        """
        This test ensures that, when adding several PO to a bill, if they are expressed with different
        currency, the amount of each AML is converted to the bill's currency
        """
        PurchaseOrderLine = self.env['purchase.order.line']
        PurchaseBillUnion = self.env['purchase.bill.union']
        ResCurrencyRate = self.env['res.currency.rate']
        usd = self.env.ref('base.USD')
        eur = self.env.ref('base.EUR')
        purchase_orders = []

        ResCurrencyRate.create({'currency_id': usd.id, 'rate': 1})
        ResCurrencyRate.create({'currency_id': eur.id, 'rate': 2})

        for currency in [usd, eur]:
            po = self.env['purchase.order'].with_context(tracking_disable=True).create({
                'partner_id': self.partner_a.id,
                'currency_id': currency.id,
            })
            pol_prod_order = PurchaseOrderLine.create({
                'name': self.product_order.name,
                'product_id': self.product_order.id,
                'product_qty': 1,
                'product_uom': self.product_order.uom_id.id,
                'price_unit': 1000,
                'order_id': po.id,
                'taxes_id': False,
            })
            po.button_confirm()
            pol_prod_order.write({'qty_received': 1})
            purchase_orders.append(po)

        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        move_form.purchase_vendor_bill_id = PurchaseBillUnion.browse(-purchase_orders[0].id)
        move_form.purchase_vendor_bill_id = PurchaseBillUnion.browse(-purchase_orders[1].id)
        move = move_form.save()

        self.assertInvoiceValues(move, [
            {
                'display_type': 'product',
                'amount_currency': 1000,
                'balance': 1000,
            }, {
                'display_type': 'product',
                'amount_currency': 500,
                'balance': 500,
            }, {
                'display_type': 'payment_term',
                'amount_currency': -1500,
                'balance': -1500,
            },
        ], {
            'amount_total': 1500,
            'currency_id': usd.id,
        })

    def test_product_price_decimal_accuracy(self):
        self.env.ref('product.decimal_price').digits = 3
        self.env.company.currency_id.rounding = 0.01

        po = self.env['purchase.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'name': self.product_a.name,
                'product_id': self.product_a.id,
                'product_qty': 12,
                'product_uom': self.product_a.uom_id.id,
                'price_unit': 0.001,
                'taxes_id': False,
            })]
        })
        po.button_confirm()
        po.order_line.qty_received = 12

        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        move_form.purchase_vendor_bill_id = self.env['purchase.bill.union'].browse(-po.id)
        move = move_form.save()

        self.assertEqual(move.amount_total, 0.01)

    def test_vendor_bill_analytic_account_model_change(self):
        """ Tests whether, when an analytic account rule is set, and user changes manually the analytic account on
        the po, it is the same that is mentioned in the bill.
        """
        # Required for `analytic.group_analytic_accounting` to be visible in the view
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_accounting')
        analytic_plan = self.env['account.analytic.plan'].create({'name': 'Plan Test', 'company_id': False})
        analytic_account_default = self.env['account.analytic.account'].create({'name': 'default', 'plan_id': analytic_plan.id})
        analytic_account_manual = self.env['account.analytic.account'].create({'name': 'manual', 'plan_id': analytic_plan.id})

        self.env['account.analytic.distribution.model'].create({
            'analytic_distribution': {analytic_account_default.id: 100},
            'product_id': self.product_order.id,
        })
        analytic_distribution_manual = {str(analytic_account_manual.id): 100}

        po_form = Form(self.env['purchase.order'].with_context(tracking_disable=True))
        po_form.partner_id = self.partner_a
        with po_form.order_line.new() as po_line_form:
            po_line_form.name = self.product_order.name
            po_line_form.product_id = self.product_order
            po_line_form.product_qty = 1.0
            po_line_form.price_unit = 10
            po_line_form.analytic_distribution = analytic_distribution_manual

        purchase_order = po_form.save()
        purchase_order.button_confirm()
        purchase_order.action_create_invoice()

        aml = self.env['account.move.line'].search([('purchase_line_id', '=', purchase_order.order_line.id)])
        self.assertRecordValues(aml, [{'analytic_distribution': analytic_distribution_manual}])

    def test_purchase_order_analytic_account_product_change(self):
        self.env.user.groups_id += self.env.ref('account.group_account_readonly')
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_accounting')

        analytic_plan = self.env['account.analytic.plan'].create({'name': 'Plan Test', 'company_id': False})
        analytic_account_super = self.env['account.analytic.account'].create({'name': 'Super Account', 'plan_id': analytic_plan.id})
        analytic_account_great = self.env['account.analytic.account'].create({'name': 'Great Account', 'plan_id': analytic_plan.id})

        super_product = self.env['product.product'].create({'name': 'Super Product'})
        great_product = self.env['product.product'].create({'name': 'Great Product'})
        self.env['account.analytic.distribution.model'].create([
            {
                'analytic_distribution': {analytic_account_super.id: 100},
                'product_id': super_product.id,
            },
            {
                'analytic_distribution': {analytic_account_great.id: 100},
                'product_id': great_product.id,
            },
        ])
        po_form = Form(self.env['purchase.order'].with_context(tracking_disable=True))
        po_form.partner_id = self.env.ref('base.res_partner_1')
        with po_form.order_line.new() as po_line_form:
            po_line_form.name = super_product.name
            po_line_form.product_id = super_product
        purchase_order = po_form.save()
        purchase_order_line = purchase_order.order_line

        self.assertEqual(purchase_order_line.analytic_distribution, {str(analytic_account_super.id): 100}, "The analytic account should be set to 'Super Account'")
        purchase_order_line.write({'product_id': great_product.id})
        self.assertEqual(purchase_order_line.analytic_distribution, {str(analytic_account_great.id): 100}, "The analytic account should be set to 'Great Account'")

        po_no_analytic_distribution = self.env['purchase.order'].create({
            'partner_id': self.env.ref('base.res_partner_1').id,
        })
        pol_no_analytic_distribution = self.env['purchase.order.line'].create({
            'name': super_product.name,
            'product_id': super_product.id,
            'order_id': po_no_analytic_distribution.id,
            'analytic_distribution': False,
        })
        po_no_analytic_distribution.button_confirm()
        self.assertFalse(pol_no_analytic_distribution.analytic_distribution, "The compute should not overwrite what the user has set.")

    def test_purchase_order_to_invoice_analytic_rule_with_account_prefix(self):
        """
        Test whether, when an analytic plan is set within the scope (applicability) of purchase
        and with an account prefix set in the distribution model,
        the default analytic account is correctly set during the conversion from po to invoice
        """
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_accounting')
        analytic_plan_default = self.env['account.analytic.plan'].create({
            'name': 'default',
            'applicability_ids': [Command.create({
                'business_domain': 'bill',
                'applicability': 'optional',
            })]
        })
        analytic_account_default = self.env['account.analytic.account'].create({'name': 'default', 'plan_id': analytic_plan_default.id})

        analytic_distribution_model = self.env['account.analytic.distribution.model'].create({
            'account_prefix': '600',
            'analytic_distribution': {analytic_account_default.id: 100},
            'product_id': self.product_a.id,
        })

        po = self.env['purchase.order'].create({'partner_id': self.partner_a.id})
        self.env['purchase.order.line'].create({
            'order_id': po.id,
            'name': 'test',
            'product_id': self.product_a.id
        })
        self.assertFalse(po.order_line.analytic_distribution, "There should be no analytic set.")
        po.button_confirm()
        po.order_line.qty_received = 1
        po.action_create_invoice()
        self.assertRecordValues(po.invoice_ids.invoice_line_ids,
                                [{'analytic_distribution': analytic_distribution_model.analytic_distribution}])

    def test_sequence_invoice_lines_from_multiple_purchases(self):
        """Test if the invoice lines are sequenced by purchase order when creating an invoice
           from multiple selected po's"""
        purchase_orders = self.env['purchase.order']

        for _ in range(3):
            pol_vals = [
                (0, 0, {
                    'name': self.product_order.name,
                    'product_id': self.product_order.id,
                    'product_qty': 10.0,
                    'product_uom': self.product_order.uom_id.id,
                    'price_unit': self.product_order.list_price,
                    'taxes_id': False,
                    'sequence': sequence_number,
                }) for sequence_number in range(10, 13)]
            purchase_order = self.env['purchase.order'].with_context(tracking_disable=True).create({
                'partner_id': self.partner_a.id,
                'order_line': pol_vals,
            })
            purchase_order.button_confirm()
            purchase_orders |= purchase_order

        action = purchase_orders.action_create_invoice()
        invoice = self.env['account.move'].browse(action['res_id'])

        expected_purchase = [
            purchase_orders[0], purchase_orders[0], purchase_orders[0],
            purchase_orders[1], purchase_orders[1], purchase_orders[1],
            purchase_orders[2], purchase_orders[2], purchase_orders[2],
        ]
        for line in invoice.invoice_line_ids.sorted('sequence'):
            self.assertEqual(line.purchase_order_id, expected_purchase.pop(0))

    def test_sequence_autocomplete_invoice(self):
        """Test if the invoice lines are sequenced by purchase order when using the autocomplete
           feature on a bill to add lines from po's"""
        purchase_orders = self.env['purchase.order']

        for _ in range(3):
            pol_vals = [
                (0, 0, {
                    'name': self.product_order.name,
                    'product_id': self.product_order.id,
                    'product_qty': 10.0,
                    'product_uom': self.product_order.uom_id.id,
                    'price_unit': self.product_order.list_price,
                    'taxes_id': False,
                    'sequence': sequence_number,
                }) for sequence_number in range(10, 13)]
            purchase_order = self.env['purchase.order'].with_context(tracking_disable=True).create({
                'partner_id': self.partner_a.id,
                'order_line': pol_vals,
            })
            purchase_order.button_confirm()
            purchase_orders |= purchase_order

        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        PurchaseBillUnion = self.env['purchase.bill.union']
        move_form.purchase_vendor_bill_id = PurchaseBillUnion.browse(-purchase_orders[0].id)
        move_form.purchase_vendor_bill_id = PurchaseBillUnion.browse(-purchase_orders[1].id)
        move_form.purchase_vendor_bill_id = PurchaseBillUnion.browse(-purchase_orders[2].id)
        invoice = move_form.save()

        expected_purchase = [
            purchase_orders[0], purchase_orders[0], purchase_orders[0],
            purchase_orders[1], purchase_orders[1], purchase_orders[1],
            purchase_orders[2], purchase_orders[2], purchase_orders[2],
        ]
        for line in invoice.invoice_line_ids.sorted('sequence'):
            self.assertEqual(line.purchase_order_id, expected_purchase.pop(0))

    def test_partial_billing_interaction_with_invoicing_switch_threshold(self):
        """ Let's say you create a partial bill 'B' for a given PO. Now if you change the
            'Invoicing Switch Threshold' such that the bill date of 'B' is before the new threshold,
            the PO should still take bill 'B' into account.
        """
        if not self.env['ir.module.module'].search([('name', '=', 'account_accountant'), ('state', '=', 'installed')]):
            self.skipTest("This test requires the installation of the account_account module")

        purchase_order = self.env['purchase.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'name': self.product_deliver.name,
                    'product_id': self.product_deliver.id,
                    'product_qty': 20.0,
                    'product_uom': self.product_deliver.uom_id.id,
                    'price_unit': self.product_deliver.list_price,
                    'taxes_id': False,
                }),
            ],
        })
        line = purchase_order.order_line[0]

        purchase_order.button_confirm()
        line.qty_received = 10
        purchase_order.action_create_invoice()

        invoice = purchase_order.invoice_ids
        invoice.invoice_date = invoice.date
        invoice.action_post()

        self.assertEqual(line.qty_invoiced, 10)

        self.env['res.config.settings'].create({
            'invoicing_switch_threshold': fields.Date.add(invoice.invoice_date, days=30),
        }).execute()

        invoice.invalidate_model(fnames=['payment_state'])

        self.assertEqual(line.qty_invoiced, 10)
        line.qty_received = 15
        self.assertEqual(line.qty_invoiced, 10)

    def test_on_change_quantity_price_unit(self):
        """ When a user changes the quantity of a product in a purchase order it
        should only update the unit price if PO line has no invoice line. """

        supplierinfo_vals = {
            'partner_id': self.partner_a.id,
            'price': 10.0,
            'min_qty': 1,
            "product_id": self.product_order.id,
            "product_tmpl_id": self.product_order.product_tmpl_id.id,
        }

        supplierinfo = self.env["product.supplierinfo"].create(supplierinfo_vals)
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_a
        with po_form.order_line.new() as po_line_form:
            po_line_form.product_id = self.product_order
            po_line_form.product_qty = 1
        po = po_form.save()
        po_line = po.order_line[0]

        self.assertEqual(10.0, po_line.price_unit, "Unit price should be set to 10.0 for 1 quantity")

        # Ensure price unit is updated when changing quantity on a un-confirmed PO
        supplierinfo.write({'min_qty': 2, 'price': 20.0})
        po_line.write({'product_qty': 2})
        self.assertEqual(20.0, po_line.price_unit, "Unit price should be set to 20.0 for 2 quantity")

        po.button_confirm()

        # Ensure price unit is updated when changing quantity on a confirmed PO
        supplierinfo.write({'min_qty': 3, 'price': 30.0})
        po_line.write({'product_qty': 3})
        self.assertEqual(30.0, po_line.price_unit, "Unit price should be set to 30.0 for 3 quantity")

        po.action_create_invoice()

        # Ensure price unit is NOT updated when changing quantity on PO confirmed and line linked to an invoice line
        supplierinfo.write({'min_qty': 4, 'price': 40.0})
        po_line.write({'product_qty': 4})
        self.assertEqual(30.0, po_line.price_unit, "Unit price should be set to 30.0 for 3 quantity")

        with po_form.order_line.new() as po_line_form:
            po_line_form.product_id = self.product_order
            po_line_form.product_qty = 1
        po = po_form.save()
        po_line = po.order_line[1]

        self.assertEqual(235.0, po_line.price_unit, "Unit price should be reset to 235.0 since the supplier supplies minimum of 4 quantities")

        # Ensure price unit is updated when changing quantity on PO confirmed and line NOT linked to an invoice line
        po_line.write({'product_qty': 4})
        self.assertEqual(40.0, po_line.price_unit, "Unit price should be set to 40.0 for 4 quantity")


@tagged('post_install', '-at_install')
class TestInvoicePurchaseMatch(TestPurchaseToInvoiceCommon):

    def test_total_match_via_partner(self):
        po = self.init_purchase(confirm=True, partner=self.partner_a, products=[self.product_order])
        invoice = self.init_invoice('in_invoice', partner=self.partner_a, products=[self.product_order])

        invoice._find_and_set_purchase_orders(
            [], invoice.partner_id.id, invoice.amount_total)

        self.assertTrue(invoice.id in po.invoice_ids.ids)
        self.assertEqual(invoice.amount_total, po.amount_total)

    def test_total_match_via_po_reference(self):
        po = self.init_purchase(confirm=True, products=[self.product_order])
        invoice = self.init_invoice('in_invoice', partner=self.partner_a, products=[self.product_order])

        invoice._find_and_set_purchase_orders(
            ['my_match_reference'], invoice.partner_id.id, invoice.amount_total)

        self.assertTrue(invoice.id in po.invoice_ids.ids)
        self.assertEqual(invoice.amount_total, po.amount_total)

    def test_subset_total_match_prefer_purchase(self):
        po = self.init_purchase(confirm=True, products=[self.product_order, self.service_order])
        invoice = self.init_invoice('in_invoice', partner=self.partner_a, products=[self.product_order])

        invoice._find_and_set_purchase_orders(
            ['my_match_reference'], invoice.partner_id.id, invoice.amount_total, prefer_purchase_line=True)
        additional_unmatch_po_line = po.order_line.filtered(lambda l: l.product_id == self.service_order)

        self.assertTrue(invoice.id in po.invoice_ids.ids)
        self.assertTrue(additional_unmatch_po_line.id in invoice.line_ids.purchase_line_id.ids)
        self.assertTrue(invoice.line_ids.filtered(lambda l: l.purchase_line_id == additional_unmatch_po_line).quantity == 0)

    def test_subset_total_match_reject_purchase(self):
        po = self.init_purchase(confirm=True, products=[self.product_order, self.service_order])
        invoice = self.init_invoice('in_invoice', partner=self.partner_a, products=[self.product_order])

        invoice._find_and_set_purchase_orders(
            ['my_match_reference'], invoice.partner_id.id, invoice.amount_total, prefer_purchase_line=False)
        additional_unmatch_po_line = po.order_line.filtered(lambda l: l.product_id == self.service_order)

        self.assertTrue(invoice.id in po.invoice_ids.ids)
        self.assertTrue(additional_unmatch_po_line.id not in invoice.line_ids.purchase_line_id.ids)

    def test_po_match_prefer_purchase(self):
        po = self.init_purchase(confirm=True, products=[self.product_order, self.service_order])
        invoice = self.init_invoice('in_invoice', products=[self.product_a])

        invoice._find_and_set_purchase_orders(
            ['my_match_reference'], invoice.partner_id.id, invoice.amount_total, prefer_purchase_line=True)

        self.assertTrue(invoice.id in po.invoice_ids.ids)

    def test_po_match_reject_purchase(self):
        po = self.init_purchase(confirm=True, products=[self.product_order, self.service_order])
        invoice = self.init_invoice('in_invoice', products=[self.product_a])

        invoice._find_and_set_purchase_orders(
            ['my_match_reference'], invoice.partner_id.id, invoice.amount_total, prefer_purchase_line=False)

        self.assertTrue(invoice.id not in po.invoice_ids.ids)
        self.assertNotEqual(invoice.amount_total, po.amount_total)

    def test_no_match(self):
        po = self.init_purchase(confirm=True, products=[self.product_order, self.service_order])
        invoice = self.init_invoice('in_invoice', products=[self.product_a])

        invoice._find_and_set_purchase_orders(
            ['other_reference'], invoice.partner_id.id, invoice.amount_total, prefer_purchase_line=False)

        self.assertTrue(invoice.id not in po.invoice_ids.ids)

    def test_onchange_partner_currency(self):
        """
        Test that the currency of the Bill is correctly set when the partner is changed
        as well as the currency of the Bill lines
        """

        vendor_eur = self.env['res.partner'].create({
            'name': 'Vendor EUR',
            'property_purchase_currency_id': self.env.ref('base.EUR').id,
        })
        vendor_us = self.env['res.partner'].create({
            'name': 'Vendor USD',
            'property_purchase_currency_id': self.env.ref('base.USD').id,
        })
        vendor_no_currency = self.env['res.partner'].create({
            'name': 'Vendor No Currency',
        })

        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        move_form.partner_id = vendor_eur
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_order
            line_form.quantity = 1
        bill = move_form.save()

        self.assertEqual(bill.currency_id, self.env.ref('base.EUR'), "The currency of the Bill should be the same as the currency of the partner")
        self.assertEqual(bill.invoice_line_ids.currency_id, self.env.ref('base.EUR'), "The currency of the Bill lines should be the same as the currency of the partner")

        move_form.partner_id = vendor_us
        bill = move_form.save()

        self.assertEqual(bill.currency_id, self.env.ref('base.USD'), "The currency of the Bill should be the same as the currency of the partner")
        self.assertEqual(bill.invoice_line_ids.currency_id, self.env.ref('base.USD'), "The currency of the Bill lines should be the same as the currency of the partner")

        move_form.partner_id = vendor_no_currency
        bill = move_form.save()

        self.assertEqual(bill.currency_id, self.env.company.currency_id, "The currency of the Bill should be the same as the currency of the company")
        self.assertEqual(bill.invoice_line_ids.currency_id, self.env.company.currency_id, "The currency of the Bill lines should be the same as the currency of the company")

    def test_onchange_partner_no_currency(self):
        """
        Test that the currency of the Bill is correctly set when the partner is changed
        as well as the currency of the Bill lines even if the partner has no property_purchase_currency_id set
        or when and the `default_currency_id` is defined in the context
        """

        vendor_a = self.env['res.partner'].create({
            'name': 'Vendor A with No Currency',
        })
        vendor_b = self.env['res.partner'].create({
            'name': 'Vendor B with No Currency',
        })

        ctx = {'default_move_type': 'in_invoice'}
        move_form = Form(self.env['account.move'].with_context(ctx))
        move_form.partner_id = vendor_a
        move_form.currency_id = self.env.ref('base.EUR')
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_order
            line_form.quantity = 1
        bill = move_form.save()

        self.assertEqual(bill.currency_id, self.env.ref('base.EUR'), "The currency of the Bill should be the one set on the Bill")
        self.assertEqual(bill.invoice_line_ids.currency_id, self.env.ref('base.EUR'), "The currency of the Bill lines should be the same as the currency of the Bill")

        move_form.partner_id = vendor_b
        bill = move_form.save()

        self.assertEqual(bill.currency_id, self.env.ref('base.EUR'), "The currency of the Bill should be the one set on the Bill")
        self.assertEqual(bill.invoice_line_ids.currency_id, self.env.ref('base.EUR'), "The currency of the Bill lines should be the same as the currency of the Bill")

        ctx['default_currency_id'] = self.currency_data['currency'].id
        move_form_currency_in_context = Form(self.env['account.move'].with_context(ctx))
        move_form_currency_in_context.currency_id = self.env.ref('base.EUR')
        with move_form_currency_in_context.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_order
            line_form.quantity = 1
        move_form_currency_in_context.save()

        move_form_currency_in_context.partner_id = vendor_a
        bill = move_form_currency_in_context.save()

        self.assertEqual(bill.currency_id, self.currency_data['currency'], "The currency of the Bill should be the one of the context")
        self.assertEqual(bill.invoice_line_ids.currency_id, self.currency_data['currency'], "The currency of the Bill lines should be the same as the currency of the Bill")

    def test_payment_reference_autocomplete_invoice(self):
        """
        Test that the payment_reference field is not replaced when selected a purchase order
        We test the flow for 8 use cases:
        - Purchase order with partner ref:
            - Bill with ref:
                - Bill with payment_reference -> should not be replaced
                - Bill without payment_reference -> should be the po.partner_ref
            - Bill without ref:
                - Bill with payment_reference -> should not be replaced
                - Bill without payment_reference -> should be the po.partner_ref
        - Purchase order without partner ref:
            - Bill with ref
                - Bill with payment_reference -> should not be replaced
                - Bill without payment_reference -> should be the bill ref
            - Bill with ref
                - Bill with payment_reference -> should not be replaced
                - Bill without payment_reference -> should be empty
        """
        purchase_order_w_ref, purchase_order_wo_ref = self.env['purchase.order'].with_context(tracking_disable=True).create([
            {
                'partner_id': self.partner_a.id,
                'partner_ref': partner_ref,
                'order_line': [
                    Command.create({
                        'product_id': self.product_order.id,
                        'product_qty': 1.0,
                        'price_unit': self.product_order.list_price,
                        'taxes_id': False,
                    }),
                ]
            } for partner_ref in ('PO-001', False)
        ])
        (purchase_order_w_ref + purchase_order_wo_ref).button_confirm()

        expected_values_dict = {
            purchase_order_w_ref: {
                'w_bill_ref': {'w_payment_reference': '222', 'wo_payment_reference': purchase_order_w_ref.partner_ref},
                'wo_bill_ref': {'w_payment_reference': '222', 'wo_payment_reference': purchase_order_w_ref.partner_ref},
            },
            purchase_order_wo_ref: {
                'w_bill_ref': {'w_payment_reference': '222', 'wo_payment_reference': '111'},
                'wo_bill_ref': {'w_payment_reference': '222', 'wo_payment_reference': ''},
            }
        }

        for purchase_order, purchase_expected_values in expected_values_dict.items():
            for w_bill_ref, expected_values in purchase_expected_values.items():
                for w_payment_reference, expected_value in expected_values.items():
                    with self.subTest(po_partner_ref=purchase_order.partner_ref, w_bill_ref=w_bill_ref, w_payment_reference=w_payment_reference, expected_value=expected_value):
                        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
                        move_form.ref = '111' if w_bill_ref == 'w_bill_ref' else ''
                        move_form.payment_reference = '222' if w_payment_reference == 'w_payment_reference' else ''
                        move_form.purchase_vendor_bill_id = self.env['purchase.bill.union'].browse(-purchase_order.id).exists()
                        payment_reference = move_form._values['payment_reference']
                        self.assertEqual(payment_reference, expected_value, "The payment reference should be %s" % expected_value)
