# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import UserError, AccessError
from odoo.tests import Form, tagged
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
