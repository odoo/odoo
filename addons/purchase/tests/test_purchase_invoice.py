# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import Form, tagged
from odoo import Command, fields


class TestPurchaseToInvoiceCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super(TestPurchaseToInvoiceCommon, cls).setUpClass()
        cls.other_currency = cls.setup_other_currency('EUR')
        cls.env.user.group_ids += cls.env.ref('uom.group_uom')
        uom_unit = cls.env.ref('uom.product_uom_unit')
        uom_hour = cls.env.ref('uom.product_uom_hour')
        cls.product_order = cls.env['product.product'].create({
            'name': "Zed+ Antivirus",
            'standard_price': 235.0,
            'list_price': 280.0,
            'type': 'consu',
            'uom_id': uom_unit.id,
            'purchase_method': 'purchase',
            'default_code': 'PROD_ORDER',
            'taxes_id': False,
        })
        cls.product_order_other_price = cls.env['product.product'].create({
            'name': "Zed+ Antivirus",
            'standard_price': 240.0,
            'list_price': 290.0,
            'type': 'consu',
            'uom_id': uom_unit.id,
            'purchase_method': 'purchase',
            'default_code': 'PROD_ORDER',
            'taxes_id': False,
        })
        cls.product_order_var_name = cls.env['product.product'].create({
            'name': "Zed+ Antivirus Var Name",
            'standard_price': 235.0,
            'list_price': 280.0,
            'type': 'consu',
            'uom_id': uom_unit.id,
            'purchase_method': 'purchase',
            'default_code': 'PROD_ORDER_VAR_NAME',
            'taxes_id': False,
        })
        cls.service_deliver = cls.env['product.product'].create({
            'name': "Cost-plus Contract",
            'standard_price': 200.0,
            'list_price': 180.0,
            'type': 'service',
            'uom_id': uom_unit.id,
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
                line_form.product_uom_id = product.uom_id
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
            'product_uom_id': self.product_deliver.uom_id.id,
            'price_unit': self.product_deliver.list_price,
            'order_id': purchase_order.id,
            'tax_ids': False,
        })
        pol_serv_deliver = PurchaseOrderLine.create({
            'name': self.service_deliver.name,
            'product_id': self.service_deliver.id,
            'product_qty': 10.0,
            'product_uom_id': self.service_deliver.uom_id.id,
            'price_unit': self.service_deliver.list_price,
            'order_id': purchase_order.id,
            'tax_ids': False,
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
            'product_uom_id': self.product_order.uom_id.id,
            'price_unit': self.product_order.list_price,
            'order_id': purchase_order.id,
            'tax_ids': False,
        })
        pol_serv_order = PurchaseOrderLine.create({
            'name': self.service_order.name,
            'product_id': self.service_order.id,
            'product_qty': 10.0,
            'product_uom_id': self.service_order.uom_id.id,
            'price_unit': self.service_order.list_price,
            'order_id': purchase_order.id,
            'tax_ids': False,
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
            'product_uom_id': self.product_deliver.uom_id.id,
            'price_unit': self.product_deliver.list_price,
            'order_id': purchase_order.id,
            'tax_ids': False,
        })
        pol_serv_deliver = PurchaseOrderLine.create({
            'name': self.service_deliver.name,
            'product_id': self.service_deliver.id,
            'product_qty': 10.0,
            'product_uom_id': self.service_deliver.uom_id.id,
            'price_unit': self.service_deliver.list_price,
            'order_id': purchase_order.id,
            'tax_ids': False,
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
            'product_uom_id': self.product_order.uom_id.id,
            'price_unit': self.product_order.list_price,
            'order_id': purchase_order.id,
            'tax_ids': False,
        })
        pol_serv_order = PurchaseOrderLine.create({
            'name': self.service_order.name,
            'product_id': self.service_order.id,
            'product_qty': 10.0,
            'product_uom_id': self.service_order.uom_id.id,
            'price_unit': self.service_order.list_price,
            'order_id': purchase_order.id,
            'tax_ids': False,
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
                'product_uom_id': self.product_order.uom_id.id,
                'price_unit': 1000,
                'order_id': po.id,
                'tax_ids': False,
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
                'amount_currency': 500,
                'balance': 500,
            }, {
                'display_type': 'product',
                'amount_currency': 1000,
                'balance': 1000,
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
        self.env.ref('product.decimal_price').max_digits = 3
        self.env.company.currency_id.rounding = 0.01

        po = self.env['purchase.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'name': self.product_a.name,
                'product_id': self.product_a.id,
                'product_qty': 12,
                'product_uom_id': self.product_a.uom_id.id,
                'price_unit': 0.001,
                'tax_ids': False,
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
        self.env.user.group_ids += self.env.ref('analytic.group_analytic_accounting')
        analytic_plan = self.env['account.analytic.plan'].create({'name': 'Plan Test'})
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
        self.env.user.group_ids += self.env.ref('account.group_account_readonly')
        self.env.user.group_ids += self.env.ref('analytic.group_analytic_accounting')

        analytic_plan = self.env['account.analytic.plan'].create({'name': 'Plan Test'})
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
        partner = self.env['res.partner'].create({'name': 'Test Partner'})
        po_form.partner_id = partner
        with po_form.order_line.new() as po_line_form:
            po_line_form.name = super_product.name
            po_line_form.product_id = super_product
        purchase_order = po_form.save()
        purchase_order_line = purchase_order.order_line

        self.assertEqual(purchase_order_line.analytic_distribution, {str(analytic_account_super.id): 100}, "The analytic account should be set to 'Super Account'")
        purchase_order_line.write({'product_id': great_product.id})
        self.assertEqual(purchase_order_line.analytic_distribution, {str(analytic_account_great.id): 100}, "The analytic account should be set to 'Great Account'")

        po_no_analytic_distribution = self.env['purchase.order'].create({
            'partner_id': partner.id,
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
        the default analytic account is correctly set during the conversion from po to invoice.
        An additional analytic account set manually in another plan is also passed to the invoice.
        """
        self.env.user.group_ids += self.env.ref('analytic.group_analytic_accounting')
        analytic_plan_default = self.env['account.analytic.plan'].create({
            'name': 'default',
            'applicability_ids': [Command.create({
                'business_domain': 'bill',
                'applicability': 'optional',
            })]
        })
        analytic_account_default = self.env['account.analytic.account'].create({'name': 'default', 'plan_id': analytic_plan_default.id})
        # Create an additional analytic account in another plan
        analytic_plan_2 = self.env['account.analytic.plan'].create({'name': 'Plan Test'})
        analytic_account_2 = self.env['account.analytic.account'].create({'name': 'manual', 'plan_id': analytic_plan_2.id})
        analytic_distribution_manual = {str(analytic_account_2.id): 100}

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
        # Add another analytic account to the line. It should be passed to the invoice
        po.order_line.analytic_distribution = analytic_distribution_manual
        po.button_confirm()
        po.order_line.qty_received = 1
        po.action_create_invoice()
        self.assertRecordValues(po.invoice_ids.invoice_line_ids, [{
            'analytic_distribution': analytic_distribution_model.analytic_distribution | analytic_distribution_manual
        }])

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
                    'product_uom_id': self.product_order.uom_id.id,
                    'price_unit': self.product_order.list_price,
                    'tax_ids': False,
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
                    'product_uom_id': self.product_order.uom_id.id,
                    'price_unit': self.product_order.list_price,
                    'tax_ids': False,
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
                    'product_uom_id': self.product_deliver.uom_id.id,
                    'price_unit': self.product_deliver.list_price,
                    'tax_ids': False,
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

    def test_supplier_discounted_price(self):
        """ Check the lower price (discount included) is used.
        """
        uom_dozen = self.env.ref('uom.product_uom_dozen')
        supplierinfo_common_vals = {
            'partner_id': self.partner_a.id,
            'product_id': self.product_order.id,
            'product_tmpl_id': self.product_order.product_tmpl_id.id,
        }
        supplierinfo = self.env['product.supplierinfo'].create([
            {
                **supplierinfo_common_vals,
                'price': 100.0,
                'discount': 0,  # Real price by unit: 100.00
            }, {
                **supplierinfo_common_vals,
                'price': 120.0,
                'discount': 20,  # Real price by unit: 96.00
            }, {
                **supplierinfo_common_vals,
                'min_qty': 10,
                'price': 140.0,
                'discount': 50,  # Real price by unit: 70.00
            },
        ])
        self.assertRecordValues(supplierinfo, [
            {'price_discounted': 100},
            {'price_discounted': 96},
            {'price_discounted': 70},
        ])

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_a
        with po_form.order_line.new() as po_line_form:
            po_line_form.product_id = self.product_order
            po_line_form.product_qty = 1
        po = po_form.save()
        po_line = po.order_line[0]
        self.assertEqual(120.0, po_line.price_unit)
        self.assertEqual(20, po_line.discount)
        self.assertEqual(96.0, po_line.price_unit_discounted)
        self.assertEqual(96.0, po_line.price_subtotal)

        # Increase the PO line quantity: it should take another price if min. qty. is reached.
        po_form = Form(po)
        with po_form.order_line.edit(0) as po_line_form:
            po_line_form.product_uom_id = uom_dozen
            po_line_form.product_qty = 3
        po = po_form.save()
        po_line = po.order_line[0]

        self.assertEqual(1680.0, po_line.price_unit, "140.0 * 12 = 1680.0")
        self.assertEqual(50, po_line.discount)
        self.assertEqual(840.0, po_line.price_unit_discounted, "1680.0 * 0.5 = 840.0")
        self.assertEqual(2520.0, po_line.price_subtotal, "840.0 * 3 = 2520.0")

    def test_invoice_line_name_has_product_name(self):
        """ Testing that when invoicing a sales order, the invoice line name ALWAYS contains the product name. """
        # Create a purchase order with different descriptions
        po = self.env['purchase.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner_a.id,
        })
        PurchaseOrderLine = self.env['purchase.order.line'].with_context(tracking_disable=True)
        pol_prod_no_redundancy = PurchaseOrderLine.create({
            'name': "just a description",
            'product_id': self.product_deliver.id,
            'product_qty': 1,
            'product_uom_id': self.product_deliver.uom_id.id,
            'price_unit': self.product_deliver.list_price,
            'order_id': po.id,
            'tax_ids': False,
        })
        pol_prod_same = PurchaseOrderLine.create({
            'name': self.product_deliver.display_name,
            'product_id': self.product_deliver.id,
            'product_qty': 1,
            'product_uom_id': self.product_deliver.uom_id.id,
            'price_unit': self.product_deliver.list_price,
            'order_id': po.id,
            'tax_ids': False,
        })
        pol_prod_product_in_name = PurchaseOrderLine.create({
            'name': f"{self.product_deliver.display_name} with more description",
            'product_id': self.product_deliver.id,
            'product_qty': 1,
            'product_uom_id': self.product_deliver.uom_id.id,
            'price_unit': self.product_deliver.list_price,
            'order_id': po.id,
            'tax_ids': False,
        })
        pol_prod_name_in_product = PurchaseOrderLine.create({
            'name': "Switch",
            'product_id': self.product_deliver.id,
            'product_qty': 1,
            'product_uom_id': self.product_deliver.uom_id.id,
            'price_unit': self.product_deliver.list_price,
            'order_id': po.id,
            'tax_ids': False,
        })

        # Invoice the purchase order
        po.button_confirm()
        po.order_line.qty_received = 4
        po.action_create_invoice()
        inv = po.invoice_ids

        # Check the invoice line names
        self.assertEqual(inv.invoice_line_ids[0].name, f"{pol_prod_no_redundancy.product_id.display_name} {pol_prod_no_redundancy.name}", "When the description doesn't contain the product name, it should be added to the invoice line name")
        self.assertEqual(inv.invoice_line_ids[1].name, f"{pol_prod_same.name}", "When the description is the product name, the invoice line name should only be the description")
        self.assertEqual(inv.invoice_line_ids[2].name, f"{pol_prod_product_in_name.name}", "When description contains the product name, the invoice line name should only be the description")
        self.assertEqual(inv.invoice_line_ids[3].name, f"{pol_prod_name_in_product.product_id.display_name} {pol_prod_name_in_product.name}", "When the product name contains the description, the invoice line name should be the product name and the description")


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

    def test_subset_total_match_from_ocr(self):
        po = self.init_purchase(confirm=True, products=[self.product_order, self.service_order])
        invoice = self.init_invoice('in_invoice', partner=self.partner_a, products=[self.product_order])

        invoice._find_and_set_purchase_orders(
            ['my_match_reference'], invoice.partner_id.id, invoice.amount_total, from_ocr=True)
        additional_unmatch_po_line = po.order_line.filtered(lambda l: l.product_id == self.service_order)

        self.assertTrue(invoice.id in po.invoice_ids.ids)
        self.assertTrue(additional_unmatch_po_line.id in invoice.line_ids.purchase_line_id.ids)
        self.assertTrue(invoice.line_ids.filtered(lambda l: l.purchase_line_id == additional_unmatch_po_line).quantity == 0)

    def test_subset_match_from_edi_full(self):
        """An invoice totally matches a purchase order line by line
        """
        po = self.init_purchase(confirm=True, products=[self.product_order, self.service_order])
        invoice = self.init_invoice('in_invoice', partner=self.partner_a, products=[self.product_order, self.service_order])

        invoice._find_and_set_purchase_orders(
            ['my_match_reference'], invoice.partner_id.id, invoice.amount_total, from_ocr=False)

        self.assertTrue(invoice.id in po.invoice_ids.ids)
        invoice_lines = invoice.line_ids.filtered(lambda l: l.price_unit)
        self.assertEqual(len(invoice_lines), 2)
        for line in invoice_lines:
            self.assertTrue(line.purchase_line_id in po.order_line)
        self.assertEqual(invoice.amount_total, po.amount_total)

    def test_subset_match_from_edi_partial_po(self):
        """A line of the invoice totally matches a 1-line purchase order
        """
        po = self.init_purchase(confirm=True, products=[self.product_order])
        invoice = self.init_invoice('in_invoice', partner=self.partner_a, products=[self.product_order, self.service_order])

        invoice._find_and_set_purchase_orders(
            ['my_match_reference'], invoice.partner_id.id, invoice.amount_total, from_ocr=False)

        self.assertTrue(invoice.id in po.invoice_ids.ids)
        invoice_lines = invoice.line_ids.filtered(lambda l: l.price_unit)
        self.assertEqual(len(invoice_lines), 2)
        for line in po.order_line:
            self.assertTrue(line in invoice_lines.purchase_line_id)

    def test_subset_match_from_edi_partial_inv(self):
        """An invoice totally matches some purchase order line
        """
        po = self.init_purchase(confirm=True, products=[self.product_order, self.service_order])
        invoice = self.init_invoice('in_invoice', partner=self.partner_a, products=[self.product_order])

        invoice._find_and_set_purchase_orders(
            ['my_match_reference'], invoice.partner_id.id, invoice.amount_total, from_ocr=False)

        self.assertTrue(invoice.id in po.invoice_ids.ids)
        invoice_lines = invoice.line_ids.filtered(lambda l: l.price_unit)
        self.assertEqual(len(invoice_lines), 1)
        for line in invoice_lines:
            self.assertTrue(line.purchase_line_id in po.order_line)

    def test_subset_match_from_edi_same_unit_price(self):
        """An invoice matches some purchase order line by unit price
        """
        po = self.init_purchase(confirm=True, products=[self.product_order_var_name, self.product_order])
        invoice = self.init_invoice('in_invoice', partner=self.partner_a, products=[self.product_order])

        invoice._find_and_set_purchase_orders(
            ['my_match_reference'], invoice.partner_id.id, invoice.amount_total, from_ocr=False)

        self.assertTrue(invoice.id in po.invoice_ids.ids)
        invoice_lines = invoice.line_ids.filtered(lambda l: l.price_unit)
        self.assertEqual(len(invoice_lines), 1)
        for line in invoice_lines:
            self.assertTrue(line.purchase_line_id in po.order_line)

    def test_subset_match_from_edi_and_diff_unit_price(self):
        """An invoice matches some purchase order line but not another one because of a unit price difference
        """
        po = self.init_purchase(confirm=True, products=[self.product_order_var_name, self.product_order])
        invoice = self.init_invoice('in_invoice', partner=self.partner_a, products=[self.product_order, self.product_order_other_price])

        invoice._find_and_set_purchase_orders(
            ['my_match_reference'], invoice.partner_id.id, invoice.amount_total, from_ocr=False)

        self.assertTrue(invoice.id in po.invoice_ids.ids)
        invoice_lines = invoice.line_ids.filtered(lambda l: l.price_unit)
        self.assertEqual(len(invoice_lines), 2)
        for line in invoice_lines:
            if (line.product_id == self.product_order):
                self.assertTrue(line.purchase_line_id in po.order_line)
            else:
                self.assertFalse(line.purchase_line_id in po.order_line)

    def test_subset_not_match_non_invoice_lines(self):
        """Test that a purchase line with a line of 0 as unit price won't match
        with a non-invoice-lines (not an invoice_line_ids)
        """
        uom_unit = self.env.ref('uom.product_uom_unit')
        product_order_zero_price = self.env['product.product'].create({
            'name': "A zero price product",
            'standard_price': 0.0,
            'list_price': 0.0,
            'type': 'consu',
            'uom_id': uom_unit.id,
            'purchase_method': 'purchase',
            'default_code': 'PROD_ORDER',
            'taxes_id': False,
        })
        po = self.init_purchase(confirm=True, products=[product_order_zero_price])
        invoice = self.init_invoice('in_invoice', partner=self.partner_a, products=[self.product_order])
        invoice._find_and_set_purchase_orders(
            ['my_match_reference'], invoice.partner_id.id, invoice.amount_total, from_ocr=False)

        self.assertFalse(invoice.id in po.invoice_ids.ids)

    def test_po_match_from_ocr(self):
        po = self.init_purchase(confirm=True, products=[self.product_order, self.service_order])
        invoice = self.init_invoice('in_invoice', products=[self.product_a])

        invoice._find_and_set_purchase_orders(
            ['my_match_reference'], invoice.partner_id.id, invoice.amount_total, from_ocr=True)

        self.assertTrue(invoice.id in po.invoice_ids.ids)

    def test_no_match_same_reference(self):
        po = self.init_purchase(confirm=True, products=[self.product_order, self.service_order])
        invoice = self.init_invoice('in_invoice', products=[self.product_a])

        invoice._find_and_set_purchase_orders(
            ['my_match_reference'], invoice.partner_id.id, invoice.amount_total, from_ocr=False)

        self.assertTrue(invoice.id not in po.invoice_ids.ids)

    def test_no_match(self):
        po = self.init_purchase(confirm=True, products=[self.product_order, self.service_order])
        invoice = self.init_invoice('in_invoice', products=[self.product_a])

        invoice._find_and_set_purchase_orders(
            ['other_reference'], invoice.partner_id.id, invoice.amount_total, from_ocr=False)

        self.assertTrue(invoice.id not in po.invoice_ids.ids)

    def test_manual_matching(self):
        po = self.init_purchase(confirm=True, products=[self.product_order])
        bill = self.init_invoice('in_invoice', partner=self.partner_a, products=[self.product_order])

        self.env['account.move.line'].flush_model()  # necessary to get the bill lines
        match_lines = self.env['purchase.bill.line.match'].search([('partner_id', '=', self.partner_a.id)])

        expected_ids = po.order_line.ids + [-lid for lid in bill.invoice_line_ids.ids]
        self.assertListEqual(match_lines.ids, expected_ids)

        match_lines.action_match_lines()
        self.assertEqual(bill.invoice_line_ids.purchase_line_id, po.order_line)
        self.assertEqual(po.order_line.qty_invoiced, bill.invoice_line_ids.quantity)

    def test_manual_matching_restrict_no_pol(self):
        """ raises when there's no POL found """
        with self.assertRaisesRegex(UserError, "must select at least one Purchase Order line"):
            match_lines = self.env['purchase.bill.line.match'].search([('partner_id', '=', self.partner_a.id)])
            match_lines.action_match_lines()

    def test_manual_matching_restrict_multi_bill(self):
        """ raises when multiple bill selected """
        with self.assertRaisesRegex(UserError, "can't select lines from multiple Vendor Bill"):
            self.init_purchase(confirm=True, products=[self.product_order])
            self.init_invoice('in_invoice', partner=self.partner_a, products=[self.product_order])
            self.init_invoice('in_invoice', partner=self.partner_a, products=[self.product_order])
            match_lines = self.env['purchase.bill.line.match'].search([('partner_id', '=', self.partner_a.id)])
            match_lines.action_match_lines()

    def test_manual_matching_create_bill(self):
        """ Selecting POL without AML will create bill with the selected POL as the lines """
        prev_moves = self.env['account.move'].search([])
        self.init_purchase(confirm=True, products=[self.product_order, self.product_order_var_name])
        self.env['purchase.order.line'].flush_model()
        self.env['purchase.order'].flush_model()

        match_lines = self.env['purchase.bill.line.match'].search([('partner_id', '=', self.partner_a.id)])
        match_lines.action_match_lines()

        new_move = self.env['account.move'].search([]) - prev_moves
        self.assertEqual(new_move.partner_id, self.partner_a)
        self.assertRecordValues(new_move.invoice_line_ids, [
            {'product_id': self.product_order.id},
            {'product_id': self.product_order_var_name.id},
        ])

    def test_manual_matching_multi_po(self):
        """ All POL are matched/added into the bill, and all unmatched AML are discarded """
        po_1 = self.init_purchase(confirm=True, products=[self.product_order, self.product_order_var_name])
        po_2 = self.init_purchase(confirm=True, products=[self.service_deliver])
        po_3 = self.init_purchase(confirm=True, products=[self.service_order])
        bill = self.init_invoice(move_type='in_invoice', partner=self.partner_a,
                                 products=[self.product_order, self.product_order_other_price])

        self.env['account.move.line'].flush_model()
        match_lines = self.env['purchase.bill.line.match'].search([('partner_id', '=', self.partner_a.id)])
        match_lines.action_match_lines()

        self.env.flush_all()
        self.assertEqual(bill.invoice_line_ids.purchase_line_id, (po_1 + po_2 + po_3).order_line)
        self.assertRecordValues(bill.invoice_line_ids, [
            {'product_id': self.product_order.id},
            {'product_id': self.service_order.id},
            {'product_id': self.product_order_var_name.id},
            {'product_id': self.service_deliver.id},
        ])

    def test_add_bill_to_po(self):
        bill = self.init_invoice('in_invoice', partner=self.partner_a, products=[self.product_order_var_name, self.service_deliver], post=True)
        self.env['account.move.line'].flush_model()

        match_lines = self.env['purchase.bill.line.match'].search([('partner_id', '=', self.partner_a.id)])

        # Use wizard to create a new PO
        action = match_lines.action_add_to_po()
        wizard = self.env['bill.to.po.wizard'].with_context({**action['context'], 'active_ids': match_lines.ids}).create({})
        self.assertEqual(wizard.partner_id, self.partner_a)
        self.assertFalse(wizard.purchase_order_id)

        action = wizard.action_add_to_po()
        po = self.env['purchase.order'].browse(action['res_id'])
        self.assertEqual(po.partner_id, self.partner_a)
        self.assertTrue(po.order_line.tax_ids)
        self.assertEqual(po.order_line.tax_ids, bill.invoice_line_ids.tax_ids)
        self.assertEqual(po.order_line.product_id, bill.invoice_line_ids.product_id)
        self.assertEqual(po.order_line.product_id, self.product_order_var_name + self.service_deliver)

        bill_2 = self.init_invoice('in_invoice', partner=self.partner_a, products=[self.product_order_other_price], post=False)
        bill_2.invoice_line_ids.write({
            'discount': 2.0,
            'product_uom_id': self.env.ref('uom.product_uom_dozen').id,
        })
        bill_2.action_post()
        self.env['account.move.line'].flush_model()

        match_lines = self.env['purchase.bill.line.match'].search([('partner_id', '=', self.partner_a.id)])

        # Use wizard to add lines to existing PO
        match_lines.action_add_to_po()
        wizard = self.env['bill.to.po.wizard'].with_context({
            'default_purchase_order_id': po.id,
            'active_ids': match_lines.ids
        }).create({})

        action = wizard.action_add_to_po()
        self.assertEqual(action['res_id'], po.id)
        self.assertEqual(len(po.order_line), 3)
        self.assertEqual(po.order_line[-1:].product_id, self.product_order_other_price)
        self.assertListEqual(po.order_line.mapped('price_total'), (bill + bill_2).invoice_line_ids.mapped('price_total'))

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

        ctx['default_currency_id'] = self.other_currency.id
        move_form_currency_in_context = Form(self.env['account.move'].with_context(ctx))
        move_form_currency_in_context.currency_id = self.env.ref('base.EUR')
        with move_form_currency_in_context.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_order
            line_form.quantity = 1
        move_form_currency_in_context.save()

        move_form_currency_in_context.partner_id = vendor_a
        bill = move_form_currency_in_context.save()

        self.assertEqual(bill.currency_id, self.other_currency, "The currency of the Bill should be the one of the context")
        self.assertEqual(bill.invoice_line_ids.currency_id, self.other_currency, "The currency of the Bill lines should be the same as the currency of the Bill")

    def test_invoice_user_id_on_bill(self):
        """
        Test that the invoice_user_id field is False when creating a vendor bill from a PO
        or when using Auto-Complete feature of a vendor bill.
        """
        group_purchase_user = self.env.ref('purchase.group_purchase_user')
        group_employee = self.env.ref('base.group_user')
        group_partner_manager = self.env.ref('base.group_partner_manager')
        purchase_user = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Purchase user',
            'login': 'purchaseUser',
            'email': 'pu@odoo.com',
            'group_ids': [Command.set([group_purchase_user.id, group_employee.id, group_partner_manager.id])],
        })
        po1 = self.env['purchase.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner_a.id,
            'user_id': purchase_user.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_order.id,
                    'product_qty': 1.0,
                    'price_unit': self.product_order.list_price,
                    'tax_ids': False,
                }),
            ]
        })
        po2 = po1.copy()
        po1.button_confirm()
        po2.button_confirm()
        # creating bill from PO
        po1.order_line.qty_received = 1
        po1.action_create_invoice()
        invoice1 = po1.invoice_ids
        self.assertFalse(invoice1.invoice_user_id)
        # creating bill with Auto_complete feature
        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        move_form.purchase_vendor_bill_id = self.env['purchase.bill.union'].browse(-po2.id)
        invoice2 = move_form.save()
        self.assertFalse(invoice2.invoice_user_id)

    def test_create_invoice_from_multiple_purchase_orders(self):
        """ Test that invoices can be created from purchase orders with different
        vendors without raising errors and with correct vendor mapping per invoice.
        """
        purchase_orders = self.env['purchase.order'].with_context(tracking_disable=True).create([
            {
                'partner_id': self.partner_a.id,
                'order_line': [
                    Command.create({
                        'product_id': self.product_order.id,
                        'product_qty': 1.0,
                        'price_unit': self.product_order.list_price,
                        'tax_ids': False,
                    }),
                ],
            },
            {
                'partner_id': self.partner_b.id,
                'order_line': [
                    Command.create({
                        'product_id': self.product_deliver.id,
                        'product_qty': 2.0,
                        'price_unit': self.product_deliver.list_price,
                        'tax_ids': False,
                    }),
                ],
            },
        ])
        purchase_orders.button_confirm()
        purchase_orders.action_create_invoice()

        self.assertEqual(len(purchase_orders.invoice_ids), 2, "Each PO should generate one invoice")
        self.assertEqual(
            set(purchase_orders.invoice_ids.partner_id.ids),
            set(purchase_orders.partner_id.ids),
            "Each invoice should be linked to the correct vendor"
        )
