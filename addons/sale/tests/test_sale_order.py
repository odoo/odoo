# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from unittest.mock import patch

from freezegun import freeze_time

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command
from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestSaleOrder(SaleCommon):

    # Those tests do not rely on accounting common on purpose
    #   If you need the accounting setup, use other classes (TestSaleToInvoice probably)

    def test_computes_auto_fill(self):
        free_product, dummy_product = self.env['product.product'].create([{
            'name': 'Free product',
            'list_price': 0.0,
        }, {
            'name': 'Dummy product',
            'list_price': 0.0,
        }])
        # Test pre-computes of lines with order
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'display_type': 'line_section',
                    'name': 'Dummy section',
                }),
                Command.create({
                    'display_type': 'line_section',
                    'name': 'Dummy section',
                }),
                Command.create({
                    'product_id': free_product.id,
                }),
                Command.create({
                    'product_id': dummy_product.id,
                })
            ]
        })

        # Test pre-computes of lines creation alone
        # Ensures the creation works fine even if the computes
        # are triggered after the defaults
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        self.env['sale.order.line'].create([
            {
                'display_type': 'line_section',
                'name': 'Dummy section',
                'order_id': order.id,
            }, {
                'display_type': 'line_section',
                'name': 'Dummy section',
                'order_id': order.id,
            }, {
                'product_id': free_product.id,
                'order_id': order.id,
            }, {
                'product_id': dummy_product.id,
                'order_id': order.id,
            }
        ])

    def test_sale_order_standard_flow(self):
        self.assertEqual(self.sale_order.amount_total, 725.0, 'Sale: total amount is wrong')
        self.sale_order.order_line._compute_product_updatable()
        self.assertTrue(self.sale_order.order_line[0].product_updatable)

        # send quotation
        email_act = self.sale_order.action_quotation_send()
        email_ctx = email_act.get('context', {})
        self.sale_order.with_context(**email_ctx).message_post_with_source(
            self.env['mail.template'].browse(email_ctx.get('default_template_id')),
            subtype_xmlid='mail.mt_comment',
        )
        self.assertTrue(self.sale_order.state == 'sent', 'Sale: state after sending is wrong')
        self.sale_order.order_line._compute_product_updatable()
        self.assertTrue(self.sale_order.order_line[0].product_updatable)

        # confirm quotation
        self.sale_order.action_confirm()
        self.assertTrue(self.sale_order.state == 'sale')
        self.assertTrue(self.sale_order.invoice_status == 'to invoice')

    def test_sale_order_send_to_self(self):
        # when sender(logged in user) is also present in recipients of the mail composer,
        # user should receive mail.
        sale_order = self.env['sale.order'].with_user(self.sale_user).create({
            'partner_id': self.sale_user.partner_id.id,
        })
        email_ctx = sale_order.action_quotation_send().get('context', {})
        # We need to prevent auto mail deletion, and so we copy the template and send the mail with
        # added configuration in copied template. It will allow us to check whether mail is being
        # sent to to author or not (in case author is present in 'Recipients' of composer).
        mail_template = self.env['mail.template'].browse(email_ctx.get('default_template_id')).copy({'auto_delete': False})
        # send the mail with same user as customer
        sale_order.with_context(**email_ctx).with_user(self.sale_user).message_post_with_source(
            mail_template,
            subtype_xmlid='mail.mt_comment',
        )
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
            so_copy.with_user(self.sale_user).unlink()
        self.assertTrue(so_copy.unlink(), 'Sale: deleting a quotation should be possible')

        # SO in state 'cancel' can be deleted
        so_copy = self.sale_order.copy()
        so_copy.action_confirm()
        self.assertTrue(so_copy.state == 'sale', 'Sale: SO should be in state "sale"')
        so_copy._action_cancel()
        self.assertTrue(so_copy.state == 'cancel', 'Sale: SO should be in state "cancel"')
        with self.assertRaises(AccessError):
            so_copy.with_user(self.sale_user).unlink()
        self.assertTrue(so_copy.unlink(), 'Sale: deleting a cancelled SO should be possible')

        # SO in state 'sale' cannot be deleted
        self.sale_order.action_confirm()
        self.assertTrue(self.sale_order.state == 'sale', 'Sale: SO should be in state "sale"')
        with self.assertRaises(UserError):
            self.sale_order.unlink()

        self.sale_order.action_lock()
        self.assertTrue(self.sale_order.state == 'sale')
        self.assertTrue(self.sale_order.locked)
        with self.assertRaises(UserError):
            self.sale_order.unlink()

    def test_compute_packaging_00(self):
        """Create a SO and use packaging. Check we suggested suitable packaging
        according to the product_qty. Also check product_qty or product_packaging
        are correctly calculated when one of them changed.
        """
        # Required for `product_packaging_qty` to be visible in the view
        self.env.user.groups_id += self.env.ref('product.group_stock_packaging')
        packaging_single, packaging_dozen = self.env['product.packaging'].create([{
            'name': "I'm a packaging",
            'product_id': self.product.id,
            'qty': 1.0,
        }, {
            'name': "I'm also a packaging",
            'product_id': self.product.id,
            'qty': 12.0,
        }])

        so = self.empty_order
        so_form = Form(so)
        with so_form.order_line.new() as line:
            line.product_id = self.product
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

        packaging_pack_of_10 = self.env['product.packaging'].create({
            'name': "PackOf10",
            'product_id': self.product.id,
            'qty': 10.0,
        })
        packaging_pack_of_20 = self.env['product.packaging'].create({
            'name': "PackOf20",
            'product_id': self.product.id,
            'qty': 20.0,
        })

        so2 = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        so2_form = Form(so2)
        with so2_form.order_line.new() as line:
            line.product_id = self.product
            line.product_uom_qty = 10
        so2_form.save()
        self.assertEqual(so2.order_line.product_packaging_id.id, packaging_pack_of_10.id)
        self.assertEqual(so2.order_line.product_packaging_qty, 1.0)

        with so2_form.order_line.edit(0) as line:
            line.product_packaging_qty = 2
        so2_form.save()
        self.assertEqual(so2.order_line.product_uom_qty, 20)
        # we should have 2 pack of 10, as we've set the package_qty manually,
        # we shouldn't recompute the packaging_id, since the package_qty is protected,
        # therefor cannot be recomputed during the same transaction, which could lead
        # to an incorrect line like (qty=20,pack_qty=2,pack_id=PackOf20)
        self.assertEqual(so2.order_line.product_packaging_qty, 2)
        self.assertEqual(so2.order_line.product_packaging_id.id, packaging_pack_of_10.id)

        with so2_form.order_line.edit(0) as line:
            line.product_packaging_id = packaging_pack_of_20
        so2_form.save()
        self.assertEqual(so2.order_line.product_uom_qty, 20)
        # we should have 1 pack of 20, as we've set the package type manually
        self.assertEqual(so2.order_line.product_packaging_qty, 1)
        self.assertEqual(so2.order_line.product_packaging_id.id, packaging_pack_of_20.id)

    def test_compute_packaging_01(self):
        """Create a SO and use packaging in a multicompany environment.
        Ensure any suggested packaging matches the SO's.
        """
        company2 = self.env['res.company'].create([{'name': 'Company 2'}])
        generic_single_pack = self.env['product.packaging'].create({
            'name': "single pack",
            'product_id': self.product.id,
            'qty': 1.0,
            'company_id': False,
        })
        company2_pack_of_10 = self.env['product.packaging'].create({
            'name': "pack of 10 by Company 2",
            'product_id': self.product.id,
            'qty': 10.0,
            'company_id': company2.id,
        })

        so1 = self.empty_order
        so1_form = Form(so1)
        with so1_form.order_line.new() as line:
            line.product_id = self.product
            line.product_uom_qty = 10.0
        so1_form.save()
        self.assertEqual(so1.order_line.product_packaging_id, generic_single_pack)
        self.assertEqual(so1.order_line.product_packaging_qty, 10.0)

        so2 = self.env['sale.order'].with_company(company2).create({
            'partner_id': self.partner.id,
        })
        so2_form = Form(so2)
        with so2_form.order_line.new() as line:
            line.product_id = self.product
            line.product_uom_qty = 10.0
        so2_form.save()
        self.assertEqual(so2.order_line.product_packaging_id, company2_pack_of_10)
        self.assertEqual(so2.order_line.product_packaging_qty, 1.0)

    def _create_sale_order(self):
        """Create dummy sale order (without lines)"""
        return self.env['sale.order'].with_context(
            default_sale_order_template_id=False
            # Do not modify test behavior even if sale_management is installed
        ).create({
            'partner_id': self.partner.id,
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
        self.env.company.quotation_validity_days = 5
        with freeze_time("2020-05-02"):
            sale_order = self._create_sale_order()

            self.assertEqual(sale_order.validity_date, fields.Date.today() + timedelta(days=5))
        self.env.company.quotation_validity_days = 0
        sale_order = self._create_sale_order()
        self.assertFalse(
            sale_order.validity_date,
            "No validity date must be specified if the company validity duration is 0")

    def test_so_names(self):
        """Test custom context key for display_name & name_search.

        Note: this key is used in sale_expense & sale_timesheet modules.
        """
        SaleOrder = self.env['sale.order'].with_context(sale_show_partner_name=True)

        res = SaleOrder.name_search(name=self.sale_order.partner_id.name)
        self.assertEqual(res[0][0], self.sale_order.id)

        self.assertNotIn(self.sale_order.partner_id.name, self.sale_order.display_name)
        self.assertIn(
            self.sale_order.partner_id.name,
            self.sale_order.with_context(sale_show_partner_name=True).display_name)

    def test_state_changes(self):
        """Test some untested state changes methods & logic."""
        self.sale_order.action_quotation_sent()

        self.assertEqual(self.sale_order.state, 'sent')
        self.assertIn(self.sale_order.partner_id, self.sale_order.message_follower_ids.partner_id)

        self.env.user.groups_id += self.env.ref('sale.group_auto_done_setting')
        self.sale_order.action_confirm()
        self.assertEqual(self.sale_order.state, 'sale')
        self.assertTrue(self.sale_order.locked)
        with self.assertRaises(UserError):
            self.sale_order.action_confirm()

        self.sale_order.action_unlock()
        self.assertEqual(self.sale_order.state, 'sale')

    def test_sol_name_search(self):
        # Shouldn't raise
        self.env['sale.order']._search([('order_line', 'ilike', 'product')])

        name_search_data = self.env['sale.order.line'].name_search(name=self.sale_order.name)
        sol_ids_found = dict(name_search_data).keys()
        self.assertEqual(list(sol_ids_found), self.sale_order.order_line.ids)

    def test_zero_quantity(self):
        """
            If the quantity set is 0 it should remain to 0
            Test that changing the uom do not change the quantity
        """
        order_line = self.sale_order.order_line[0]
        order_line.product_uom_qty = 0.0
        order_line.product_uom = self.uom_dozen
        self.assertEqual(order_line.product_uom_qty, 0.0)

    def test_discount_rounding(self):
        """
            Check the discount is properly rounded and the price subtotal
            computed with this rounded discount
        """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 192,
                'discount': 74.246,
            })]
        })
        self.assertEqual(sale_order.order_line.price_subtotal, 49.44, "Subtotal should be equal to 192 * (1 - 0.7425)")
        self.assertEqual(sale_order.order_line.discount, 74.25)

    def test_tax_amount_rounding(self):
        """ Check order amounts are rounded according to settings """

        tax_a = self.env['account.tax'].create({
            'name': 'Test tax',
            'type_tax_use': 'sale',
            'price_include': False,
            'amount_type': 'percent',
            'amount': 15.0,
        })

        # Test Round per Line (default)
        self.env.company.tax_calculation_rounding_method = 'round_per_line'
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'product_uom_qty': 1,
                    'price_unit': 6.7,
                    'discount': 0,
                    'tax_id': tax_a.ids,
                }),
                Command.create({
                    'product_id': self.product.id,
                    'product_uom_qty': 1,
                    'price_unit': 6.7,
                    'discount': 0,
                    'tax_id': tax_a.ids,
                }),
            ],
        })
        self.assertEqual(sale_order.amount_total, 15.42, "")

        # Test Round Globally
        self.env.company.tax_calculation_rounding_method = 'round_globally'
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'product_uom_qty': 1,
                    'price_unit': 6.7,
                    'discount': 0,
                    'tax_id': tax_a.ids,
                }),
                Command.create({
                    'product_id': self.product.id,
                    'product_uom_qty': 1,
                    'price_unit': 6.7,
                    'discount': 0,
                    'tax_id': tax_a.ids,
                }),
            ],
        })
        self.assertEqual(sale_order.amount_total, 15.41, "")

    def test_order_auto_lock_with_public_user(self):
        public_user = self.env.ref('base.public_user')
        self.sale_order.create_uid.groups_id += self.env.ref('sale.group_auto_done_setting')
        self.sale_order.with_user(public_user.id).sudo().action_confirm()

        self.assertFalse(public_user.has_group('sale.group_auto_done_setting'))
        self.assertTrue(self.sale_order.locked)

    def test_generate_account_analytic_when_confirm_so(self):
        """ Test generate account analytic when SO with expense product is confirmed """
        restaurant_expenses_product = self.env['product.product'].create({
            'name': 'Restaurant Expenses',
            'type': 'service',
            'expense_policy': 'sales_price',
            'list_price': 14.0,
            'standard_price': 10.0,
        })
        sale_order = self.env['sale.order'].with_user(self.sale_user).create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({
                'product_id': restaurant_expenses_product.id,
                'product_uom_qty': 1,
            })],
        })
        self.assertFalse(sale_order.analytic_account_id)
        sale_order.action_confirm()
        self.assertTrue(sale_order.analytic_account_id, "An analytic account should be generated")

    def test_so_discount_is_not_reset(self):
        """ Discounts should not be recomputed on order confirmation """
        with patch(
            'odoo.addons.sale.models.sale_order_line.SaleOrderLine'
            '._compute_discount'
        ) as patched:
            self.sale_order.action_confirm()
            self.sale_order.order_line.flush_recordset(['discount'])
            patched.assert_not_called()

    def test_so_is_not_invoiceable_if_only_discount_line_is_to_invoice(self):
        self.sale_order.order_line.product_id.invoice_policy = 'delivery'
        self.sale_order.action_confirm()

        self.assertEqual(self.sale_order.invoice_status, 'no')
        standard_lines = self.sale_order.order_line

        self.env['sale.order.discount'].create({
            'sale_order_id': self.sale_order.id,
            'discount_amount': 33,
            'discount_type': 'amount',
        }).action_apply_discount()

        # Only the discount line is invoiceable (there are lines not invoiced and not invoiceable)
        discount_line = self.sale_order.order_line - standard_lines
        self.assertEqual(discount_line.invoice_status, 'to invoice')
        self.assertEqual(self.sale_order.invoice_status, 'no')

    def test_so_is_invoiceable_if_only_discount_line_remains_to_invoice(self):
        self.sale_order.order_line.product_id.invoice_policy = 'delivery'
        self.sale_order.action_confirm()

        self.assertEqual(self.sale_order.invoice_status, 'no')
        standard_lines = self.sale_order.order_line

        for sol in standard_lines:
            sol.qty_delivered = sol.product_uom_qty
        self.sale_order._create_invoices()

        self.assertEqual(self.sale_order.invoice_status, 'invoiced')

        self.env['sale.order.discount'].create({
            'sale_order_id': self.sale_order.id,
            'discount_amount': 33,
            'discount_type': 'amount',
        }).action_apply_discount()

        # Only the discount line is invoiceable (there are no other lines remaining to invoice)
        discount_line = (self.sale_order.order_line - standard_lines)
        self.assertEqual(discount_line.invoice_status, 'to invoice')
        self.assertEqual(self.sale_order.invoice_status, 'to invoice')

    def test_sale_order_line_product_taxes_on_branch(self):
        """ Check taxes populated on SO lines from product on branch company.
            Taxes from the branch company should be taken with a fallback on parent company.
        """
        # create the following branch hierarchy:
        #     Parent company
        #         |----> Branch X
        #                   |----> Branch XX
        company = self.env.company
        branch_x = self.env['res.company'].create({
            'name': 'Branch X',
            'country_id': company.country_id.id,
            'parent_id': company.id,
        })
        branch_xx = self.env['res.company'].create({
            'name': 'Branch XX',
            'country_id': company.country_id.id,
            'parent_id': branch_x.id,
        })
        # create taxes for the parent company and its branches
        tax_groups = self.env['account.tax.group'].create([{
            'name': 'Tax Group',
            'company_id': company.id,
        }, {
            'name': 'Tax Group X',
            'company_id': branch_x.id,
        }, {
            'name': 'Tax Group XX',
            'company_id': branch_xx.id,
        }])
        tax_a = self.env['account.tax'].create({
            'name': 'Tax A',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 10,
            'tax_group_id': tax_groups[0].id,
            'company_id': company.id,
        })
        tax_b = self.env['account.tax'].create({
            'name': 'Tax B',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 15,
            'tax_group_id': tax_groups[0].id,
            'company_id': company.id,
        })
        tax_x = self.env['account.tax'].create({
            'name': 'Tax X',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 20,
            'tax_group_id': tax_groups[1].id,
            'company_id': branch_x.id,
        })
        tax_xx = self.env['account.tax'].create({
            'name': 'Tax XX',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 25,
            'tax_group_id': tax_groups[2].id,
            'company_id': branch_xx.id,
        })
        # create several products with different taxes combination
        product_all_taxes = self.env['product.product'].create({
            'name': 'Product all taxes',
            'taxes_id': [Command.set((tax_a + tax_b + tax_x + tax_xx).ids)],
        })
        product_no_xx_tax = self.env['product.product'].create({
            'name': 'Product no tax from XX',
            'taxes_id': [Command.set((tax_a + tax_b + tax_x).ids)],
        })
        product_no_branch_tax = self.env['product.product'].create({
            'name': 'Product no tax from branch',
            'taxes_id': [Command.set((tax_a + tax_b).ids)],
        })
        product_no_tax = self.env['product.product'].create({
            'name': 'Product no tax',
            'taxes_id': [],
        })
        # create a SO from Branch XX
        so_form = Form(self.env['sale.order'].with_company(branch_xx))
        so_form.partner_id = self.partner
        # add 4 SO lines with the different products:
        # - Product all taxes           => tax from Branch XX should be set
        # - Product no tax from XX      => tax from Branch X should be set
        # - Product no tax from branch  => 2 taxes from parent company should be set
        # - Product no tax              => no tax should be set
        with so_form.order_line.new() as line:
            line.product_id = product_all_taxes
        with so_form.order_line.new() as line:
            line.product_id = product_no_xx_tax
        with so_form.order_line.new() as line:
            line.product_id = product_no_branch_tax
        with so_form.order_line.new() as line:
            line.product_id = product_no_tax
        so = so_form.save()
        self.assertRecordValues(so.order_line, [
            {'product_id': product_all_taxes.id, 'tax_id': tax_xx.ids},
            {'product_id': product_no_xx_tax.id, 'tax_id': tax_x.ids},
            {'product_id': product_no_branch_tax.id, 'tax_id': (tax_a + tax_b).ids},
            {'product_id': product_no_tax.id, 'tax_id': []},
        ])


