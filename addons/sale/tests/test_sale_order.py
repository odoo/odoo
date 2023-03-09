# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta
from freezegun import freeze_time

from odoo import fields
from odoo.exceptions import UserError, AccessError
from odoo.tests import tagged, Form
from odoo.tools import float_compare

from .common import TestSaleCommon


@tagged('post_install', '-at_install')
class TestSaleOrder(TestSaleCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        SaleOrder = cls.env['sale.order'].with_context(tracking_disable=True)

        # set up users
        cls.crm_team0 = cls.env['crm.team'].create({
            'name': 'crm team 0',
            'company_id': cls.company_data['company'].id
        })
        cls.crm_team1 = cls.env['crm.team'].create({
            'name': 'crm team 1',
            'company_id': cls.company_data['company'].id
        })
        cls.user_in_team = cls.env['res.users'].sudo().create({
            'email': 'team0user@example.com',
            'login': 'team0user',
            'name': 'User in Team 0',
        })
        cls.crm_team0.sudo().write({'member_ids': [4, cls.user_in_team.id]})
        cls.user_not_in_team = cls.env['res.users'].sudo().create({
            'email': 'noteamuser@example.com',
            'login': 'noteamuser',
            'name': 'User Not In Team',
        })

        # create a generic Sale Order with all classical products and empty pricelist
        cls.sale_order = SaleOrder.create({
            'partner_id': cls.partner_a.id,
            'partner_invoice_id': cls.partner_a.id,
            'partner_shipping_id': cls.partner_a.id,
            'pricelist_id': cls.company_data['default_pricelist'].id,
        })
        cls.sol_product_order = cls.env['sale.order.line'].create({
            'name': cls.company_data['product_order_no'].name,
            'product_id': cls.company_data['product_order_no'].id,
            'product_uom_qty': 2,
            'product_uom': cls.company_data['product_order_no'].uom_id.id,
            'price_unit': cls.company_data['product_order_no'].list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })
        cls.sol_serv_deliver = cls.env['sale.order.line'].create({
            'name': cls.company_data['product_service_delivery'].name,
            'product_id': cls.company_data['product_service_delivery'].id,
            'product_uom_qty': 2,
            'product_uom': cls.company_data['product_service_delivery'].uom_id.id,
            'price_unit': cls.company_data['product_service_delivery'].list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })
        cls.sol_serv_order = cls.env['sale.order.line'].create({
            'name': cls.company_data['product_service_order'].name,
            'product_id': cls.company_data['product_service_order'].id,
            'product_uom_qty': 2,
            'product_uom': cls.company_data['product_service_order'].uom_id.id,
            'price_unit': cls.company_data['product_service_order'].list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })
        cls.sol_product_deliver = cls.env['sale.order.line'].create({
            'name': cls.company_data['product_delivery_no'].name,
            'product_id': cls.company_data['product_delivery_no'].id,
            'product_uom_qty': 2,
            'product_uom': cls.company_data['product_delivery_no'].uom_id.id,
            'price_unit': cls.company_data['product_delivery_no'].list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })

    def test_sale_order(self):
        """ Test the sales order flow (invoicing and quantity updates)
            - Invoice repeatedly while varrying delivered quantities and check that invoice are always what we expect
        """
        # TODO?: validate invoice and register payments
        self.sale_order.order_line.read(['name', 'price_unit', 'product_uom_qty', 'price_total'])

        self.assertEqual(self.sale_order.amount_total, 1240.0, 'Sale: total amount is wrong')
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
        self.assertEqual(invoice.amount_total, 740.0, 'Sale: invoice total amount is wrong')
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
        self.assertEqual(invoice2.amount_total, 500.0, 'Sale: second invoice total amount is wrong')
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
        self.assertEqual(invoice3.amount_total, 720.0, 'Sale: second invoice total amount is wrong')
        self.assertTrue(self.sale_order.invoice_status == 'invoiced', 'Sale: SO status after invoicing everything (including the upsel) should be "invoiced"')

    def test_sale_order_send_to_self(self):
        # when sender(logged in user) is also present in recipients of the mail composer,
        # user should receive mail.
        sale_order = self.env['sale.order'].with_user(self.company_data['default_user_salesman']).create({
            'partner_id': self.company_data['default_user_salesman'].partner_id.id,
            'order_line': [[0, 0, {
                'name':  self.company_data['product_order_no'].name,
                'product_id': self.company_data['product_order_no'].id,
                'product_uom_qty': 1,
                'price_unit': self.company_data['product_order_no'].list_price,
            }]]
        })
        email_ctx = sale_order.action_quotation_send().get('context', {})
        # We need to prevent auto mail deletion, and so we copy the template and send the mail with
        # added configuration in copied template. It will allow us to check whether mail is being
        # sent to to author or not (in case author is present in 'Recipients' of composer).
        mail_template = self.env['mail.template'].browse(email_ctx.get('default_template_id')).copy({'auto_delete': False})
        # send the mail with same user as customer
        sale_order.with_context(**email_ctx).with_user(self.company_data['default_user_salesman']).message_post_with_template(mail_template.id)
        self.assertTrue(sale_order.state == 'sent', 'Sale : state should be changed to sent')
        mail_message = sale_order.message_ids[0]
        self.assertEqual(mail_message.author_id, sale_order.partner_id, 'Sale: author should be same as customer')
        self.assertEqual(mail_message.author_id, mail_message.partner_ids, 'Sale: author should be in composer recipients thanks to "partner_to" field set on template')
        self.assertEqual(mail_message.partner_ids, mail_message.sudo().mail_ids.recipient_ids, 'Sale: author should receive mail due to presence in composer recipients')

    def test_invoice_state_when_ordered_quantity_is_negative(self):
        """When you invoice a SO line with a product that is invoiced on ordered quantities and has negative ordered quantity,
        this test ensures that the  invoicing status of the SO line is 'invoiced' (and not 'upselling')."""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'product_id': self.company_data['product_order_no'].id,
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
            so_copy.with_user(self.company_data['default_user_employee']).unlink()
        self.assertTrue(so_copy.unlink(), 'Sale: deleting a quotation should be possible')

        # SO in state 'cancel' can be deleted
        so_copy = self.sale_order.copy()
        so_copy.action_confirm()
        self.assertTrue(so_copy.state == 'sale', 'Sale: SO should be in state "sale"')
        so_copy.action_cancel()
        self.assertTrue(so_copy.state == 'cancel', 'Sale: SO should be in state "cancel"')
        with self.assertRaises(AccessError):
            so_copy.with_user(self.company_data['default_user_employee']).unlink()
        self.assertTrue(so_copy.unlink(), 'Sale: deleting a cancelled SO should be possible')

        # SO in state 'sale' or 'done' cannot be deleted
        self.sale_order.action_confirm()
        self.assertTrue(self.sale_order.state == 'sale', 'Sale: SO should be in state "sale"')
        with self.assertRaises(UserError):
            self.sale_order.unlink()

        self.sale_order.action_done()
        self.assertTrue(self.sale_order.state == 'done', 'Sale: SO should be in state "done"')
        with self.assertRaises(UserError):
            self.sale_order.unlink()

    def test_cost_invoicing(self):
        """ Test confirming a vendor invoice to reinvoice cost on the so """
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
        prod_gap = self.company_data['product_service_order']
        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [(0, 0, {'name': prod_gap.name, 'product_id': prod_gap.id, 'product_uom_qty': 2, 'product_uom': prod_gap.uom_id.id, 'price_unit': prod_gap.list_price})],
            'pricelist_id': self.company_data['default_pricelist'].id,
        })
        so.action_confirm()
        so._create_analytic_account()

        inv = self.env['account.move'].with_context(default_move_type='in_invoice').create({
            'partner_id': self.partner_a.id,
            'invoice_date': so.date_order,
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
        inv.action_post()
        sol = so.order_line.filtered(lambda l: l.product_id == serv_cost)
        self.assertTrue(sol, 'Sale: cost invoicing does not add lines when confirming vendor invoice')
        self.assertEqual((sol.price_unit, sol.qty_delivered, sol.product_uom_qty, sol.qty_invoiced), (160, 2, 0, 0), 'Sale: line is wrong after confirming vendor invoice')

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

            self.assertEqual(float_compare(line.price_subtotal, price, precision_digits=2), 0)

        self.assertEqual(self.sale_order.amount_total,
                          self.sale_order.amount_untaxed + self.sale_order.amount_tax,
                          'Taxes should be applied')

    def test_so_create_multicompany(self):
        """Check that only taxes of the right company are applied on the lines."""

        # Preparing test Data
        product_shared = self.env['product.template'].create({
            'name': 'shared product',
            'invoice_policy': 'order',
            'taxes_id': [(6, False, (self.company_data['default_tax_sale'] + self.company_data_2['default_tax_sale']).ids)],
            'property_account_income_id': self.company_data['default_account_revenue'].id,
        })

        so_1 = self.env['sale.order'].with_user(self.company_data['default_user_salesman']).create({
            'partner_id': self.env['res.partner'].create({'name': 'A partner'}).id,
            'company_id': self.company_data['company'].id,
        })
        so_1.write({
            'order_line': [(0, False, {'product_id': product_shared.product_variant_id.id, 'order_id': so_1.id})],
        })

        self.assertEqual(so_1.order_line.tax_id, self.company_data['default_tax_sale'],
            'Only taxes from the right company are put by default')
        so_1.action_confirm()
        # i'm not interested in groups/acls, but in the multi-company flow only
        # the sudo is there for that and does not impact the invoice that gets created
        # the goal here is to invoice in company 1 (because the order is in company 1) while being
        # 'mainly' in company 2 (through the context), the invoice should be in company 1
        inv=so_1.sudo()\
            .with_context(allowed_company_ids=(self.company_data['company'] + self.company_data_2['company']).ids)\
            ._create_invoices()
        self.assertEqual(inv.company_id, self.company_data['company'], 'invoices should be created in the company of the SO, not the main company of the context')

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

    def test_so_note_to_invoice(self):
        """Test that notes from SO are pushed into invoices"""

        sol_note = self.env['sale.order.line'].create({
            'name': 'This is a note',
            'display_type': 'line_note',
            'product_id': False,
            'product_uom_qty': 0,
            'product_uom': False,
            'price_unit': 0,
            'order_id': self.sale_order.id,
            'tax_id': False,
        })

        # confirm quotation
        self.sale_order.action_confirm()

        # create invoice
        invoice = self.sale_order._create_invoices()

        # check note from SO has been pushed in invoice
        self.assertEqual(len(invoice.invoice_line_ids.filtered(lambda line: line.display_type == 'line_note')), 1, 'Note SO line should have been pushed to the invoice')

    def test_multi_currency_discount(self):
        """Verify the currency used for pricelist price & discount computation."""
        products = self.env["product.product"].search([], limit=2)
        product_1 = products[0]
        product_2 = products[1]

        # Make sure the company is in USD
        main_company = self.env.ref('base.main_company')
        main_curr = main_company.currency_id
        current_curr = self.env.company.currency_id
        other_curr = self.currency_data['currency']
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
        self.assertEqual(product_1.cost_currency_id, current_curr)
        self.assertEqual(product_2.cost_currency_id, current_curr)

        product_1_ctxt = product_1.with_user(user_in_other_company)
        product_2_ctxt = product_2.with_user(user_in_other_company)
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
            'partner_id': self.partner_a.id,
            'team_id': self.crm_team1.id
        })
        sale_order.user_id = self.user_in_team
        sale_order.onchange_user_id()
        self.assertEqual(sale_order.team_id.id, self.crm_team0.id, 'Should assign to team of sales person')

    def test_keep_sales_team_when_changing_user_with_no_team(self):
        """When we assign a sales person that has no team, do not reset the team to default"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'team_id': self.crm_team1.id
        })
        sale_order.user_id = self.user_not_in_team
        sale_order.onchange_user_id()
        self.assertEqual(sale_order.team_id.id, self.crm_team1.id, 'Should not reset the team to default')

    def test_onchange_packaging_00(self):
        """Create a SO and use packaging. Check we suggested suitable packaging
        according to the product_qty. Also check product_qty or product_packaging
        are correctly calculated when one of them changed.
        """
        partner = self.env['res.partner'].create({'name': "I'm a partner"})
        product_tmpl = self.env['product.template'].create({'name': "I'm a product"})
        product = product_tmpl.product_variant_id
        packaging_single = self.env['product.packaging'].create({
            'name': "I'm a packaging",
            'product_id': product.id,
            'qty': 1.0,
        })
        packaging_dozen = self.env['product.packaging'].create({
            'name': "I'm also a packaging",
            'product_id': product.id,
            'qty': 12.0,
        })

        so = self.env['sale.order'].create({
            'partner_id': partner.id,
        })
        so_form = Form(so)
        with so_form.order_line.new() as line:
            line.product_id = product
            line.product_uom_qty = 1.0
        so_form.save()
        self.assertEqual(so.order_line.product_packaging_id, packaging_single)
        self.assertEqual(so.order_line.product_packaging_qty, 1.0)
        with so_form.order_line.edit(0) as line:
            line.product_packaging_qty = 2.0
        so_form.save()
        self.assertEqual(so.order_line.product_uom_qty, 2.0)


        with so_form.order_line.edit(0) as line:
            line.product_uom_qty = 24.0
        so_form.save()
        self.assertEqual(so.order_line.product_packaging_id, packaging_dozen)
        self.assertEqual(so.order_line.product_packaging_qty, 2.0)
        with so_form.order_line.edit(0) as line:
            line.product_packaging_qty = 1.0
        so_form.save()
        self.assertEqual(so.order_line.product_uom_qty, 12)

    def _create_sale_order(self):
        """Create dummy sale order (without lines)"""
        return self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
        })

    def test_invoicing_terms(self):
        # Enable invoicing terms
        self.env['ir.config_parameter'].sudo().set_param('account.use_invoice_terms', True)

        # Plain invoice terms
        self.env.company.terms_type = 'plain'
        self.env.company.invoice_terms = "Coin coin"
        sale_order = self._create_sale_order()
        self.assertEqual(sale_order.note, "<p>Coin coin</p>")

        # Html invoice terms (/terms page)
        self.env.company.terms_type = 'html'
        sale_order = self._create_sale_order()
        self.assertTrue(sale_order.note.startswith("<p>Terms &amp; Conditions: "))

    def test_validity_days(self):
        self.env['ir.config_parameter'].sudo().set_param('sale.use_quotation_validity_days', True)
        self.env.company.quotation_validity_days = 5
        with freeze_time("2020-05-02"):
            sale_order = self._create_sale_order()

            self.assertEqual(sale_order.validity_date, fields.Date.today() + timedelta(days=5))
        self.env.company.quotation_validity_days = 0
        sale_order = self._create_sale_order()
        self.assertFalse(
            sale_order.validity_date,
            "No validity date must be specified if the company validity duration is 0")

    def test_update_prices(self):
        """Test prices recomputation on SO's.

        `update_prices` is shown as a button to update
        prices when the pricelist was changed.
        """
        self.env.user.write({'groups_id': [(4, self.env.ref('product.group_discount_per_so_line').id)]})

        sale_order = self.sale_order
        so_amount = sale_order.amount_total
        sale_order.update_prices()
        self.assertEqual(
            sale_order.amount_total, so_amount,
            "Updating the prices of an unmodified SO shouldn't modify the amounts")

        pricelist = sale_order.pricelist_id
        pricelist.item_ids = [
            fields.Command.create({
                'percent_price': 5.0,
                'compute_price': 'percentage'
            })
        ]
        pricelist.discount_policy = "without_discount"
        self.env['product.product'].invalidate_cache(['price'])
        sale_order.update_prices()

        self.assertTrue(all(line.discount == 5 for line in sale_order.order_line))
        self.assertEqual(sale_order.amount_undiscounted, so_amount)
        self.assertEqual(sale_order.amount_total, 0.95*so_amount)

        pricelist.discount_policy = "with_discount"
        self.env['product.product'].invalidate_cache(['price'])
        sale_order.update_prices()

        self.assertTrue(all(line.discount == 0 for line in sale_order.order_line))
        self.assertEqual(sale_order.amount_undiscounted, so_amount)
        self.assertEqual(sale_order.amount_total, 0.95*so_amount)

    def test_so_names(self):
        """Test custom context key for name_get & name_search.

        Note: this key is used in sale_expense & sale_timesheet modules.
        """
        SaleOrder = self.env['sale.order'].with_context(sale_show_partner_name=True)

        res = SaleOrder.name_search(name=self.sale_order.partner_id.name)
        self.assertEqual(res[0][0], self.sale_order.id)

        self.assertNotIn(self.sale_order.partner_id.name, self.sale_order.display_name)
        self.assertIn(
            self.sale_order.partner_id.name,
            self.sale_order.with_context(sale_show_partner_name=True).name_get()[0][1])

    def test_state_changes(self):
        """Test some untested state changes methods & logic."""
        self.sale_order.action_quotation_sent()

        self.assertEqual(self.sale_order.state, 'sent')
        self.assertIn(self.sale_order.partner_id, self.sale_order.message_follower_ids.partner_id)

        self.env.user.groups_id += self.env.ref('sale.group_auto_done_setting')
        self.sale_order.action_confirm()
        self.assertEqual(self.sale_order.state, 'done', "The order wasn't automatically locked at confirmation.")
        with self.assertRaises(UserError):
            self.sale_order.action_confirm()

        self.sale_order.action_unlock()
        self.assertEqual(self.sale_order.state, 'sale')

    def test_discount_and_untaxed_subtotal(self):
        """When adding a discount on a SO line, this test ensures that the untaxed amount to invoice is
        equal to the untaxed subtotal"""
        self.product_a.invoice_policy = 'delivery'
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'product_id': self.product_a.id,
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
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'product_id': self.product_a.id,
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
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'product_id': self.company_data['product_order_no'].id,
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

    def test_sale_order_analytic_tag_change(self):
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_accounting')
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_tags')

        analytic_account_super = self.env['account.analytic.account'].create({'name': 'Super Account'})
        analytic_account_great = self.env['account.analytic.account'].create({'name': 'Great Account'})
        analytic_tag_super = self.env['account.analytic.tag'].create({'name': 'Super Tag'})
        analytic_tag_great = self.env['account.analytic.tag'].create({'name': 'Great Tag'})
        super_product = self.env['product.product'].create({'name': 'Super Product'})
        great_product = self.env['product.product'].create({'name': 'Great Product'})
        product_no_account = self.env['product.product'].create({'name': 'Product No Account'})
        self.env['account.analytic.default'].create([
            {
                'analytic_id': analytic_account_super.id,
                'product_id': super_product.id,
                'analytic_tag_ids': [analytic_tag_super.id],
            },
            {
                'analytic_id': analytic_account_great.id,
                'product_id': great_product.id,
                'analytic_tag_ids': [analytic_tag_great.id],
            },
        ])
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
        })
        sol = self.env['sale.order.line'].create({
            'name': super_product.name,
            'product_id': super_product.id,
            'order_id': sale_order.id,
        })

        self.assertEqual(sol.analytic_tag_ids.id, analytic_tag_super.id, "The analytic tag should be set to 'Super Tag'")
        sol.write({'product_id': great_product.id})
        self.assertEqual(sol.analytic_tag_ids.id, analytic_tag_great.id, "The analytic tag should be set to 'Great Tag'")
        sol.write({'product_id': product_no_account.id})
        self.assertFalse(sol.analytic_tag_ids.id, "The analytic account should not be set")

        so_no_analytic_account = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
        })
        sol_no_analytic_account = self.env['sale.order.line'].create({
            'name': super_product.name,
            'product_id': super_product.id,
            'order_id': so_no_analytic_account.id,
            'analytic_tag_ids': False,
        })
        so_no_analytic_account.action_confirm()
        self.assertFalse(sol_no_analytic_account.analytic_tag_ids.id, "The compute should not overwrite what the user has set.")

    def test_cannot_assign_tax_of_mismatch_company(self):
        """ Test that sol cannot have assigned tax belonging to a different company from that of the sale order. """
        company_a = self.env['res.company'].create({'name': 'A'})
        company_b = self.env['res.company'].create({'name': 'B'})

        tax_a = self.env['account.tax'].create({
            'name': 'A',
            'amount': 10,
            'company_id': company_a.id,
        })
        tax_b = self.env['account.tax'].create({
            'name': 'B',
            'amount': 10,
            'company_id': company_b.id,
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'company_id': company_a.id
        })
        product = self.env['product.product'].create({'name': 'Product'})

        # In sudo to simulate an user that have access to both companies.
        sol = self.env['sale.order.line'].sudo().create({
            'name': product.name,
            'product_id': product.id,
            'order_id': sale_order.id,
            'tax_id': tax_a,
        })

        with self.assertRaises(UserError):
            sol.tax_id = tax_b
