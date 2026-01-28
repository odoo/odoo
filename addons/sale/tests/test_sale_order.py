# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from unittest.mock import patch

from freezegun import freeze_time

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command
from odoo.tests import Form, HttpCase, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestSaleOrder(SaleCommon):

    # Those tests do not rely on accounting common on purpose
    #   If you need the accounting setup, use other classes (TestSaleToInvoice probably)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner1, cls.partner2 = cls.env['res.partner'].create([
            {'name': 'Partner 1'},
            {'name': 'Partner 2'},
        ])
        cls.confirmation_email_template = cls.sale_order._get_confirmation_template()
        cls.async_emails_cron = cls.env.ref('sale.send_pending_emails_cron')

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

    def test_sol_names(self):
        """Check that the SOL description gets used for the display name."""
        no_variant_attr = self.env['product.attribute'].create({
            'name': "Attribute",
            'create_variant': 'no_variant',
            'value_ids': [
                Command.create({'name': "Value 1", 'sequence': 1}),
                Command.create({'name': "Value 2", 'sequence': 2}),
            ],
        })
        no_variant_product_tmpl = self.env['product.template'].create({
            'name': "No Variant",
            'attribute_line_ids': [Command.create({
                'attribute_id': no_variant_attr.id,
                'value_ids': no_variant_attr.value_ids.ids,
            })],
        })
        no_variant_product = no_variant_product_tmpl.product_variant_id
        ptals = no_variant_product_tmpl.valid_product_template_attribute_line_ids
        ptav1 = next(iter(ptals.product_template_value_ids))
        product_with_desc = self.env['product.product'].create({
            'name': "Product with description",
            'description_sale': "Additional\ninfo.",
        })

        self.sale_order.order_line = [
            Command.create({'is_downpayment': True}),
            Command.create({'display_type': 'line_note', 'name': "Foo\nBar\nBaz"}),
            Command.create({
                'product_id': no_variant_product.id,
                'product_no_variant_attribute_value_ids': ptav1.ids,
            }),
            Command.create({'product_id': product_with_desc.id}),
        ]
        sol1, sol2, sol3, sol4, sol5, sol6 = self.sale_order.order_line
        sol1.name += "\nOK THANK YOU\nGOOD BYE"

        self.assertEqual(
            sol1.display_name,
            f"{self.sale_order.name} - OK THANK YOU ({self.partner.name})",
            "Product line with a custom description should display the first line of description",
        )
        self.assertEqual(
            sol2.display_name,
            f"{self.sale_order.name} - {sol2.product_id.display_name} ({self.partner.name})",
            "Product line without description should display the product name",
        )
        self.assertEqual(
            sol3.display_name,
            f"{self.sale_order.name} - {sol3.name} ({self.partner.name})",
            "Down payment line should display the down payment name",
        )
        self.assertEqual(
            sol4.display_name,
            f"{self.sale_order.name} - Foo ({self.partner.name})",
            "Multi-line note should display the first line only",
        )
        self.assertIn(f"{no_variant_attr.name}: {ptav1.name}", sol5.name.split('\n'))
        self.assertEqual(
            sol5.display_name,
            f"{self.sale_order.name} - {no_variant_product.name} ({self.partner.name})",
            "Lines with attribute-based descriptions should display the product name",
        )
        self.assertEqual(
            sol6.display_name,
            f"{self.sale_order.name} - {product_with_desc.display_name} ({self.partner.name})",
            "Product lines with standard sales description should display the product name",
        )

    def test_state_changes(self):
        """Test some untested state changes methods & logic."""
        self.sale_order.action_quotation_sent()

        self.assertEqual(self.sale_order.state, 'sent')
        self.assertNotIn(
            self.sale_order.partner_id, self.sale_order.message_partner_ids,
            'Customer should not be added automatically in followers')

        self.env.user.group_ids += self.env.ref('sale.group_auto_done_setting')
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
        order_line.product_uom_id = self.uom_dozen
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
            'price_include_override': 'tax_excluded',
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
                    'tax_ids': tax_a.ids,
                }),
                Command.create({
                    'product_id': self.product.id,
                    'product_uom_qty': 1,
                    'price_unit': 6.7,
                    'discount': 0,
                    'tax_ids': tax_a.ids,
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
                    'tax_ids': tax_a.ids,
                }),
                Command.create({
                    'product_id': self.product.id,
                    'product_uom_qty': 1,
                    'price_unit': 6.7,
                    'discount': 0,
                    'tax_ids': tax_a.ids,
                }),
            ],
        })
        self.assertEqual(sale_order.amount_total, 15.41, "")

    def test_order_auto_lock_with_public_user(self):
        public_user = self.env.ref('base.public_user')
        self.sale_order.create_uid.group_ids += self.env.ref('sale.group_auto_done_setting')
        self.sale_order.with_user(public_user.id).sudo().action_confirm()

        self.assertFalse(public_user.has_group('sale.group_auto_done_setting'))
        self.assertTrue(self.sale_order.locked)

    def test_order_status_email_is_sent_synchronously_if_not_configured(self):
        """ Test that the order status email is sent synchronously when nothing is configured. """
        self.env['ir.config_parameter'].set_param('sale.async_emails', 'False')

        self.sale_order._send_order_notification_mail(self.confirmation_email_template)
        self.assertFalse(
            self.env['ir.cron.trigger'].search_count([('cron_id', '=', self.async_emails_cron.id)]),
            msg="The email should be sent synchronously when the system parameter is not set.",
        )

    def test_order_status_email_is_sent_asynchronously_if_configured(self):
        """ Test that the order status email is sent asynchronously when configured. """
        self.env['ir.config_parameter'].set_param('sale.async_emails', 'True')

        self.sale_order._send_order_notification_mail(self.confirmation_email_template)
        self.assertTrue(
            self.sale_order.pending_email_template_id,
            msg="The email template should be saved on the sales order.",
        )
        self.assertTrue(
            self.env['ir.cron.trigger'].search_count([('cron_id', '=', self.async_emails_cron.id)]),
            msg="The asynchronous email sending cron should be triggered.",
        )

    def test_async_emails_cron_does_not_trigger_itself(self):
        """ Test that the asynchronous email sending cron does not loop indefinitely. """
        self.env['ir.config_parameter'].set_param('sale.async_emails', 'True')
        self.sale_order.pending_email_template_id = self.confirmation_email_template

        with self.enter_registry_test_mode():
            self.env.ref('sale.send_pending_emails_cron').method_direct_trigger()
        self.assertFalse(
            self.sale_order.pending_email_template_id,
            msg="The email template should be removed from the sales order.",
        )
        self.assertFalse(
            self.env['ir.cron.trigger'].search_count([('cron_id', '=', self.async_emails_cron.id)]),
            msg="The email should be sent synchronously when requested by the cron.",
        )

    def test_scheduled_mark_so_as_sent(self):
        """Check that a order gets marked as sent after a scheduled message was sent."""
        order = self.sale_order
        composer = self.env['mail.compose.message'].with_context(
            active_id=order.id,
            active_ids=order.ids,
            active_model=order._name,
            mark_so_as_sent=True,
        ).new({
            'body': '<h1>Your Sales Order</h1>',
            'scheduled_date': fields.Datetime.now() + timedelta(days=1),
        })
        composer.action_schedule_message()

        scheduled_message = self.env['mail.scheduled.message'].search([
            ('model', '=', order._name),
            ('res_id', '=', order.id),
        ], limit=1)
        self.assertEqual(order.state, 'draft')
        scheduled_message.post_message()
        self.assertEqual(order.state, 'sent')

    def test_so_discount_is_not_reset(self):
        """ Discounts should not be recomputed on order confirmation """
        with patch(
            'odoo.addons.sale.models.sale_order_line.SaleOrderLine'
            '._compute_discount'
        ) as patched:
            self.sale_order.action_confirm()
            self.sale_order.order_line.flush_recordset(['discount'])
            patched.assert_not_called()

    def test_so_company_empty(self):
        """Check emptying company on SO form"""
        company_2 = self.env['res.company'].create({
            'name': 'Company 2'
        })
        self.env = self.env(context=dict(self.env.context, allowed_company_ids=[self.env.company.id, company_2.id]))
        so_form = Form(self.env['sale.order'])
        with self.assertRaises(ValidationError):
            so_form.company_id = self.env['res.company']

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

    def test_so_with_fixed_discount_zero_amount(self):
        """ Applying a fixed discount of 0.0 should have no effect on the order total. """
        initial_total = self.sale_order.amount_total
        self.env['sale.order.discount'].create({
            'sale_order_id': self.sale_order.id,
            'discount_amount': 0.0,
            'discount_type': 'amount',
        }).action_apply_discount()
        self.assertEqual(self.sale_order.amount_total, initial_total)

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
            {'product_id': product_all_taxes.id, 'tax_ids': tax_xx.ids},
            {'product_id': product_no_xx_tax.id, 'tax_ids': tax_x.ids},
            {'product_id': product_no_branch_tax.id, 'tax_ids': (tax_a + tax_b).ids},
            {'product_id': product_no_tax.id, 'tax_ids': []},
        ])

    def test_price_recomputation_on_readonly_unit_price(self):
        """Make sure that price computation works fine when unit price is readonly.

        Since the client doesn't send readonly fields, flagging the field as readonly
        will result in the `price_unit` being absent from the values, but not the
        `technical_price_unit` field, which would disable the price computation.

        This test makes sure that the `technical_price_unit` is correctly discarded
        if not provided in the same request as the `price_unit`
        """
        self.pricelist.item_ids = [
            Command.create({
                'product_id': self.product.id,
                'fixed_price': 22.0,
                'min_quantity': 3.0,
            })
        ]

        # Order update
        product_sol = self.sale_order.order_line[0]
        self.assertNotEqual(product_sol.price_unit, 22)
        self.sale_order.write({
            'order_line': [Command.update(
                product_sol.id,
                {'product_uom_qty': 4.0, 'technical_price_unit': 22.0}
            )],
        })
        self.assertEqual(product_sol.price_unit, 22.0)

        # Order creation
        new_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'product_uom_qty': 5.0,
                    'technical_price_unit': 22.0,
                }),
            ],
        })
        self.assertEqual(new_order.order_line.price_unit, 22.0)

    def test_sale_warnings(self):
        """Test warnings when partner/products with sale warnings are used."""
        partner_with_warning = self.env['res.partner'].create({
            'name': 'Test Partner', 'sale_warn_msg': 'Highly infectious disease'})
        child_partner = self.env['res.partner'].create({
            'type': 'invoice', 'parent_id': partner_with_warning.id, 'sale_warn_msg': 'Slightly infectious disease'})
        sale_order = self.env['sale.order'].create({'partner_id': partner_with_warning.id})
        sale_order2 = self.env['sale.order'].create({'partner_id': child_partner.id})

        product_with_warning1 = self.env['product.product'].create({
            'name': 'Test Product 1', 'sale_line_warn_msg': 'Highly corrosive'})
        product_with_warning2 = self.env['product.product'].create({
            'name': 'Test Product 2', 'sale_line_warn_msg': 'Toxic pollutant'})
        self.env['sale.order.line'].create([
            {
                'order_id': sale_order.id,
                'product_id': product_with_warning1.id,
            },
            {
                'order_id': sale_order.id,
                'product_id': product_with_warning2.id,
            },
            # Warnings for duplicate products should not appear.
            {
                'order_id': sale_order.id,
                'product_id': product_with_warning1.id,
            },
            {
                'order_id': sale_order2.id,
                'product_id': product_with_warning1.id,
            },
            {
                'order_id': sale_order2.id,
                'product_id': product_with_warning2.id,
            },
            # Warnings for duplicate products should not appear.
            {
                'order_id': sale_order2.id,
                'product_id': product_with_warning1.id,
            },
        ])

        group_warning_sale = self.env.ref('sale.group_warning_sale')
        self.group_user.implied_ids = [Command.link(group_warning_sale.id)]
        sale_order2.action_confirm()
        sale_order2._create_invoices()
        invoice = Form(sale_order2.invoice_ids[0])

        expected_warnings = ('Test Partner - Highly infectious disease',
                             'Test Product 1 - Highly corrosive',
                             'Test Product 2 - Toxic pollutant')
        expected_warnings_for_sale_order2 = ('Test Partner, Invoice - Slightly infectious disease',
                                             'Test Partner - Highly infectious disease',
                                             'Test Product 1 - Highly corrosive',
                                             'Test Product 2 - Toxic pollutant')
        self.assertEqual(sale_order.sale_warning_text, '\n'.join(expected_warnings))
        self.assertEqual(sale_order2.sale_warning_text, '\n'.join(expected_warnings_for_sale_order2))
        self.assertEqual(invoice.sale_warning_text, '\n'.join(expected_warnings_for_sale_order2))

        # without warning group, there should be no warning
        self.group_user.implied_ids = [Command.unlink(group_warning_sale.id)]
        self.assertEqual(sale_order.sale_warning_text, '')
        self.assertEqual(sale_order2.sale_warning_text, '')
        invoice = Form(sale_order2.invoice_ids[0])
        self.assertEqual(invoice.sale_warning_text, '')

    def test_sale_order_email_subtitle(self):
        """Test email notification subtitle for Sale Order with and without partner name."""
        partner = self.env['res.partner'].create({'type': 'invoice', 'parent_id': self.partner.id})
        self.sale_order.partner_id = partner
        context = self.sale_order._notify_by_email_prepare_rendering_context(message=self.env['mail.message'])
        self.assertEqual(context['subtitles'][0], self.sale_order.name)

        self.sale_order.partner_id.name = "Test Partner"
        context = self.sale_order._notify_by_email_prepare_rendering_context(message=self.env['mail.message'])
        self.assertEqual(context['subtitles'][0], f"{self.sale_order.name} - Test Partner")

    def test_sale_order_unit_price_recompute_on_product_change(self):
        """Ensure price_unit is correctly recomputed when the product is
           changed after manually changing the price.
        """
        product2 = self.env['product.product'].create({
            'name': "Test Product2",
            'list_price': 0.0,
        })
        sol = self.sale_order.order_line[0]
        # Manually change the product & price on the SO line
        with Form(sol) as sol_form:
            sol_form.product_id = product2
            sol_form.price_unit = 100
        # Expected price_subtotal = custom unit price * quantity
        self.assertAlmostEqual(
            sol.price_subtotal, 100 * sol.product_uom_qty,
            msg="price_total should be equal to expected_total",
        )
        # Unit price should reset after changing the product
        with Form(sol) as sol_form:
            sol_form.product_id = self.product
        # Expected price_subtotal = list price * quantity
        self.assertAlmostEqual(
            sol.price_subtotal, self.product.list_price * sol.product_uom_qty,
            msg="price_total should be equal to expected_total",
        )


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
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': partner.id,
        })
        self.assertEqual(sale_order.team_id.id, self.sale_team.id, 'Should assign to team of sales person')

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
        self.env.user.group_ids += self.env.ref('analytic.group_analytic_accounting')

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
            'tax_ids': tax_a,
        })

        with self.assertRaises(UserError):
            sol.tax_ids = tax_b

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
            'tax_ids': tax_b1,
        })

        # should not raise anything
        sol_b1.tax_ids = tax_b0
        sol_b1.tax_ids = tax_b1
        # should raise (b2 is not on the same branch lineage as b1)
        with self.assertRaises(UserError):
            sol_b1.tax_ids = tax_b2

    def test_downpayment_amount_constraints(self):
        """Down payment amounts should be in the interval ]0, 1]."""

        self.sale_order.require_payment = True
        with self.assertRaises(ValidationError):
            self.sale_order.prepayment_percent = -1
        with self.assertRaises(ValidationError):
            self.sale_order.prepayment_percent = 1.01

    def test_qty_delivered_on_creation(self):
        """Checks that the qty delivered of sol is automatically set to 0.0 when an so is created"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                })],
        })
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
            'price_include_override': 'tax_included',
        })

        mapping_a = self.env['account.fiscal.position'].create({
            'name': 'Special Tax Reduction',
        })
        mapping_b = self.env['account.fiscal.position'].create({
            'name': 'Special Tax Reduction',
        })
        mapped_tax_a = self.env['account.tax'].create({
            'name': "tax_a",
            'amount_type': 'percent',
            'amount': 12.5,
            'include_base_amount': True,
            'price_include_override': 'tax_included',
            'fiscal_position_ids': mapping_a,
            'original_tax_ids': special_tax,
        })

        mapped_tax_b = self.env['account.tax'].create({
            'name': "tax_b",
            'amount_type': 'percent',
            'amount': 5.0,
            'include_base_amount': True,
            'price_include_override': 'tax_included',
            'fiscal_position_ids': mapping_b,
            'original_tax_ids': special_tax,
        })

        sales_tax = self.env['account.tax'].create({
            'name': "VAT 20%",
            'amount_type': 'percent',
            'amount': 20.0,
            'price_include_override': 'tax_included',
        })


        # taxes and standard price need to be set on the product, as they will be
        # recomputed when changing the fiscal position.
        self.product.write({
            'lst_price': 300,
            'taxes_id': [Command.set((special_tax + sales_tax).ids)],
        })

        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
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


@tagged('post_install', '-at_install')
class TestSaleMailComposerUI(MailCommon, HttpCase):
    @classmethod
    def setUpClass(cls):
        super(TestSaleMailComposerUI, cls).setUpClass()
        cls.env['mail.alias.domain'].create({'name': 'example.com'})
        cls.partner = cls.env['res.partner'].create({
            'name': 'test customer',
            'email': 'dummy@example.com'
        })
        cls.quotation = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
        })

    def test_mail_attachment_removal_tour(self):
        url = f"/odoo/sales/{self.quotation.id}"
        with self.mock_mail_app():
            self.start_tour(
                url,
                "mail_attachment_removal_tour",
                login="admin",
            )
