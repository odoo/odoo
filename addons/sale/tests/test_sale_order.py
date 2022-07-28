# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.exceptions import UserError, AccessError
from odoo.tests import Form
from odoo.tools import float_compare

from .test_sale_common import TestCommonSaleNoChart


class TestSaleOrder(TestCommonSaleNoChart):

    @classmethod
    def setUpClass(cls):
        super(TestSaleOrder, cls).setUpClass()

        SaleOrder = cls.env['sale.order'].with_context(tracking_disable=True)

        # set up users
        cls.setUpUsers()
        group_salemanager = cls.env.ref('sales_team.group_sale_manager')
        group_salesman = cls.env.ref('sales_team.group_sale_salesman')
        group_employee = cls.env.ref('base.group_user')
        cls.user_manager.write({'groups_id': [(6, 0, [group_salemanager.id, group_employee.id])]})
        cls.user_employee.write({'groups_id': [(6, 0, [group_salesman.id, group_employee.id])]})
        cls.crm_team0 = cls.env['crm.team'].create({
            'name': 'crm team 0',
            'company_id': cls.env.user.company_id.id,
        })
        cls.crm_team1 = cls.env['crm.team'].create({
            'name': 'crm team 1',
            'company_id': cls.env.user.company_id.id,
        })
        cls.user_in_team = cls.env['res.users'].create({
            'email': 'team0user@example.com',
            'login': 'team0user',
            'name': 'User in Team 0',
            'sale_team_id': cls.crm_team0.id
        })
        cls.user_not_in_team = cls.env['res.users'].create({
            'email': 'noteamuser@example.com',
            'login': 'noteamuser',
            'name': 'User Not In Team',
        })

        # set up accounts and products and journals
        cls.setUpAdditionalAccounts()
        cls.setUpClassicProducts()
        cls.setUpAccountJournal()

        # create a generic Sale Order with all classical products and empty pricelist
        cls.sale_order = SaleOrder.create({
            'partner_id': cls.partner_customer_usd.id,
            'partner_invoice_id': cls.partner_customer_usd.id,
            'partner_shipping_id': cls.partner_customer_usd.id,
            'pricelist_id': cls.pricelist_usd.id,
        })
        cls.sol_product_order = cls.env['sale.order.line'].create({
            'name': cls.product_order.name,
            'product_id': cls.product_order.id,
            'product_uom_qty': 2,
            'product_uom': cls.product_order.uom_id.id,
            'price_unit': cls.product_order.list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })
        cls.sol_serv_deliver = cls.env['sale.order.line'].create({
            'name': cls.service_deliver.name,
            'product_id': cls.service_deliver.id,
            'product_uom_qty': 2,
            'product_uom': cls.service_deliver.uom_id.id,
            'price_unit': cls.service_deliver.list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })
        cls.sol_serv_order = cls.env['sale.order.line'].create({
            'name': cls.service_order.name,
            'product_id': cls.service_order.id,
            'product_uom_qty': 2,
            'product_uom': cls.service_order.uom_id.id,
            'price_unit': cls.service_order.list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })
        cls.sol_product_deliver = cls.env['sale.order.line'].create({
            'name': cls.product_deliver.name,
            'product_id': cls.product_deliver.id,
            'product_uom_qty': 2,
            'product_uom': cls.product_deliver.uom_id.id,
            'price_unit': cls.product_deliver.list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })

    def test_sale_order(self):
        """ Test the sales order flow (invoicing and quantity updates)
            - Invoice repeatedly while varrying delivered quantities and check that invoice are always what we expect
        """
        # DBO TODO: validate invoice and register payments
        self.sale_order.order_line.read(['name', 'price_unit', 'product_uom_qty', 'price_total'])

        self.assertEqual(self.sale_order.amount_total, sum([2 * p.list_price for p in self.product_map.values()]), 'Sale: total amount is wrong')
        self.sale_order.order_line._compute_product_updatable()
        self.assertTrue(self.sale_order.order_line[0].product_updatable)
        # send quotation
        email_act = self.sale_order.action_quotation_send()
        email_ctx = email_act.get('context', {})
        self.sale_order.with_context(**email_ctx).message_post_with_template(email_ctx.get('default_template_id'))
        self.assertTrue(self.sale_order.state == 'sent', 'Sale: state after sending is wrong')
        self.sale_order.order_line._compute_product_updatable()
        self.assertTrue(self.sale_order.order_line[0].product_updatable)

        # confirm quotation
        self.sale_order.action_confirm()
        self.assertTrue(self.sale_order.state == 'sale')
        self.assertTrue(self.sale_order.invoice_status == 'to invoice')

        # create invoice: only 'invoice on order' products are invoiced
        invoice = self.sale_order._create_invoices()
        self.assertEqual(len(invoice.invoice_line_ids), 2, 'Sale: invoice is missing lines')
        self.assertEqual(invoice.amount_total, sum([2 * p.list_price if p.invoice_policy == 'order' else 0 for p in self.product_map.values()]), 'Sale: invoice total amount is wrong')
        self.assertTrue(self.sale_order.invoice_status == 'no', 'Sale: SO status after invoicing should be "nothing to invoice"')
        self.assertTrue(len(self.sale_order.invoice_ids) == 1, 'Sale: invoice is missing')
        self.sale_order.order_line._compute_product_updatable()
        self.assertFalse(self.sale_order.order_line[0].product_updatable)

        # deliver lines except 'time and material' then invoice again
        for line in self.sale_order.order_line:
            line.qty_delivered = 2 if line.product_id.expense_policy == 'no' else 0
        self.assertTrue(self.sale_order.invoice_status == 'to invoice', 'Sale: SO status after delivery should be "to invoice"')
        invoice2 = self.sale_order._create_invoices()
        self.assertEqual(len(invoice2.invoice_line_ids), 2, 'Sale: second invoice is missing lines')
        self.assertEqual(invoice2.amount_total, sum([2 * p.list_price if p.invoice_policy == 'delivery' else 0 for p in self.product_map.values()]), 'Sale: second invoice total amount is wrong')
        self.assertTrue(self.sale_order.invoice_status == 'invoiced', 'Sale: SO status after invoicing everything should be "invoiced"')
        self.assertTrue(len(self.sale_order.invoice_ids) == 2, 'Sale: invoice is missing')

        # go over the sold quantity
        self.sol_serv_order.write({'qty_delivered': 10})
        self.assertTrue(self.sale_order.invoice_status == 'upselling', 'Sale: SO status after increasing delivered qty higher than ordered qty should be "upselling"')

        # upsell and invoice
        self.sol_serv_order.write({'product_uom_qty': 10})
        # There is a bug with `new` and `_origin`
        # If you create a first new from a record, then change a value on the origin record, than create another new,
        # this other new wont have the updated value of the origin record, but the one from the previous new
        # Here the problem lies in the use of `new` in `move = self_ctx.new(new_vals)`,
        # and the fact this method is called multiple times in the same transaction test case.
        # Here, we update `qty_delivered` on the origin record, but the `new` records which are in cache with this order line
        # as origin are not updated, nor the fields that depends on it.
        self.sol_serv_order.flush()
        for field in self.env['sale.order.line']._fields.values():
            for res_id in list(self.env.cache._data[field]):
                if not res_id:
                    self.env.cache._data[field].pop(res_id)

        invoice3 = self.sale_order._create_invoices()
        self.assertEqual(len(invoice3.invoice_line_ids), 1, 'Sale: third invoice is missing lines')
        self.assertEqual(invoice3.amount_total, 8 * self.product_map['serv_order'].list_price, 'Sale: second invoice total amount is wrong')
        self.assertTrue(self.sale_order.invoice_status == 'invoiced', 'Sale: SO status after invoicing everything (including the upsel) should be "invoiced"')

    def test_invoice_state_when_ordered_quantity_is_negative(self):
        """When you invoice a SO line with a product that is invoiced on ordered quantities and has negative ordered quantity,
        this test ensures that the  invoicing status of the SO line is 'invoiced' (and not 'upselling')."""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_customer_usd.id,
            'order_line': [(0, 0, {
                'product_id': self.product_order.id,
                'product_uom_qty': -1,
            })]
        })
        sale_order.action_confirm()
        sale_order._create_invoices(final=True)
        self.assertTrue(sale_order.invoice_status == 'invoiced', 'Sale: The invoicing status of the SO should be "invoiced"')

    def test_sale_sequence(self):
        self.env['ir.sequence'].search([
            ('code', '=', 'sale.order'),
        ]).write({
            'use_date_range': True, 'prefix': 'SO/%(range_year)s/',
        })
        sale_order = self.sale_order.copy({'date_order': '2019-01-01'})
        self.assertTrue(sale_order.name.startswith('SO/2019/'))
        sale_order = self.sale_order.copy({'date_order': '2020-01-01'})
        self.assertTrue(sale_order.name.startswith('SO/2020/'))
        # In EU/BXL tz, this is actually already 01/01/2020
        sale_order = self.sale_order.with_context(tz='Europe/Brussels').copy({'date_order': '2019-12-31 23:30:00'})
        self.assertTrue(sale_order.name.startswith('SO/2020/'))

    def test_unlink_cancel(self):
        """ Test deleting and cancelling sales orders depending on their state and on the user's rights """
        # SO in state 'draft' can be deleted
        so_copy = self.sale_order.copy()
        with self.assertRaises(AccessError):
            so_copy.with_user(self.user_employee).unlink()
        self.assertTrue(so_copy.with_user(self.user_manager).unlink(), 'Sale: deleting a quotation should be possible')

        # SO in state 'cancel' can be deleted
        so_copy = self.sale_order.copy()
        so_copy.action_confirm()
        self.assertTrue(so_copy.state == 'sale', 'Sale: SO should be in state "sale"')
        so_copy.action_cancel()
        self.assertTrue(so_copy.state == 'cancel', 'Sale: SO should be in state "cancel"')
        with self.assertRaises(AccessError):
            so_copy.with_user(self.user_employee).unlink()
        self.assertTrue(so_copy.with_user(self.user_manager).unlink(), 'Sale: deleting a cancelled SO should be possible')

        # SO in state 'sale' or 'done' cannot be deleted
        self.sale_order.action_confirm()
        self.assertTrue(self.sale_order.state == 'sale', 'Sale: SO should be in state "sale"')
        with self.assertRaises(UserError):
            self.sale_order.with_user(self.user_manager).unlink()

        self.sale_order.action_done()
        self.assertTrue(self.sale_order.state == 'done', 'Sale: SO should be in state "done"')
        with self.assertRaises(UserError):
            self.sale_order.with_user(self.user_manager).unlink()

    def test_cost_invoicing(self):
        """ Test confirming a vendor invoice to reinvoice cost on the so """
        # force the pricelist to have the same currency as the company
        self.pricelist_usd.currency_id = self.env.ref('base.main_company').currency_id

        serv_cost = self.env['product.product'].create({
            'name': "Ordered at cost",
            'standard_price': 160,
            'list_price': 180,
            'type': 'consu',
            'invoice_policy': 'order',
            'expense_policy': 'cost',
            'default_code': 'PROD_COST',
            'service_type': 'manual',
        })
        prod_gap = self.service_order
        so = self.env['sale.order'].create({
            'partner_id': self.partner_customer_usd.id,
            'partner_invoice_id': self.partner_customer_usd.id,
            'partner_shipping_id': self.partner_customer_usd.id,
            'order_line': [(0, 0, {'name': prod_gap.name, 'product_id': prod_gap.id, 'product_uom_qty': 2, 'product_uom': prod_gap.uom_id.id, 'price_unit': prod_gap.list_price})],
            'pricelist_id': self.pricelist_usd.id,
        })
        so.action_confirm()
        so._create_analytic_account()

        inv = self.env['account.move'].with_context(default_type='in_invoice').create({
            'partner_id': self.partner_customer_usd.id,
            'invoice_line_ids': [
                (0, 0, {
                    'name': serv_cost.name,
                    'product_id': serv_cost.id,
                    'product_uom_id': serv_cost.uom_id.id,
                    'quantity': 2,
                    'price_unit': serv_cost.standard_price,
                    'analytic_account_id': so.analytic_account_id.id,
                }),
            ],
        })
        inv.post()
        sol = so.order_line.filtered(lambda l: l.product_id == serv_cost)
        self.assertTrue(sol, 'Sale: cost invoicing does not add lines when confirming vendor invoice')
        self.assertEquals((sol.price_unit, sol.qty_delivered, sol.product_uom_qty, sol.qty_invoiced), (160, 2, 0, 0), 'Sale: line is wrong after confirming vendor invoice')

    def test_sale_with_taxes(self):
        """ Test SO with taxes applied on its lines and check subtotal applied on its lines and total applied on the SO """
        # Create a tax with price included
        tax_include = self.env['account.tax'].create({
            'name': 'Tax with price include',
            'amount': 10,
            'price_include': True
        })
        # Create a tax with price not included
        tax_exclude = self.env['account.tax'].create({
            'name': 'Tax with no price include',
            'amount': 10,
        })

        # Apply taxes on the sale order lines
        self.sol_product_order.write({'tax_id': [(4, tax_include.id)]})
        self.sol_serv_deliver.write({'tax_id': [(4, tax_include.id)]})
        self.sol_serv_order.write({'tax_id': [(4, tax_exclude.id)]})
        self.sol_product_deliver.write({'tax_id': [(4, tax_exclude.id)]})

        # Trigger onchange to reset discount, unit price, subtotal, ...
        for line in self.sale_order.order_line:
            line.product_id_change()
            line._onchange_discount()

        for line in self.sale_order.order_line:
            if line.tax_id.price_include:
                price = line.price_unit * line.product_uom_qty - line.price_tax
            else:
                price = line.price_unit * line.product_uom_qty

            self.assertEquals(float_compare(line.price_subtotal, price, precision_digits=2), 0)

        self.assertEquals(self.sale_order.amount_total,
                          self.sale_order.amount_untaxed + self.sale_order.amount_tax,
                          'Taxes should be applied')

    def test_so_create_multicompany(self):
        """Check that only taxes of the right company are applied on the lines."""
        user_demo = self.env.ref('base.user_demo')
        company_1 = self.env.ref('base.main_company')
        company_2 = self.env['res.company'].create({
            'name': 'company 2',
            'parent_id': company_1.id,
        })
        user_demo.company_ids = (company_1 | company_2).ids

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
            'property_account_income_id': self.account_receivable.id,
        })

        so_1 = self.env['sale.order'].with_user(user_demo.id).create({
            'partner_id': self.env.ref('base.res_partner_2').id,
            'company_id': company_1.id,
        })
        so_1.write({
            'order_line': [(0, False, {'product_id': product_shared.product_variant_id.id, 'order_id': so_1.id})],
        })

        self.assertEqual(set(so_1.order_line.tax_id.ids), set([tax_company_1.id]),
            'Only taxes from the right company are put by default')
        so_1.action_confirm()
        # i'm not interested in groups/acls, but in the multi-company flow only
        # the sudo is there for that and does not impact the invoice that gets created
        # the goal here is to invoice in company 1 (because the order is in company 1) while being
        # 'mainly' in company 2 (through the context), the invoice should be in company 1
        inv=so_1.sudo().with_context(allowed_company_ids=[company_2.id, company_1.id])._create_invoices()
        self.assertEqual(inv.company_id, company_1, 'invoices should be created in the company of the SO, not the main company of the context')


    def test_reconciliation_with_so(self):
        # create SO
        so = self.env['sale.order'].create({
            'name': 'SO/01/01',
            'reference': 'Petit suisse',
            'partner_id': self.partner_customer_usd.id,
            'partner_invoice_id': self.partner_customer_usd.id,
            'partner_shipping_id': self.partner_customer_usd.id,
            'pricelist_id': self.pricelist_usd.id,
        })
        self.env['sale.order.line'].create({
            'name': self.product_order.name,
            'product_id': self.product_order.id,
            'product_uom_qty': 2,
            'product_uom': self.product_order.uom_id.id,
            'price_unit': self.product_order.list_price,
            'order_id': so.id,
            'tax_id': False,
        })
        # Mark SO as sent otherwise we won't find any match
        so.write({'state': 'sent'})
        # Create bank statement
        statement = self.env['account.bank.statement'].create({
            'name': 'Test',
            'journal_id': self.journal_purchase.id,
            'user_id': self.user_employee.id,
        })
        st_line1 = self.env['account.bank.statement.line'].create({
            'name': 'should not find anything',
            'amount': 15,
            'statement_id': statement.id
        })
        st_line2 = self.env['account.bank.statement.line'].create({
            'name': 'Payment for SO/01/01',
            'amount': 15,
            'statement_id': statement.id
        })
        st_line3 = self.env['account.bank.statement.line'].create({
            'name': 'Payment for Petit suisse',
            'amount': 15,
            'statement_id': statement.id
        })
        # Call get_bank_statement_line_data for st_line_1, should not find any sale order
        res = self.env['account.reconciliation.widget'].get_bank_statement_line_data([st_line1.id])
        line = res.get('lines', [{}])[0]
        self.assertFalse(line.get('sale_order_ids', False))
        # Call again for st_line_2, it should find sale_order
        res = self.env['account.reconciliation.widget'].get_bank_statement_line_data([st_line2.id])
        line = res.get('lines', [{}])[0]
        self.assertEquals(line.get('sale_order_ids', []), [so.id])
        # Call again for st_line_3, it should find sale_order based on reference
        res = self.env['account.reconciliation.widget'].get_bank_statement_line_data([st_line3.id])
        line = res.get('lines', [{}])[0]
        self.assertEquals(line.get('sale_order_ids', []), [so.id])

    def test_group_invoice(self):
        """ Test that invoicing multiple sales order for the same customer works. """
        # Create 3 SOs for the same partner, one of which that uses another currency
        eur_pricelist = self.env['product.pricelist'].create({'name': 'EUR', 'currency_id': self.env.ref('base.EUR').id})
        so1 = self.sale_order.with_context(mail_notrack=True).copy()
        so1.pricelist_id = eur_pricelist
        so2 = so1.copy()
        usd_pricelist = self.env['product.pricelist'].create({'name': 'USD', 'currency_id': self.env.ref('base.USD').id})
        so3 = so1.copy()
        so1.pricelist_id = usd_pricelist
        orders = so1 | so2 | so3
        orders.action_confirm()
        # Create the invoicing wizard and invoice all of them at once
        wiz = self.env['sale.advance.payment.inv'].with_context(active_ids=orders.ids, open_invoices=True).create({})
        res = wiz.create_invoices()
        # Check that exactly 2 invoices are generated
        self.assertEqual(len(res['domain'][0][2]),2, "Grouping invoicing 3 orders for the same partner with 2 currencies should create exactly 2 invoices")

    def test_multi_currency_discount(self):
        """Verify the currency used for pricelist price & discount computation."""
        products = self.env["product.product"].search([], limit=2)
        product_1 = products[0]
        product_2 = products[1]

        # Make sure the company is in USD
        main_company = self.env.ref('base.main_company')
        main_curr = main_company.currency_id
        other_curr = (self.env.ref('base.USD') + self.env.ref('base.EUR')) - main_curr
        # main_company.currency_id = other_curr # product.currency_id when no company_id set
        other_company = self.env["res.company"].create({
            "name": "Test",
            "currency_id": other_curr.id
        })
        user_in_other_company = self.env["res.users"].create({
            "company_id": other_company.id,
            "company_ids": [(6, 0, [other_company.id])],
            "name": "E.T",
            "login": "hohoho",
        })
        user_in_other_company.groups_id |= self.env.ref('product.group_discount_per_so_line')
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': '2010-01-01',
            'rate': 2.0,
            'currency_id': main_curr.id,
            "company_id": False,
        })

        product_1.company_id = False
        product_2.company_id = False

        self.assertEqual(product_1.currency_id, main_curr)
        self.assertEqual(product_2.currency_id, main_curr)
        self.assertEqual(product_1.cost_currency_id, main_curr)
        self.assertEqual(product_2.cost_currency_id, main_curr)

        product_1_ctxt = product_1.with_env(self.env(user=user_in_other_company.id))
        product_2_ctxt = product_2.with_env(self.env(user=user_in_other_company.id))
        self.assertEqual(product_1_ctxt.currency_id, main_curr)
        self.assertEqual(product_2_ctxt.currency_id, main_curr)
        self.assertEqual(product_1_ctxt.cost_currency_id, other_curr)
        self.assertEqual(product_2_ctxt.cost_currency_id, other_curr)

        product_1.lst_price = 100.0
        product_2_ctxt.standard_price = 10.0 # cost is company_dependent

        pricelist = self.env["product.pricelist"].create({
            "name": "Test multi-currency",
            "discount_policy": "without_discount",
            "currency_id": other_curr.id,
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
        pricelist.currency_id = main_curr
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

    def test_assign_sales_team_from_partner_user(self):
        """Use the team from the customer's sales person, if it is set"""
        partner = self.env['res.partner'].create({
            'name': 'Customer of User In Team',
            'user_id': self.user_in_team.id,
            'team_id': self.crm_team1.id,
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': partner.id,
        })
        sale_order.onchange_partner_id()
        self.assertEqual(sale_order.team_id.id, self.crm_team0.id, 'Should assign to team of sales person')

    def test_assign_sales_team_from_partner_team(self):
        """If no team set on the customer's sales person, fall back to the customer's team"""
        partner = self.env['res.partner'].create({
            'name': 'Customer of User Not In Team',
            'user_id': self.user_not_in_team.id,
            'team_id': self.crm_team1.id,
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': partner.id,
        })
        sale_order.onchange_partner_id()
        self.assertEqual(sale_order.team_id.id, self.crm_team1.id, 'Should assign to team of partner')

    def test_assign_sales_team_when_changing_user(self):
        """When we assign a sales person, change the team on the sales order to their team"""
        sale_order = self.env['sale.order'].create({
            'user_id': self.user_not_in_team.id,
            'partner_id': self.partner_customer_usd.id,
            'team_id': self.crm_team1.id
        })
        sale_order.user_id = self.user_in_team
        sale_order.onchange_user_id()
        self.assertEqual(sale_order.team_id.id, self.crm_team0.id, 'Should assign to team of sales person')

    def test_keep_sales_team_when_changing_user_with_no_team(self):
        """When we assign a sales person that has no team, do not reset the team to default"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_customer_usd.id,
            'team_id': self.crm_team1.id
        })
        sale_order.user_id = self.user_not_in_team
        sale_order.onchange_user_id()
        self.assertEqual(sale_order.team_id.id, self.crm_team1.id, 'Should not reset the team to default')

    def test_discount_and_untaxed_subtotal(self):
        """When adding a discount on a SO line, this test ensures that the untaxed amount to invoice is
        equal to the untaxed subtotal"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_customer_usd.id,
            'order_line': [(0, 0, {
                'product_id': self.product_deliver.id,
                'product_uom_qty': 38,
                'price_unit': 541.26,
                'discount': 2.00,
            })]
        })
        sale_order.action_confirm()
        line = sale_order.order_line
        self.assertEqual(line.untaxed_amount_to_invoice, 0)

        line.qty_delivered = 38
        # (541.26 - 0.02 * 541.26) * 38 = 20156.5224 ~= 20156.52
        self.assertEqual(line.price_subtotal, 20156.52)
        self.assertEqual(line.untaxed_amount_to_invoice, line.price_subtotal)

        # Same with an included-in-price tax
        sale_order = sale_order.copy()
        line = sale_order.order_line
        line.tax_id = [(0, 0, {
            'name': 'Super Tax',
            'amount_type': 'percent',
            'amount': 15.0,
            'price_include': True,
        })]
        sale_order.action_confirm()
        self.assertEqual(line.untaxed_amount_to_invoice, 0)

        line.qty_delivered = 38
        # (541,26 / 1,15) * ,98 * 38 = 17527,410782609 ~= 17527.41
        self.assertEqual(line.price_subtotal, 17527.41)
        self.assertEqual(line.untaxed_amount_to_invoice, line.price_subtotal)

    def test_discount_and_amount_undiscounted(self):
        """When adding a discount on a SO line, this test ensures that amount undiscounted is
        consistent with the used tax"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_customer_usd.id,
            'order_line': [(0, 0, {
                'product_id': self.product_deliver.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
                'discount': 1.00,
            })]
        })
        sale_order.action_confirm()
        line = sale_order.order_line

        # test discount and qty 1
        self.assertEqual(sale_order.amount_undiscounted, 100.0)
        self.assertEqual(line.price_subtotal, 99.0)

        # more quantity 1 -> 3
        sale_form = Form(sale_order)
        with sale_form.order_line.edit(0) as line_form:
            line_form.product_uom_qty = 3.0
            line_form.price_unit = 100.0
        sale_order = sale_form.save()

        self.assertEqual(sale_order.amount_undiscounted, 300.0)
        self.assertEqual(line.price_subtotal, 297.0)

        # undiscounted
        with sale_form.order_line.edit(0) as line_form:
            line_form.discount = 0.0
        sale_order = sale_form.save()
        self.assertEqual(line.price_subtotal, 300.0)
        self.assertEqual(sale_order.amount_undiscounted, 300.0)

        # Same with an included-in-price tax
        sale_order = sale_order.copy()
        line = sale_order.order_line
        line.tax_id = [(0, 0, {
            'name': 'Super Tax',
            'amount_type': 'percent',
            'amount': 10.0,
            'price_include': True,
        })]
        line.discount = 50.0
        sale_order.action_confirm()

        # 300 with 10% incl tax -> 272.72 total tax excluded without discount
        # 136.36 price tax excluded with discount applied
        self.assertEqual(sale_order.amount_undiscounted, 272.72)
        self.assertEqual(line.price_subtotal, 136.36)

    def test_free_product_and_price_include_fixed_tax(self):
        """ Check that fixed tax include are correctly computed while the price_unit is 0
        """
        # please ensure this test remains consistent with
        # test_out_invoice_line_onchange_2_taxes_fixed_price_include_free_product in account module
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_customer_usd.id,
            'order_line': [(0, 0, {
                'product_id': self.product_deliver.id,
                'product_uom_qty': 1,
                'price_unit': 0.0,
            })]
        })
        sale_order.action_confirm()
        line = sale_order.order_line
        line.tax_id = [
            (0, 0, {
                'name': 'BEBAT 0.05',
                'type_tax_use': 'sale',
                'amount_type': 'fixed',
                'amount': 0.05,
                'price_include': True,
                'include_base_amount': True,
            }),
            (0, 0, {
                'name': 'Recupel 0.25',
                'type_tax_use': 'sale',
                'amount_type': 'fixed',
                'amount': 0.25,
                'price_include': True,
                'include_base_amount': True,
            }),
        ]
        sale_order.action_confirm()
        self.assertRecordValues(sale_order, [{
            'amount_untaxed': -0.30,
            'amount_tax': 0.30,
            'amount_total': 0.0,
        }])

    def test_sol_name_search(self):
        # Shouldn't raise
        self.env['sale.order']._search([('order_line', 'ilike', 'acoustic')])

        name_search_data = self.env['sale.order.line'].name_search(name=self.sale_order.name)
        sol_ids_found = dict(name_search_data).keys()
        self.assertEqual(list(sol_ids_found), self.sale_order.order_line.ids)