@tagged('post_install', '-at_install')
class TestSaleOrderInvoicing(AccountTestInvoicingCommon, SaleCommon):
    def test_invoice_state_when_ordered_quantity_is_negative(self):
        """When you invoice a SO line with a product that is invoiced on ordered quantities and has negative ordered quantity,
        this test ensures that the  invoicing status of the SO line is 'invoiced' (and not 'upselling')."""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': -1,
            })]
        })
        sale_order.action_confirm()
        sale_order._create_invoices(final=True)
        self.assertTrue(sale_order.invoice_status == 'invoiced', 'Sale: The invoicing status of the SO should be "invoiced"')


@tagged('post_install', '-at_install')
class TestSalesTeam(SaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # set up users
        cls.sale_team_2 = cls.env['crm.team'].create({
            'name': 'Test Sales Team (2)',
        })
        cls.user_in_team = cls.env['res.users'].create({
            'email': 'team0user@example.com',
            'login': 'team0user',
            'name': 'User in Team 0',
        })
        cls.sale_team.write({'member_ids': [4, cls.user_in_team.id]})
        cls.user_not_in_team = cls.env['res.users'].create({
            'email': 'noteamuser@example.com',
            'login': 'noteamuser',
            'name': 'User Not In Team',
        })

    def test_assign_sales_team_from_partner_user(self):
        """Use the team from the customer's sales person, if it is set"""
        partner = self.env['res.partner'].create({
            'name': 'Customer of User In Team',
            'user_id': self.user_in_team.id,
            'team_id': self.sale_team_2.id,
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': partner.id,
        })
        self.assertEqual(sale_order.team_id.id, self.sale_team.id, 'Should assign to team of sales person')

    def test_assign_sales_team_from_partner_team(self):
        """If no team set on the customer's sales person, fall back to the customer's team"""
        partner = self.env['res.partner'].create({
            'name': 'Customer of User Not In Team',
            'user_id': self.user_not_in_team.id,
            'team_id': self.sale_team_2.id,
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': partner.id,
        })
        self.assertEqual(sale_order.team_id.id, self.sale_team_2.id, 'Should assign to team of partner')

    def test_assign_sales_team_when_changing_user(self):
        """When we assign a sales person, change the team on the sales order to their team"""
        sale_order = self.env['sale.order'].create({
            'user_id': self.user_not_in_team.id,
            'partner_id': self.partner.id,
            'team_id': self.sale_team_2.id
        })
        sale_order.user_id = self.user_in_team
        self.assertEqual(sale_order.team_id.id, self.sale_team.id, 'Should assign to team of sales person')

    def test_keep_sales_team_when_changing_user_with_no_team(self):
        """When we assign a sales person that has no team, do not reset the team to default"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'team_id': self.sale_team_2.id
        })
        sale_order.user_id = self.user_not_in_team
        self.assertEqual(sale_order.team_id.id, self.sale_team_2.id, 'Should not reset the team to default')

    def test_sale_order_analytic_distribution_change(self):
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_accounting')

        analytic_plan = self.env['account.analytic.plan'].create({'name': 'Plan Test'})
        analytic_account_super = self.env['account.analytic.account'].create({'name': 'Super Account', 'plan_id': analytic_plan.id})
        analytic_account_great = self.env['account.analytic.account'].create({'name': 'Great Account', 'plan_id': analytic_plan.id})
        super_product = self.env['product.product'].create({'name': 'Super Product'})
        great_product = self.env['product.product'].create({'name': 'Great Product'})
        product_no_account = self.env['product.product'].create({'name': 'Product No Account'})
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
        partner = self.env['res.partner'].create({'name': 'Test Partner'})
        sale_order = self.env['sale.order'].create({
            'partner_id': partner.id,
        })
        sol = self.env['sale.order.line'].create({
            'name': super_product.name,
            'product_id': super_product.id,
            'order_id': sale_order.id,
        })

        self.assertEqual(sol.analytic_distribution, {str(analytic_account_super.id): 100}, "The analytic distribution should be set to Super Account")
        sol.write({'product_id': great_product.id})
        self.assertEqual(sol.analytic_distribution, {str(analytic_account_great.id): 100}, "The analytic distribution should be set to Great Account")

        so_no_analytic_account = self.env['sale.order'].create({
            'partner_id': partner.id,
        })
        sol_no_analytic_account = self.env['sale.order.line'].create({
            'name': super_product.name,
            'product_id': super_product.id,
            'order_id': so_no_analytic_account.id,
            'analytic_distribution': False,
        })
        so_no_analytic_account.action_confirm()
        self.assertFalse(sol_no_analytic_account.analytic_distribution, "The compute should not overwrite what the user has set.")

        sale_order.action_confirm()
        sol_on_confirmed_order = self.env['sale.order.line'].create({
            'name': super_product.name,
            'product_id': super_product.id,
            'order_id': sale_order.id,
        })

        self.assertEqual(
            sol_on_confirmed_order.analytic_distribution,
            {str(analytic_account_super.id): 100},
            "The analytic distribution should be set to Super Account, even for confirmed orders"
        )


    def test_cannot_assign_tax_of_mismatch_company(self):
        """ Test that sol cannot have assigned tax belonging to a different company from that of the sale order. """
        company_a = self.env['res.company'].create({'name': 'A'})
        company_b = self.env['res.company'].create({'name': 'B'})
        tax_group_a = self.env['account.tax.group'].create({'name': 'A', 'company_id': company_a.id})
        tax_group_b = self.env['account.tax.group'].create({'name': 'B', 'company_id': company_b.id})
        country = self.env['res.country'].search([], limit=1)

        tax_a = self.env['account.tax'].create({
            'name': 'A',
            'amount': 10,
            'company_id': company_a.id,
            'tax_group_id': tax_group_a.id,
            'country_id': country.id,
        })
        tax_b = self.env['account.tax'].create({
            'name': 'B',
            'amount': 10,
            'company_id': company_b.id,
            'tax_group_id': tax_group_b.id,
            'country_id': country.id,
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
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

    def test_assign_tax_multi_company(self):
        root_company = self.env['res.company'].create({'name': 'B0 company'})
        root_company.write({'child_ids': [
            Command.create({'name': 'B1 company'}),
            Command.create({'name': 'B2 company'}),
        ]})

        country = self.env['res.country'].search([], limit=1)
        basic_tax_group = self.env['account.tax.group'].create({'name': 'basic group', 'country_id': country.id})
        tax_b0 = self.env['account.tax'].create({
            'name': 'B0 tax',
            'company_id': root_company.id,
            'amount': 10,
            'tax_group_id': basic_tax_group.id,
            'country_id': country.id,
        })
        tax_b1 = self.env['account.tax'].create({
            'name': 'B1 tax',
            'company_id': root_company.child_ids[0].id,
            'amount': 11,
            'tax_group_id': basic_tax_group.id,
            'country_id': country.id,
        })
        tax_b2 = self.env['account.tax'].create({
            'name': 'B2 tax',
            'company_id': root_company.child_ids[1].id,
            'amount': 20,
            'tax_group_id': basic_tax_group.id,
            'country_id': country.id,
        })

        sale_order = self.env['sale.order'].create({'partner_id': self.partner.id, 'company_id': root_company.child_ids[0].id})
        product = self.env['product.product'].create({'name': 'Product'})

        # In sudo to simulate an user that have access to both companies.
        sol_b1 = self.env['sale.order.line'].sudo().create({
            'name': product.name,
            'product_id': product.id,
            'order_id': sale_order.id,
            'tax_id': tax_b1,
        })

        # should not raise anything
        sol_b1.tax_id = tax_b0
        sol_b1.tax_id = tax_b1
        # should raise (b2 is not on the same branch lineage as b1)
        with self.assertRaises(UserError):
            sol_b1.tax_id = tax_b2

    def test_downpayment_amount_constraints(self):
        """Down payment amounts should be in the interval ]0, 1]."""

        self.sale_order.require_payment = True
        with self.assertRaises(ValidationError):
            self.sale_order.prepayment_percent = -1
        with self.assertRaises(ValidationError):
            self.sale_order.prepayment_percent = 1.01

    def test_sales_team_defined_on_partner_user_no_team(self):
        """ Test that sale order picks up a team from res.partner on change if user has no team specified """

        crm_team0 = self.env['crm.team'].create({
            'name':"Test Team A"
        })

        crm_team1 = self.env['crm.team'].create({
            'name':"Test Team B"
        })

        partner_a = self.env['res.partner'].create({
            'name': 'Partner A',
            'team_id': crm_team0.id,
        })

        partner_b = self.env['res.partner'].create({
            'name': 'Partner B',
            'team_id': crm_team1.id,
        })

        sale_order = self.env['sale.order'].with_user(self.user_not_in_team).create({
            'partner_id': partner_a.id,
        })

        self.assertEqual(sale_order.team_id, crm_team0, "Sales team should change to partner's")
        sale_order.with_user(self.user_not_in_team).write({'partner_id': partner_b.id})
        self.assertEqual(sale_order.team_id, crm_team1, "Sales team should change to partner's")

    def test_qty_delivered_on_creation(self):
        """Checks that the qty delivered of sol is automatically set to 0.0 when an so is created"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                })],
        })
        # As we want to determine if the value is set in the DB we need to perform a search
        self.assertFalse(self.env['sale.order.line'].search(['&', ('order_id', '=', sale_order.id), ('qty_delivered', '=', False)]))
        self.assertEqual(self.env['sale.order.line'].search(['&', ('order_id', '=', sale_order.id), ('qty_delivered', '=', 0.0)]), sale_order.order_line)

    def test_action_recompute_taxes(self):
        '''
        This test verifies the taxes recomputation action that can be triggered
        after updating the fiscal position on a sale order document.
        '''
        special_tax = self.env['account.tax'].create({
            'name': "special_tax_10",
            'amount_type': 'percent',
            'amount': 25.0,
            'include_base_amount': True,
            'price_include': True,
        })

        mapped_tax_a = self.env['account.tax'].create({
            'name': "tax_a",
            'amount_type': 'percent',
            'amount': 12.5,
            'include_base_amount': True,
            'price_include': True,
        })

        mapped_tax_b = self.env['account.tax'].create({
            'name': "tax_b",
            'amount_type': 'percent',
            'amount': 5.0,
            'include_base_amount': True,
            'price_include': True,
        })

        sales_tax = self.env['account.tax'].create({
            'name': "VAT 20%",
            'amount_type': 'percent',
            'amount': 20.0,
            'price_include': True,
        })

        mapping_a = self.env['account.fiscal.position'].create({
            'name': 'Special Tax Reduction',
            'tax_ids': [Command.create({'tax_src_id': special_tax.id, 'tax_dest_id': mapped_tax_a.id})],
        })
        mapping_b = self.env['account.fiscal.position'].create({
            'name': 'Special Tax Reduction',
            'tax_ids': [Command.create({'tax_src_id': special_tax.id, 'tax_dest_id': mapped_tax_b.id})],
        })

        # taxes and standard price need to be set on the product, as they will be
        # recomputed when changing the fiscal position.
        self.consumable_product.write({
            'lst_price': 300,
            'taxes_id': [Command.set((special_tax + sales_tax).ids)],
        })

        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.consumable_product.id,
                    'product_uom_qty': 1.0,
                }),
            ],
        })

        self.assertEqual(order.amount_total, 300)
        self.assertEqual(order.amount_tax, 100)
        order.fiscal_position_id = mapping_a
        order._recompute_prices()
        order.action_update_taxes()
        self.assertEqual(order.amount_total, 270)
        self.assertEqual(order.amount_tax, 70)
        order.fiscal_position_id = mapping_b
        order._recompute_prices()
        order.action_update_taxes()
        self.assertEqual(order.amount_total, 252)
        self.assertEqual(order.amount_tax, 52)

    def test_recompute_taxes_rounded_globally_multi_company_currency(self):
        '''
        Check that taxes computation are made in the currency of the company
        configured on the SO lines.
        '''
        # create a currency with no decimal
        currency_b = self.env['res.currency'].create({
            'name': 'B',
            'symbol': 'B',
            'rounding': 1.000000,
        })
        # create a company with USD as currency (rounding == 0.01)
        company_a = self.env['res.company'].create({
            'name': 'Company A',
            'country_id': self.env.ref('base.us').id,
        })
        # create a company with currency_b as currency
        company_b = self.env['res.company'].create({
            'name': 'Company B',
            'tax_calculation_rounding_method': 'round_globally',
            'currency_id': currency_b.id,
        })
        # set company_b as default company of current user
        self.env.user.company_id = company_b
        tax_group_a = self.env['account.tax.group'].create({
            'name': 'Tax Group A',
            'company_id': company_a.id,
        })
        tax_a = self.env['account.tax'].create({
            'name': 'Tax A',
            'amount': 10,
            'company_id': company_a.id,
            'tax_group_id': tax_group_a.id,
            'country_id': self.env.ref('base.us').id,
        })
        # create a SO from company_a
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'company_id': company_a.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'product_uom_qty': 1,
                    'price_unit': 123.4,
                    'tax_id': tax_a.ids,
                }),
            ],
        })
        # edit the price unit
        so.write({
            'order_line': [
                Command.update(so.order_line[0].id, {'price_unit': 123.5}),
            ],
        })
        # call "flush_all" as it is done in "call_kw" method to test
        # the tax values that have been recomputed after it
        self.env.flush_all()
        self.assertEqual(so.amount_tax, 12.35)
        self.assertEqual(so.amount_total, 135.85)
        # set "Rounding Method" of company A to "Round Globally"
        company_a.tax_calculation_rounding_method = 'round_globally'
        # edit the price unit
        so.write({
            'order_line': [
                Command.update(so.order_line[0].id, {'price_unit': 123.6}),
            ],
        })
        self.env.flush_all()
        self.assertEqual(so.amount_tax, 12.36)
        self.assertEqual(so.amount_total, 135.96)

    def test_recompute_taxes_rounded_globally_currency_precision(self):
        '''
        Check that taxes computation are made in the currency of the company
        configured on the SO lines.
        '''
        # create a currency with no decimal
        currency_b = self.env['res.currency'].create({
            'name': 'B',
            'symbol': 'B',
            'rounding': 1.000000,
        })
        # create a company with currency_b as currency
        company_b = self.env['res.company'].create({
            'name': 'Company B',
            'tax_calculation_rounding_method': 'round_globally',
            'currency_id': currency_b.id,
        })
        # set company_b as default company of current user
        self.env.user.company_id = company_b

        pricelist_b = self.env['product.pricelist'].with_company(company_b).create({
            'name': 'pricelist b',
            'currency_id': self.env.ref('base.USD').id,
        })
        tax_group_a = self.env['account.tax.group'].create({
            'name': 'Tax Group',
            'company_id': company_b.id,
        })
        tax = self.env['account.tax'].create({
            'name': 'Tax A',
            'amount': 19,
            'company_id': company_b.id,
            'country_id': self.env.ref('base.us').id,
            'tax_group_id': tax_group_a.id,
        })
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'company_id': company_b.id,
            'pricelist_id': pricelist_b.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'product_uom_qty': 1,
                    'price_unit': 15.31,
                    'tax_id': tax.ids,
                }),
            ],
        })
        self.assertEqual(so.amount_tax, 2.91)
        self.assertEqual(so.amount_total, 18.22)
        self.assertEqual(so.order_line.price_tax, 2.91)
        self.assertEqual(so.order_line.price_total, 18.22)
