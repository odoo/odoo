# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError, AccessError

from .test_sale_common import TestSale


class TestSaleOrder(TestSale):
    def test_sale_order(self):
        """ Test the sales order flow (invoicing and quantity updates)
            - Invoice repeatedly while varrying delivered quantities and check that invoice are always what we expect
        """
        # DBO TODO: validate invoice and register payments
        inv_obj = self.env['account.invoice']
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': p.name, 'product_id': p.id, 'product_uom_qty': 2, 'product_uom': p.uom_id.id, 'price_unit': p.list_price}) for p in self.products.values()],
            'pricelist_id': self.env.ref('product.list0').id,
        })
        self.assertEqual(so.amount_total, sum([2 * p.list_price for p in self.products.values()]), 'Sale: total amount is wrong')
        so.order_line._compute_product_updatable()
        self.assertTrue(so.order_line[0].product_updatable)
        # send quotation
        so.force_quotation_send()
        self.assertTrue(so.state == 'sent', 'Sale: state after sending is wrong')
        so.order_line._compute_product_updatable()
        self.assertTrue(so.order_line[0].product_updatable)

        # confirm quotation
        so.action_confirm()
        self.assertTrue(so.state == 'sale')
        self.assertTrue(so.invoice_status == 'to invoice')

        # create invoice: only 'invoice on order' products are invoiced
        inv_id = so.action_invoice_create()
        inv = inv_obj.browse(inv_id)
        self.assertEqual(len(inv.invoice_line_ids), 2, 'Sale: invoice is missing lines')
        self.assertEqual(inv.amount_total, sum([2 * p.list_price if p.invoice_policy == 'order' else 0 for p in self.products.values()]), 'Sale: invoice total amount is wrong')
        self.assertTrue(so.invoice_status == 'no', 'Sale: SO status after invoicing should be "nothing to invoice"')
        self.assertTrue(len(so.invoice_ids) == 1, 'Sale: invoice is missing')
        so.order_line._compute_product_updatable()
        self.assertFalse(so.order_line[0].product_updatable)
        # deliver lines except 'time and material' then invoice again
        for line in so.order_line:
            line.qty_delivered = 2 if line.product_id.expense_policy=='no' else 0
        self.assertTrue(so.invoice_status == 'to invoice', 'Sale: SO status after delivery should be "to invoice"')
        inv_id = so.action_invoice_create()
        inv = inv_obj.browse(inv_id)
        self.assertEqual(len(inv.invoice_line_ids), 2, 'Sale: second invoice is missing lines')
        self.assertEqual(inv.amount_total, sum([2 * p.list_price if p.invoice_policy == 'delivery' else 0 for p in self.products.values()]), 'Sale: second invoice total amount is wrong')
        self.assertTrue(so.invoice_status == 'invoiced', 'Sale: SO status after invoicing everything should be "invoiced"')
        self.assertTrue(len(so.invoice_ids) == 2, 'Sale: invoice is missing')
        # go over the sold quantity
        for line in so.order_line:
            if line.product_id == self.products['serv_order']:
                line.qty_delivered = 10
        self.assertTrue(so.invoice_status == 'upselling', 'Sale: SO status after increasing delivered qty higher than ordered qty should be "upselling"')

        # upsell and invoice
        for line in so.order_line:
            if line.product_id == self.products['serv_order']:
                line.product_uom_qty = 10
        inv_id = so.action_invoice_create()
        inv = inv_obj.browse(inv_id)
        self.assertEqual(len(inv.invoice_line_ids), 1, 'Sale: third invoice is missing lines')
        self.assertEqual(inv.amount_total, 8 * self.products['serv_order'].list_price, 'Sale: second invoice total amount is wrong')
        self.assertTrue(so.invoice_status == 'invoiced', 'Sale: SO status after invoicing everything (including the upsel) should be "invoiced"')

    def test_unlink_cancel(self):
        """ Test deleting and cancelling sales orders depending on their state and on the user's rights """
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': p.name, 'product_id': p.id, 'product_uom_qty': 2, 'product_uom': p.uom_id.id, 'price_unit': p.list_price}) for p in self.products.values()],
            'pricelist_id': self.env.ref('product.list0').id,
        })

        # SO in state 'draft' can be deleted
        so_copy = so.copy()
        with self.assertRaises(AccessError):
            so_copy.sudo(self.user).unlink()
        self.assertTrue(so_copy.sudo(self.manager).unlink(), 'Sale: deleting a quotation should be possible')

        # SO in state 'cancel' can be deleted
        so_copy = so.copy()
        so_copy.action_confirm()
        self.assertTrue(so_copy.state == 'sale', 'Sale: SO should be in state "sale"')
        so_copy.action_cancel()
        self.assertTrue(so_copy.state == 'cancel', 'Sale: SO should be in state "cancel"')
        with self.assertRaises(AccessError):
            so_copy.sudo(self.user).unlink()
        self.assertTrue(so_copy.sudo(self.manager).unlink(), 'Sale: deleting a cancelled SO should be possible')

        # SO in state 'sale' or 'done' cannot be deleted
        so.action_confirm()
        self.assertTrue(so.state == 'sale', 'Sale: SO should be in state "sale"')
        with self.assertRaises(UserError):
            so.sudo(self.manager).unlink()

        so.action_done()
        self.assertTrue(so.state == 'done', 'Sale: SO should be in state "done"')
        with self.assertRaises(UserError):
            so.sudo(self.manager).unlink()

    def test_cost_invoicing(self):
        """ Test confirming a vendor invoice to reinvoice cost on the so """
        # force the pricelist to have the same currency as the company
        self.env.ref('product.list0').currency_id = self.env.ref('base.main_company').currency_id

        serv_cost = self.env.ref('product.service_cost_01')
        prod_gap = self.env.ref('product.product_product_1')
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': prod_gap.name, 'product_id': prod_gap.id, 'product_uom_qty': 2, 'product_uom': prod_gap.uom_id.id, 'price_unit': prod_gap.list_price})],
            'pricelist_id': self.env.ref('product.list0').id,
        })
        so.action_confirm()
        so._create_analytic_account()
        inv_partner = self.env.ref('base.res_partner_2')
        company = self.env.ref('base.main_company')
        journal = self.env['account.journal'].create({'name': 'Purchase Journal - Test', 'code': 'STPJ', 'type': 'purchase', 'company_id': company.id})
        account_payable = self.env['account.account'].create({'code': 'X1111', 'name': 'Sale - Test Payable Account', 'user_type_id': self.env.ref('account.data_account_type_payable').id, 'reconcile': True})
        account_income = self.env['account.account'].create({'code': 'X1112', 'name': 'Sale - Test Account', 'user_type_id': self.env.ref('account.data_account_type_direct_costs').id})
        invoice_vals = {
            'name': '',
            'type': 'in_invoice',
            'partner_id': inv_partner.id,
            'invoice_line_ids': [(0, 0, {'name': serv_cost.name, 'product_id': serv_cost.id, 'quantity': 2, 'uom_id': serv_cost.uom_id.id, 'price_unit': serv_cost.standard_price, 'account_analytic_id': so.analytic_account_id.id, 'account_id': account_income.id})],
            'account_id': account_payable.id,
            'journal_id': journal.id,
            'currency_id': company.currency_id.id,
        }
        inv = self.env['account.invoice'].create(invoice_vals)
        inv.action_invoice_open()
        sol = so.order_line.filtered(lambda l: l.product_id == serv_cost)
        self.assertTrue(sol, 'Sale: cost invoicing does not add lines when confirming vendor invoice')
        self.assertEquals((sol.price_unit, sol.qty_delivered, sol.product_uom_qty, sol.qty_invoiced), (160, 2, 0, 0), 'Sale: line is wrong after confirming vendor invoice')

    def test_so_create_multicompany(self):
        """In case we use new() outside of an onchange,
           it might cause the value of related fields to be incorrect.
           If so, then the company being a related might not be set,
           which would mean that taxes from all child companies
           would end up on the order lines.
        """
        user_demo = self.env.ref('base.user_demo')
        company_1 = self.env.ref('base.main_company')
        company_2 = self.env['res.company'].create({
            'name': 'company 2',
            'parent_id': company_1.id,
        })

        tax_company_1 = self.env['account.tax'].create({
            'name': 'T1',
            'amount': 90,
            'company_id': company_1.id,
        })

        tax_company_2 = self.env['account.tax'].create({
            'name': 'T2',
            'amount': 90,
            'company_id': company_2.id,
        })

        product_shared = self.env['product.template'].create({
            'name': 'shared product',
            'taxes_id': [(6, False, [tax_company_1.id, tax_company_2.id])],
        })

        so_1 = self.env['sale.order'].sudo(user_demo.id).create({
            'partner_id': self.env.ref('base.res_partner_2').id,
            'company_id': company_1.id,
        })
        so_1.write({
            'order_line': [(0, False, {'product_id': product_shared.product_variant_id.id, 'order_id': so_1.id})],
        })

        self.assertEqual(set(so_1.order_line.tax_id.ids), set([tax_company_1.id]),
            'Only taxes from the right company are put by default')

    def test_multi_currency_discount(self):
        """Verify the currency used for pricelist price & discount computation."""
        products = self.env["product.product"].search([], limit=2)
        product_1 = products[0]
        product_2 = products[1]

        # Make sure the company is in USD
        curr_usd = self.env.ref('base.USD')
        curr_eur = self.env.ref('base.EUR')
        main_company = self.env.ref('base.main_company')
        self.assertEqual(main_company.currency_id, curr_usd)
        # main_company.currency_id = curr_eur # product.currency_id when no company_id set
        other_company = self.env["res.company"].create({
            "name": "Test",
            "currency_id": curr_eur.id
        })
        user_in_other_company = self.env["res.users"].create({
            "company_id": other_company.id,
            "company_ids": [(6, 0, [other_company.id])],
            "name": "E.T",
            "login": "hohoho",
        })
        user_in_other_company.groups_id |= self.env.ref('sale.group_discount_per_so_line')
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': '2010-01-01',
            'rate': 2.0,
            'currency_id': curr_usd.id,
            "company_id": False,
        })

        product_1.company_id = False
        product_2.company_id = False

        self.assertEqual(product_1.currency_id, curr_usd)
        self.assertEqual(product_2.currency_id, curr_usd)
        self.assertEqual(product_1.cost_currency_id, curr_usd)
        self.assertEqual(product_2.cost_currency_id, curr_usd)

        product_1_ctxt = product_1.with_env(self.env(user=user_in_other_company.id))
        product_2_ctxt = product_2.with_env(self.env(user=user_in_other_company.id))
        self.assertEqual(product_1_ctxt.currency_id, curr_usd)
        self.assertEqual(product_2_ctxt.currency_id, curr_usd)
        self.assertEqual(product_1_ctxt.cost_currency_id, curr_eur)
        self.assertEqual(product_2_ctxt.cost_currency_id, curr_eur)

        product_1.lst_price = 100.0
        product_2_ctxt.standard_price = 10.0 # cost is company_dependent

        pricelist = self.env["product.pricelist"].create({
            "name": "Test multi-currency",
            "discount_policy": "without_discount",
            "currency_id": curr_eur.id,
            "item_ids": [
                (0, 0, {
                    "base": "list_price",
                    "product_id": product_1.id,
                    "compute_price": "percentage",
                    "percent_price": 20,
                }),
                (0, 0, {
                    "base": "standard_price",
                    "product_id": product_2.id,
                    "compute_price": "percentage",
                    "percent_price": 10,
                })
            ]
        })

        # Create a SO in the other company
        ##################################
        # product_currency = main_company.currency_id when no company_id on the product

        # CASE 1:
        # company currency = so currency
        # product_1.currency != so currency
        # product_2.cost_currency_id = so currency
        sales_order = product_1_ctxt.with_context(mail_notrack=True, mail_create_nolog=True).env["sale.order"].create({
            "partner_id": self.env.user.partner_id.id,
            "pricelist_id": pricelist.id,
            "order_line": [
                (0, 0, {
                    "product_id": product_1.id,
                    "product_uom_qty": 1.0
                }),
                (0, 0, {
                    "product_id": product_2.id,
                    "product_uom_qty": 1.0
                })
            ]
        })
        for line in sales_order.order_line:
            # Create values autofill does not compute discount.
            line._onchange_discount()

        so_line_1 = sales_order.order_line[0]
        so_line_2 = sales_order.order_line[1]
        self.assertEqual(so_line_1.discount, 20)
        self.assertEqual(so_line_1.price_unit, 50.0)
        self.assertEqual(so_line_2.discount, 10)
        self.assertEqual(so_line_2.price_unit, 10)

        # CASE 2
        # company currency != so currency
        # product_1.currency == so currency
        # product_2.cost_currency_id != so currency
        pricelist.currency_id = curr_usd
        sales_order = product_1_ctxt.with_context(mail_notrack=True, mail_create_nolog=True).env["sale.order"].create({
            "partner_id": self.env.user.partner_id.id,
            "pricelist_id": pricelist.id,
            "order_line": [
                # Verify discount is considered in create hack
                (0, 0, {
                    "product_id": product_1.id,
                    "product_uom_qty": 1.0
                }),
                (0, 0, {
                    "product_id": product_2.id,
                    "product_uom_qty": 1.0
                })
            ]
        })
        for line in sales_order.order_line:
            line._onchange_discount()

        so_line_1 = sales_order.order_line[0]
        so_line_2 = sales_order.order_line[1]
        self.assertEqual(so_line_1.discount, 20)
        self.assertEqual(so_line_1.price_unit, 100.0)
        self.assertEqual(so_line_2.discount, 10)
        self.assertEqual(so_line_2.price_unit, 20)
