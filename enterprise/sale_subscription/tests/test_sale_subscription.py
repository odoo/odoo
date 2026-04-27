import datetime
from dateutil.relativedelta import relativedelta
from markupsafe import Markup
from unittest.mock import patch

from odoo.addons.account_accountant.tests.test_signature import TestInvoiceSignature
from odoo.addons.mail.tests.common import MockEmail
from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon
from odoo.addons.sale_subscription.models.sale_order import SaleOrder
from odoo.tests import Form, tagged, freeze_time
from odoo.tools import mute_logger
from odoo import fields, Command
from odoo.exceptions import AccessError, ValidationError, UserError


@tagged('post_install', '-at_install')
class TestSubscription(TestSubscriptionCommon, MockEmail):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_a.recurring_invoice = False

    def flush_tracking(self):
        """ Force the creation of tracking values. """
        self.env.flush_all()
        self.cr.flush()

    @classmethod
    def default_env_context(cls):
        return {}

    def setUp(self):
        super(TestSubscription, self).setUp()
        self.other_currency = self.setup_other_currency('CAD')
        self.env.ref('base.group_user').write({"implied_ids": [(4, self.env.ref('sale_management.group_sale_order_template').id)]})
        self.flush_tracking()

        self.post_process_patcher = patch(
            'odoo.addons.account_payment.models.payment_transaction.PaymentTransaction._post_process',
        )
        self.startPatcher(self.post_process_patcher)

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_automatic(self):
        self.assertTrue(True)
        sub = self.subscription
        context_no_mail = {'no_reset_password': True, 'mail_create_nosubscribe': True, 'mail_create_nolog': True, }
        sub_product_tmpl = self.env['product.template'].with_context(context_no_mail).create({
            'name': 'Subscription Product',
            'type': 'service',
            'recurring_invoice': True,
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'list_price': 42
        })
        product = sub_product_tmpl.product_variant_id
        template = self.env['sale.order.template'].create({
            'name': 'Subscription template without discount',
            'duration_unit': 'year',
            'is_unlimited': False,
            'duration_value': 2,
            'plan_id': self.plan_month.id,
            'sale_order_template_line_ids': [Command.create({
                'name': "monthly",
                'product_id': product.id,
                'product_uom_id': product.uom_id.id
            }),
                Command.create({
                    'name': "yearly",
                    'product_id': product.id,
                    'product_uom_id': product.uom_id.id,
                })
            ]

        })
        self.plan_month.auto_close_limit = 3
        self.company = self.env.company

        self.provider = self.env['payment.provider'].create(
            {'name': 'The Wire',
             'company_id': self.company.id,
             'state': 'test',
             'redirect_form_view_id': self.env['ir.ui.view'].search([('type', '=', 'qweb')], limit=1).id})

        sub.sale_order_template_id = template.id
        sub._onchange_sale_order_template_id()
        with freeze_time("2021-01-03"):
            sub.write({'start_date': False, 'next_invoice_date': False})
            sub.action_confirm()
            self.assertEqual(sub.invoice_count, 0)
            self.assertEqual(datetime.date(2021, 1, 3), sub.start_date, 'start date should be reset at confirmation')
            self.assertEqual(datetime.date(2021, 1, 3), sub.next_invoice_date, 'next invoice date should be updated')
            self.env['sale.order']._cron_recurring_create_invoice()
            self.assertEqual(datetime.date(2021, 2, 3), sub.next_invoice_date, 'next invoice date should be updated')
            inv = sub.invoice_ids.sorted('date')[-1]
            inv_line = inv.invoice_line_ids[0].sorted('id')[0]
            invoice_periods = inv_line.name.split('\n')[2]
            self.assertEqual(invoice_periods, "1 Months 01/03/2021 to 02/02/2021")
            self.assertEqual(inv_line.date, datetime.date(2021, 1, 3))

        with freeze_time("2021-02-03"):
            self.assertEqual(sub.invoice_count, 1)
            self.env['sale.order']._cron_recurring_create_invoice()
            self.assertEqual(sub.invoice_count, 2)
            self.assertEqual(datetime.date(2021, 1, 3), sub.start_date, 'start date should not changed')
            self.assertEqual(datetime.date(2021, 3, 3), sub.next_invoice_date, 'next invoice date should be in 1 month')
            inv = sub.invoice_ids.sorted('date')[-1]
            invoice_periods = inv.invoice_line_ids[1].name.split('\n')[2]
            self.assertEqual(invoice_periods, "1 Months 02/03/2021 to 03/02/2021")
            self.assertEqual(inv.invoice_line_ids[1].date, datetime.date(2021, 2, 3))

        with freeze_time("2021-03-03"):
            self.env['sale.order']._cron_recurring_create_invoice()
            self.assertEqual(datetime.date(2021, 4, 3), sub.next_invoice_date, 'next invoice date should be in 1 month')
            inv = sub.invoice_ids.sorted('date')[-1]
            invoice_periods = inv.invoice_line_ids[0].name.split('\n')[2]
            self.assertEqual(invoice_periods, "1 Months 03/03/2021 to 04/02/2021")
            self.assertEqual(inv.invoice_line_ids[0].date, datetime.date(2021, 3, 3))

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_template(self):
        """ Test behaviour of on_change_template """
        Subscription = self.env['sale.order']
        self.assertEqual(self.subscription.note, Markup('<p>original subscription description</p>'), "Original subscription note")
        # on_change_template on cached record (NOT present in the db)
        temp = Subscription.new({'name': 'CachedSubscription',
                                 'partner_id': self.user_portal.partner_id.id})
        temp.update({'sale_order_template_id': self.subscription_tmpl.id})
        temp._onchange_sale_order_template_id()
        self.assertEqual(temp.note, Markup('<p>This is the template description</p>'), 'Override the subscription note')

    def test_template_without_selected_partner(self):
        """ Create a subscription by choosing a template before the customer """
        with Form(self.env['sale.order']) as subscription:
            subscription.sale_order_template_id = self.subscription_tmpl
            subscription.partner_id = self.partner # mandatory to have no error

    def test_invoicing_with_section(self):
        """ Test invoicing when order has section/note."""
        context_no_mail = {'no_reset_password': True, 'mail_create_nosubscribe': True, 'mail_create_nolog': True, }

        # create specific test products
        sub_product1_tmpl = self.env['product.template'].with_context(context_no_mail).create({
            'name': 'Subscription #A',
            'type': 'service',
            'recurring_invoice': True,
            'uom_id': self.env.ref('uom.product_uom_unit').id,
        })
        sub_product1 = sub_product1_tmpl.product_variant_id
        sub_product2_tmpl = self.env['product.template'].with_context(context_no_mail).create({
            'name': 'Subscription #B',
            'type': 'service',
            'recurring_invoice': True,
            'uom_id': self.env.ref('uom.product_uom_unit').id,
        })
        sub_product2 = sub_product2_tmpl.product_variant_id
        sub_product_onetime_discount_tmpl = self.env['product.template'].with_context(context_no_mail).create({
            'name': 'Initial discount',
            'type': 'service',
            'recurring_invoice': False,
            'uom_id': self.env.ref('uom.product_uom_unit').id,
        })
        sub_product_onetime_discount = sub_product_onetime_discount_tmpl.product_variant_id

        with freeze_time("2021-01-03"):
            sub = self.env["sale.order"].with_context(**context_no_mail).create({
                'name': 'TestSubscription',
                'is_subscription': True,
                'plan_id': self.plan_month.id,
                'note': "original subscription description",
                'partner_id': self.user_portal.partner_id.id,
                'pricelist_id': self.company_data['default_pricelist'].id,
                'sale_order_template_id': self.subscription_tmpl.id,
            })
            sub._onchange_sale_order_template_id()
            sub.write({
                'start_date': False,
                'end_date': False,
                'next_invoice_date': False,
            })
            sub.order_line = [
                Command.clear(),
                Command.create({
                    'display_type': 'line_section',
                    'name': 'Products',
                }),
                Command.create({
                    'product_id': sub_product1.id,
                    'name': "Subscription #A",
                    'price_unit': 42,
                    'product_uom_qty': 2,
                }),
                Command.create({
                    'product_id': sub_product2.id,
                    'name': "Subscription #B",
                    'price_unit': 42,
                    'product_uom_qty': 2,
                }),
                Command.create({
                    'product_id': sub_product_onetime_discount.id,
                    'name': 'Initial discount New subscription discount (one-time)',
                    'price_unit': -10.0,
                    'product_uom_qty': 2,
                }),
                Command.create({
                    'display_type': 'line_section',
                    'name': 'Information',
                }),
                Command.create({
                    'display_type': 'line_note',
                    'name': '...',
                }),
            ]
            sub.action_confirm()
            sub._create_invoices()

        # first invoice, it should include one-time discount
        self.assertEqual(len(sub.invoice_ids), 1)
        sub.invoice_ids._post()
        invoice = sub.invoice_ids[-1]
        self.assertEqual(invoice.amount_untaxed, 148.0)
        self.assertEqual(len(invoice.invoice_line_ids), 6)
        self.assertRecordValues(invoice.invoice_line_ids, [
            {'display_type': 'line_section', 'name': 'Products', 'product_id': False},
            {
                'display_type': 'product', 'product_id': sub_product1.id,
                'name': 'Subscription #A\n1 Months 01/03/2021 to 02/02/2021',
            },
            {
                'display_type': 'product', 'product_id': sub_product2.id,
                'name': 'Subscription #B\n1 Months 01/03/2021 to 02/02/2021',
            },
            {
                'display_type': 'product', 'product_id': sub_product_onetime_discount.id,
                'name': 'Initial discount New subscription discount (one-time)',
            },
            {'display_type': 'line_section', 'name': 'Information', 'product_id': False},
            {'display_type': 'line_note', 'name': '...', 'product_id': False},
        ])

        with freeze_time("2021-02-03"):
            invoice = sub._create_invoices()
            invoice._post()

        # second invoice, should NOT include one-time discount
        self.assertEqual(len(sub.invoice_ids), 2)
        self.assertEqual(invoice.amount_untaxed, 168.0)
        self.assertEqual(len(invoice.invoice_line_ids), 5)
        self.assertRecordValues(invoice.invoice_line_ids, [
            {'display_type': 'line_section', 'name': 'Products', 'product_id': False},
            {
             'display_type': 'product', 'product_id': sub_product1.id,
             'name': 'Subscription #A\n1 Months 02/03/2021 to 03/02/2021',
            },
            {
             'display_type': 'product', 'product_id': sub_product2.id,
             'name': 'Subscription #B\n1 Months 02/03/2021 to 03/02/2021',
            },
            {'display_type': 'line_section', 'name': 'Information', 'product_id': False},
            {'display_type': 'line_note', 'name': '...', 'product_id': False},
        ])

    def test_add_aml_to_invoice(self):
        """ Test that it is possible to manually add a line with a start and end
        date to an invoice generated from a subscription sale order.
        """
        sub_product1, sub_product2 = self.env['product.product'].create([
            {
                'name': 'SubA',
                'type': 'service',
                'recurring_invoice': True,
                'invoice_policy': 'order',
            },
            {
                'name': 'SubB',
                'type': 'service',
                'recurring_invoice': True,
            }
        ])

        sub = self.env['sale.order'].create({
            'name': 'TestSubscription',
            'is_subscription': True,
            'plan_id': self.plan_month.id,
            'partner_id': self.user_portal.partner_id.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'order_line': [(0, 0, {'product_id': sub_product1.id})],
        })

        sub.action_confirm()
        invoice = sub._create_invoices()
        invoice.write({
            'line_ids': [(0, 0, {
                'product_id': sub_product2.id,
                'deferred_start_date': '2015-03-14',
                'deferred_end_date': '2030-06-28',
            })],
        })
        invoice._post()  # should not throw an error
        self.assertEqual(invoice.line_ids.product_id, sub_product1 | sub_product2)

    def test_invoicing_access_rights(self):
        """Ensure a salesman can get amount invoiced for subscriptions with others' invoices."""
        sales_user = self.company_data['default_user_salesman']
        self.subscription.write({
            'user_id': sales_user.id,
            'order_line': [Command.create({
                'name': "Non-recurring product",
                'product_id': self.product_a.id,
                'tax_id': False,
            })],
        })
        self.subscription.action_confirm()
        self.assertAlmostEqual(
            self.subscription.with_user(sales_user).amount_to_invoice,
            sum(self.subscription.order_line.mapped('price_total')),
            msg="All lines should still need to be invoiced",
        )

        # assign a different user to the invoice
        invoice = self.subscription._create_recurring_invoice()
        invoice.user_id = self.env.ref('base.user_admin')

        # ensure salesman doesn't have access to just any invoice
        invoice.invalidate_recordset(['name'])
        with self.assertRaises(AccessError):
            invoice.with_user(sales_user).user_id = sales_user

        self.assertAlmostEqual(
            self.subscription.with_user(sales_user).amount_invoiced,
            self.product_a.list_price,
            msg="We should get the amount invoiced for non-recurring products",
        )

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_unlimited_sale_order(self):
        """ Test behaviour of on_change_template """
        with freeze_time("2021-01-03"):
            sub = self.subscription
            sub.order_line = [Command.clear()]
            context_no_mail = {'no_reset_password': True, 'mail_create_nosubscribe': True, 'mail_create_nolog': True, }
            sub_product_tmpl = self.env['product.template'].with_context(context_no_mail).create({
                'name': 'Subscription Product',
                'type': 'service',
                'recurring_invoice': True,
                'uom_id': self.env.ref('uom.product_uom_unit').id,
            })
            product = sub_product_tmpl.product_variant_id
            sub.order_line = [Command.create({'product_id': product.id,
                                              'name': "coucou",
                                              'price_unit': 42,
                                              'product_uom_qty': 2,
                                              })]
            sub.write({'start_date': False, 'next_invoice_date': False})
            sub.action_confirm()
            self.assertFalse(sub.last_invoice_date)
            self.assertEqual("2021-01-03", sub.start_date.strftime("%Y-%m-%d"))
            self.assertEqual("2021-01-03", sub.next_invoice_date.strftime("%Y-%m-%d"))

            sub._create_recurring_invoice()
            # Next invoice date should not be bumped up because it is the first period
            self.assertEqual("2021-02-03", sub.next_invoice_date.strftime("%Y-%m-%d"))

            invoice_periods = sub.invoice_ids.invoice_line_ids.name.split('\n')[2]
            self.assertEqual(invoice_periods, "1 Months 01/03/2021 to 02/02/2021")
            self.assertEqual(sub.invoice_ids.invoice_line_ids.date, datetime.date(2021, 1, 3))
        with freeze_time("2021-02-03"):
            # February
            sub._create_recurring_invoice()
            self.assertEqual("2021-02-03", sub.last_invoice_date.strftime("%Y-%m-%d"))
            self.assertEqual("2021-03-03", sub.next_invoice_date.strftime("%Y-%m-%d"))
            inv = sub.invoice_ids.sorted('date')[-1]
            invoice_periods = inv.invoice_line_ids.name.split('\n')[2]
            self.assertEqual(invoice_periods, "1 Months 02/03/2021 to 03/02/2021")
            self.assertEqual(inv.invoice_line_ids.date, datetime.date(2021, 2, 3))
        with freeze_time("2021-03-03"):
            # March
            sub._create_recurring_invoice()
            self.assertEqual("2021-03-03", sub.last_invoice_date.strftime("%Y-%m-%d"))
            self.assertEqual("2021-04-03", sub.next_invoice_date.strftime("%Y-%m-%d"))
            inv = sub.invoice_ids.sorted('date')[-1]
            invoice_periods = inv.invoice_line_ids.name.split('\n')[2]
            self.assertEqual(invoice_periods, "1 Months 03/03/2021 to 04/02/2021")
            self.assertEqual(inv.invoice_line_ids.date, datetime.date(2021, 3, 3))

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_limited_service_sale_order(self):
        """ Test behaviour of on_change_template """
        with freeze_time("2021-01-03"):
            sub = self.subscription
            sub.order_line = [Command.clear()]
            context_no_mail = {'no_reset_password': True, 'mail_create_nosubscribe': True, 'mail_create_nolog': True}
            sub_product_tmpl = self.env['product.template'].with_context(context_no_mail).create({
                'name': 'Subscription Product',
                'type': 'service',
                'recurring_invoice': True,
                'uom_id': self.env.ref('uom.product_uom_unit').id,
            })
            product = sub_product_tmpl.product_variant_id
            sub.order_line = [Command.create({'product_id': product.id,
                                              'name': "coucou",
                                              'price_unit': 42,
                                              'product_uom_qty': 2,
                                              })]
            sub.write({'start_date': False, 'next_invoice_date': False, 'end_date': '2021-03-18'})
            sub.action_confirm()
            inv = sub._create_recurring_invoice()
            self.assertAlmostEqual(inv.amount_untaxed, 84)

        with freeze_time("2021-02-03"):
            # February
            inv = sub._create_recurring_invoice()
            self.assertAlmostEqual(inv.amount_untaxed, 84)

        with freeze_time("2021-03-03"):
            # March
            inv = sub._create_recurring_invoice()
            self.assertAlmostEqual(inv.amount_untaxed, 84, 1,  msg="Last period is full too 01 to 01 even if the end_date occurs in the middle of the period")

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_invoice_on_period_start_service_sale_order(self):
        """ Test behaviour of on_change_template """
        with freeze_time("2021-01-15"):
            sub = self.subscription
            sub.order_line = [Command.clear()]
            context_no_mail = {'no_reset_password': True, 'mail_create_nosubscribe': True, 'mail_create_nolog': True}
            sub_product_tmpl = self.env['product.template'].with_context(context_no_mail).create({
                'name': 'Subscription Product',
                'type': 'service',
                'recurring_invoice': True,
                'uom_id': self.env.ref('uom.product_uom_unit').id,
            })
            product = sub_product_tmpl.product_variant_id
            sub.order_line = [Command.create({'product_id': product.id,
                                              'name': "coucou",
                                              'price_unit': 42,
                                              'product_uom_qty': 2,
                                              })]
            sub.write({'start_date': False, 'next_invoice_date': False, 'end_date': '2021-03-18'})
            sub.plan_id.billing_first_day = True
            sub.action_confirm()
            inv = sub._create_recurring_invoice()
            self.assertAlmostEqual(inv.amount_untaxed, 84 * 17 / 31, 1, msg="15 to 31 is 17 days (15 and 31 included)")

        with freeze_time("2021-02-01"):
            # February
            inv = sub._create_recurring_invoice()
            self.assertAlmostEqual(inv.amount_untaxed, 84)

        with freeze_time("2021-03-01"):
            # March
            inv = sub._create_recurring_invoice()
            self.assertAlmostEqual(inv.amount_untaxed, 84, 1, msg="Last period is full too 01 to 01 even if the end_date occurs in the middle of the period")

    @mute_logger('odoo.models.unlink')
    def test_renewal(self):
        """ Test subscription renewal """
        with freeze_time("2021-11-18"):
            # We reset the renew alert to make sure it will run with freezetime
            self.subscription.write({
                'start_date': False,
                'next_invoice_date': False,
                'partner_invoice_id': self.partner_a_invoice.id,
                'partner_shipping_id': self.partner_a_shipping.id,
                'internal_note': 'internal note',
                'tag_ids': [Command.create({'name': 'Subscription Tag'})]
            })            # add an so line with a different uom
            uom_dozen = self.env.ref('uom.product_uom_dozen').id
            self.subscription_tmpl.duration_value = 2 # end after 2 months to adapt to the following line
            self.subscription_tmpl.duration_unit = 'month'
            self.env['sale.order.line'].create({'name': self.product.name,
                                                'order_id': self.subscription.id,
                                                'product_id': self.product3.id,
                                                'product_uom_qty': 4,
                                                'product_uom': uom_dozen,
                                                'price_unit': 42})

            self.subscription.message_subscribe([self.env.user.partner_id.id, self.partner_a.id])
            self.subscription.action_confirm()
            self.subscription._create_recurring_invoice()
            self.assertEqual(self.subscription.end_date, datetime.date(2022, 1, 17), 'The end date of the subscription should be updated according to the template')
            self.assertEqual(self.subscription.next_invoice_date, datetime.date(2021, 12, 18))
            self.env['account.payment.register'] \
                .with_context(active_model='account.move', active_ids=self.subscription.invoice_ids.ids) \
                .create({
                'currency_id': self.subscription.currency_id.id,
                'amount': self.subscription.amount_total,
            })._create_payments()
            self.assertEqual(self.subscription.invoice_count, 1)

        self.assertTrue(self.subscription.invoice_ids.payment_state in ['in_payment', 'paid'], "the invoice is considered paid, depending on the settings.")

        with freeze_time("2021-12-18"):
            action = self.subscription.prepare_renewal_order()
            renewal_so = self.env['sale.order'].browse(action['res_id'])
            self.assertEqual(renewal_so.partner_invoice_id, self.partner_a_invoice)
            self.assertEqual(renewal_so.partner_shipping_id, self.partner_a_shipping)
            # check produt_uom_qty
            self.assertEqual(renewal_so.sale_order_template_id.id, self.subscription.sale_order_template_id.id,
                             'sale_subscription: renewal so should have the same template')

            renewal_start_date = renewal_so.start_date
            with self.assertRaises(ValidationError):
                # try to start the renewal before the parent next invoice date
                renewal_so.start_date = self.subscription.next_invoice_date - relativedelta(days=1)
                renewal_so.action_confirm()
            renewal_so.start_date = renewal_start_date
            renewal_so.action_confirm()

            self.assertEqual(renewal_so.internal_note_display, Markup('<p>internal note</p>'), 'Internal Note should redirect to the parent')
            self.assertEqual(self.subscription.recurring_monthly, 189, 'Should be closed but with an MRR')
            self.assertEqual(renewal_so.subscription_state, '3_progress', 'so should now be in progress')
            self.assertEqual(self.subscription.subscription_state, '5_renewed')
            self.assertEqual(renewal_so.date_order.date(), self.subscription.end_date, 'renewal start date should depends on the parent end date')
            self.assertEqual(renewal_so.start_date, self.subscription.end_date, 'The renewal subscription start date and the renewed end_date should be aligned')
            self.assertEqual(renewal_so.message_follower_ids.mapped('partner_id'), self.subscription.message_follower_ids.mapped('partner_id'), 'The followers from the subscription should also follow the renewal')
            self.assertEqual(renewal_so.tag_ids, self.subscription.tag_ids, 'The tags from the subscription should have been copied to the renewal')

            self.assertEqual(renewal_so.plan_id, self.plan_month, 'the plan should be propagated')
            self.assertEqual(renewal_so.next_invoice_date, datetime.date(2021, 12, 18))
            self.assertEqual(renewal_so.start_date, datetime.date(2021, 12, 18))
            self.assertTrue(renewal_so.is_subscription)
            renewal_so._create_recurring_invoice()

        with freeze_time("2024-11-17"):
            invoice = self.subscription._create_recurring_invoice()
            self.assertFalse(invoice, "Locked contract should not generate invoices")
            renewal_so.internal_note_display = 'new internal note'
            self.assertEqual(renewal_so.internal_note_display, Markup('<p>new internal note</p>'), 'Internal Note should be updated')
            self.assertEqual(self.subscription.internal_note_display, Markup('<p>new internal note</p>'), 'Internal Note should be updated')
        with freeze_time("2024-11-19"):
            self.subscription._create_recurring_invoice() # it will close self.subscription
            renew_close_reason_id = self.env.ref('sale_subscription.close_reason_renew').id
            self.assertEqual(self.subscription.subscription_state, '5_renewed')
            self.assertEqual(self.subscription.close_reason_id.id, renew_close_reason_id)
            (self.subscription | renewal_so).invalidate_recordset(['invoice_ids', 'invoice_count'])
            self.assertEqual(self.subscription.invoice_count, 2)
            self.assertEqual(renewal_so.invoice_count, 2)

    def test_upsell_no_start_date(self):
        self.sub_product_tmpl.product_subscription_pricing_ids = [(5, 0, 0)]
        self.subscription_tmpl.sale_order_template_option_ids = [Command.create({
            'name': "Option 1",
            'product_id': self.product5.id,
            'quantity': 1,
            'uom_id': self.product5.uom_id.id,
        })]
        self.subscription.write({
                'partner_id': self.partner.id,
                'plan_id': self.plan_month.id,
                'order_line': [Command.create({'product_id': self.product.id,
                                               'name': "Monthly cheap",
                                               'price_unit': 42,
                                               'product_uom_qty': 2,
                                               }),
                               Command.create({'product_id': self.product2.id,
                                               'name': "Monthly expensive",
                                               'price_unit': 420,
                                               'product_uom_qty': 3,
                                               }),
                               ]
            })
        self.subscription.action_confirm()
        self.env['sale.order']._cron_recurring_create_invoice()
        self.subscription.invoice_ids.filtered(lambda am: am.state == 'draft')._post()
        action = self.subscription.prepare_upsell_order()
        upsell_so = self.env['sale.order'].browse(action['res_id'])
        upsell_so.order_line.filtered(lambda l: not l.display_type).product_uom_qty = 6
        upsell_so.start_date = False
        upsell_so.action_confirm()
        upsell_so._create_invoices()
        self.assertEqual(self.subscription.order_line.sorted('id').mapped('product_uom_qty'), [7.0, 7.0, 8.0, 9.0])

    def test_upsell_via_so(self):
        # Test the upsell flow using an intermediary upsell quote.
        self.sub_product_tmpl.product_subscription_pricing_ids = [(5, 0, 0)]
        self.subscription_tmpl.sale_order_template_option_ids = [Command.create({
            'name': "Option 1",
            'product_id': self.product5.id,
            'quantity': 1,
            'uom_id': self.product5.uom_id.id,
        })]
        self.product_tmpl_2.product_subscription_pricing_ids = [(5, 0, 0)]
        self.env['sale.subscription.pricing'].create({'plan_id': self.plan_month.id, 'product_template_id': self.sub_product_tmpl.id, 'price': 42})
        self.env['sale.subscription.pricing'].create({'plan_id': self.plan_month.id, 'product_template_id': self.product_tmpl_2.id, 'price': 420})
        with freeze_time("2021-01-01"):
            self.subscription.order_line = False
            self.subscription.start_date = False
            self.subscription.next_invoice_date = False
            self.subscription.write({
                'partner_id': self.partner.id,
                'partner_invoice_id': self.partner_a_invoice.id,
                'partner_shipping_id': self.partner_a_shipping.id,
                'plan_id': self.plan_month.id,
                'order_line': [Command.create({'product_id': self.product.id,
                                               'name': "Monthly cheap",
                                               'price_unit': 42,
                                               'product_uom_qty': 2,
                                               }),
                               Command.create({'product_id': self.product2.id,
                                               'name': "Monthly expensive",
                                               'price_unit': 420,
                                               'product_uom_qty': 3,
                                               }),
                               ]
            })
            self.subscription.action_confirm()
            self.env['sale.order']._cron_recurring_create_invoice()
            self.subscription.invoice_ids.filtered(lambda am: am.state == 'draft')._post()

            self.assertEqual(self.subscription.order_line.sorted('id').mapped('product_uom_qty'), [2, 3], "Quantities should be equal to 2 and 3")
        with freeze_time("2021-01-15"):
            action = self.subscription.prepare_upsell_order()
            upsell_so = self.env['sale.order'].browse(action['res_id'])
            self.assertEqual(upsell_so.partner_invoice_id, self.partner_a_invoice)
            self.assertEqual(upsell_so.partner_shipping_id, self.partner_a_shipping)
            self.assertEqual(upsell_so.order_line.mapped('product_uom_qty'), [0, 0, 0], 'The upsell order has 0 quantity')
            note = upsell_so.order_line.filtered('display_type')
            self.assertEqual(note.name, '(*) These recurring products are discounted according to the prorated period from 01/15/2021 to 01/31/2021')
            self.assertEqual(upsell_so.order_line.product_id, self.subscription.order_line.product_id)
            upsell_so.order_line.filtered(lambda l: not l.display_type).product_uom_qty = 1
            # When the upsell order is created, all quantities are equal to 0
            # add line to quote manually, it must be taken into account in the subscription after validation
            upsell_so.order_line = [(0, 0, {
                'name': self.product2.name,
                'order_id': upsell_so.id,
                'product_id': self.product2.id,
                'product_uom_qty': 2,
                'product_uom': self.product2.uom_id.id,
                'price_unit': self.product2.list_price,
            }), (0, 0, {
                'name': self.product3.name,
                'order_id': upsell_so.id,
                'product_id': self.product3.id,
                'product_uom_qty': 1,
                'product_uom': self.product3.uom_id.id,
                'price_unit': self.product3.list_price,
            })]
            self.assertEqual(upsell_so.type_name, "Quotation")
            upsell_so.action_confirm()
            self.assertEqual(upsell_so.type_name, "Sales Order")
            self.subscription._create_recurring_invoice()
            self.subscription.invoice_ids.filtered(lambda am: am.state == 'draft')._post()
            discounts = [round(v, 2) for v in upsell_so.order_line.sorted('discount').mapped('discount')]
            self.assertEqual(discounts, [0.0, 45.16, 45.16, 45.16, 45.16], 'Prorated prices should be applied')
            prices = [round(v, 2) for v in upsell_so.order_line.sorted('id').mapped('price_subtotal')]
            self.assertEqual(prices, [23.03, 230.33, 0, 21.94, 23.03], 'Prorated prices should be applied')

        with freeze_time("2021-02-01"):
            self.env['sale.order']._cron_recurring_create_invoice()
            self.subscription.invoice_ids.filtered(lambda am: am.state == 'draft')._post()

        with freeze_time("2021-03-01"):
            self.env['sale.order']._cron_recurring_create_invoice()
            upsell_so._create_invoices()
            self.subscription.invoice_ids.filtered(lambda am: am.state == 'draft')._post()
            sorted_lines = self.subscription.order_line.sorted('id')
            self.assertEqual(sorted_lines.mapped('product_uom_qty'), [3.0, 4.0, 2.0, 1.0], "Quantities should be equal to 3.0, 4.0, 2.0, 1.0")

        with freeze_time("2021-04-01"):
            self.env['sale.order']._cron_recurring_create_invoice()
            self.subscription.invoice_ids.filtered(lambda am: am.state == 'draft')._post()
        with freeze_time("2021-05-01"):
            self.env['sale.order']._cron_recurring_create_invoice()
            self.subscription.invoice_ids.filtered(lambda am: am.state == 'draft')._post()
        with freeze_time("2021-06-01"):
            self.subscription._create_recurring_invoice()
            self.subscription.invoice_ids.filtered(lambda am: am.state == 'draft')._post()
        with freeze_time("2021-07-01"):
            self.env['sale.order']._cron_recurring_create_invoice()
            self.subscription.invoice_ids.filtered(lambda am: am.state == 'draft')._post()
        with freeze_time("2021-08-01"):
            self.env['sale.order']._cron_recurring_create_invoice()
            self.subscription.invoice_ids.filtered(lambda am: am.state == 'draft')._post()
            inv = self.subscription.invoice_ids.sorted('date')[-1]
            invoice_periods = inv.invoice_line_ids.sorted('id').mapped('name')
            first_period = invoice_periods[0].split('\n')[2]
            self.assertEqual(first_period, "1 Months 08/01/2021 to 08/31/2021")
            second_period = invoice_periods[1].split('\n')[2]
            self.assertEqual(second_period, "1 Months 08/01/2021 to 08/31/2021")

        self.assertEqual(len(self.subscription.order_line), 4)

    def test_sale_subscription_set_date(self):
        """ Test case to verify that updating the `start_date` on a copied upsell sale order
            correctly sets the new date in the subscription. """
        with freeze_time("2024-11-01"):
            self.subscription.action_confirm()
            self.env['sale.order']._cron_recurring_create_invoice()

        with freeze_time("2024-11-11"):
            # Prepare the upsell order from the subscription
            action = self.subscription.prepare_upsell_order()
            upsell_so = self.env['sale.order'].browse(action['res_id'])
            # Copy the upsell order
            upsell_so_new = upsell_so.copy()
            # Set a new start date on the copied upsell order
            new_start_date = fields.Date.from_string("2024-11-12")
            upsell_so_new.write({'start_date': new_start_date})
            self.assertEqual(upsell_so_new.start_date, new_start_date, "The start date of the copied upsell order should be updated.")

    def test_subscription_order_line_description(self):
        with freeze_time("2024-04-01"):
            self.subscription.action_confirm()
            self.env['sale.order']._cron_recurring_create_invoice()

        with freeze_time("2024-04-15"):
            action = self.subscription.prepare_upsell_order()
            upsell_so = self.env['sale.order'].browse(action['res_id'])
            self.assertEqual(upsell_so.order_line.mapped('discount'), [46.67, 46.67, 0])
            self.assertEqual(upsell_so.order_line[0].name, "Product 1(*)", "(*) should be added in discounted product's description")
            self.assertEqual(upsell_so.order_line[1].name, "Product 2(*)", "(*) should be added in discounted product's description")
            self.assertEqual(upsell_so.order_line[2].name, "(*) These recurring products are discounted according to the prorated period from 04/15/2024 to 04/30/2024")

    def test_upsell_prorata(self):
        """ Test the prorated values obtained when creating an upsell. complementary to the previous one where new
         lines had no existing default values.
        """
        self.env['sale.subscription.pricing'].create({'plan_id': self.plan_2_month.id, 'product_template_id': self.sub_product_tmpl.id, 'price': 42})
        self.env['sale.subscription.pricing'].create(
            {'plan_id': self.plan_2_month.id, 'product_template_id': self.product_tmpl_2.id, 'price': 42})
        with freeze_time("2021-01-01"):
            self.subscription.order_line = False
            self.subscription.start_date = False
            self.subscription.next_invoice_date = False
            self.subscription.write({
                'partner_id': self.partner.id,
                'plan_id': self.plan_2_month.id,
                'order_line': [
                    Command.create({
                        'product_id': self.product.id,
                        'name': "month: original",
                        'price_unit': 50,
                        'product_uom_qty': 1,
                    }),
                    Command.create({
                        'product_id': self.product2.id,
                        'name': "2 month: original",
                        'price_unit': 50,
                        'product_uom_qty': 1,
                    }),
                ]
            })

            self.subscription.action_confirm()
            self.subscription._create_recurring_invoice()

        with freeze_time("2021-01-20"):
            action = self.subscription.prepare_upsell_order()
            upsell_so = self.env['sale.order'].browse(action['res_id'])
            # Create new lines that should be aligned with existing ones
            so_line_vals = [{
                'name': 'Upsell added: 1 month',
                'order_id': upsell_so.id,
                'product_id': self.product2.id,
                'product_uom_qty': 1,
                'product_uom': self.product2.uom_id.id,
                'price_unit': self.product.list_price,
            }, {
                'name': 'Upsell added: 2 month',
                'order_id': upsell_so.id,
                'product_id': self.product3.id,
                'product_uom_qty': 1,
                'product_uom': self.product3.uom_id.id,
                'price_unit': self.product3.list_price,
            }]
            self.env['sale.order.line'].create(so_line_vals)
            upsell_so.order_line.product_uom_qty = 1
            discounts = [round(v) for v in upsell_so.order_line.sorted('discount').mapped('discount')]
            # discounts for: 40/59 days
            self.assertEqual(discounts, [0, 32, 32, 32, 32], 'Prorated prices should be applied')
            self.assertEqual(self.subscription.order_line.ids, upsell_so.order_line.parent_line_id.ids,
                             "The parent line id should correspond to the first two lines")
            # discounts for: 12d/31d; 40d/59d; 21d/31d (shifted); 31d/41d; 59d/78d;
            self.assertEqual(discounts, [0, 32, 32, 32, 32], 'Prorated prices should be applied')
            prices = [round(v, 2) for v in upsell_so.order_line.sorted('price_subtotal').mapped('price_subtotal')]
            self.assertEqual(prices, [0.0, 28.48, 28.48, 28.48, 28.48], 'Prorated prices should be applied')

    def test_recurring_revenue(self):
        """Test computation of recurring revenue"""
        # Initial subscription is $100/y
        self.subscription_tmpl.write({'duration_value': 1, 'duration_unit': 'year'})
        self.subscription.write({
            'plan_id': self.plan_2_month.id,
            'start_date': False,
            'next_invoice_date': False,
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'payment_token_id': self.payment_token.id,
        })
        self.subscription.order_line[0].write({'price_unit': 1200, 'technical_price_unit': 1200})
        self.subscription.order_line[1].write({'price_unit': 200, 'technical_price_unit': 200})
        self.subscription.action_confirm()
        self.assertAlmostEqual(self.subscription.amount_untaxed, 1400, msg="unexpected price after setup")
        self.assertAlmostEqual(self.subscription.recurring_monthly, 700, msg="Half because invoice every two months")
        # Change periodicity
        self.subscription.order_line.product_id.product_subscription_pricing_ids = [(6, 0, 0)] # remove all pricings to fallaback on list price
        self.subscription.plan_id = self.plan_year
        self.assertAlmostEqual(self.subscription.amount_untaxed, 70, msg='Recompute price_unit : 50 (product) + 20 (product2)')
        # 1200 over 4 year = 25/year + 100 per month
        self.assertAlmostEqual(self.subscription.recurring_monthly, 5.84, msg='70 / 12')

    def test_recurring_total(self):
        """Test rounding of (non-) recurring total"""
        self.company.write({
            'currency_id': self.env.ref('base.BGN').id,
            'account_price_include': 'tax_included',
            'tax_calculation_rounding_method': 'round_globally',
        })
        sub_tax = self.env['account.tax'].create({
            'name': '20% BG',
            'amount': 20,
            'company_id': self.company.id,
        })
        subscription = self.env['sale.order'].create({
            'name': 'TestSubscription',
            'is_subscription': True,
            'company_id': self.company.id,
            'plan_id': self.plan_month.id,
            'partner_id': self.user_portal.partner_id.id,
            'order_line': [
                Command.create({'product_id': self.product.id,
                                'price_unit': 140,
                                'tax_id': [Command.set(sub_tax.ids)]
                                }),
                Command.create({'product_id': self.product.id,
                                'price_unit': 36.97,
                                'tax_id': [Command.set(sub_tax.ids)]
                                }),
                Command.create({'product_id': self.product.id,
                                'price_unit': 36.97,
                                'tax_id': [Command.set(sub_tax.ids)]
                                }),
                Command.create({'product_id': self.product.id,
                                'price_unit': 21,
                                'tax_id': [Command.set(sub_tax.ids)]
                                }),
                ]
        })
        self.assertEqual(subscription.non_recurring_total, 0)
        self.assertEqual(subscription.recurring_total, 195.78)

    def test_compute_kpi(self):
        self.env['sale.order.alert'].create([
            {
                'name': 'Bad domain Setup',
                'trigger_condition': 'on_create_or_write',
                'mrr_min': 0,
                'mrr_max': 80,
                'subscription_state': '3_progress',
                'action': 'set_health_value',
                'health': 'bad'
            }, {
                'name': 'Good domain Setup',
                'trigger_condition': 'on_create_or_write',
                'mrr_min': 120,
                'mrr_max': 9999,
                'action': 'set_health_value',
                'health': 'done'
            },
        ])
        self.subscription.action_confirm()
        self.env['sale.order']._cron_update_kpi()
        self.assertEqual(self.subscription.health, 'bad')

        # 16 to 6 weeks: 80
        # 6 to 2 weeks: 100
        # 2weeks - today : 120
        date_log = datetime.date.today() - relativedelta(weeks=16)
        self.env['sale.order.log'].sudo().create({
            'event_type': '1_expansion',
            'event_date': date_log,
            'create_date': date_log,
            'order_id': self.subscription.id,
            'recurring_monthly': 80,
            'amount_signed': 80,
            'currency_id': self.subscription.currency_id.id,
            'subscription_state': self.subscription.subscription_state,
            'user_id': self.subscription.user_id.id,
            'team_id': self.subscription.team_id.id,
        })

        date_log = datetime.date.today() - relativedelta(weeks=6)
        self.env['sale.order.log'].sudo().create({
            'event_type': '1_expansion',
            'event_date': date_log,
            'create_date': date_log,
            'order_id': self.subscription.id,
            'recurring_monthly': 100,
            'amount_signed': 20,
            'currency_id': self.subscription.currency_id.id,
            'subscription_state': self.subscription.subscription_state,
            'user_id': self.subscription.user_id.id,
            'team_id': self.subscription.team_id.id,
         })

        self.subscription.recurring_monthly = 120.0
        date_log = datetime.date.today() - relativedelta(weeks=2)
        self.env['sale.order.log'].sudo().create({
            'event_type': '1_expansion',
            'event_date': date_log,
            'create_date': date_log,
            'order_id': self.subscription.id,
            'recurring_monthly': 120,
            'amount_signed': 20,
            'currency_id': self.subscription.currency_id.id,
            'subscription_state': self.subscription.subscription_state,
            'user_id': self.subscription.user_id.id,
            'team_id': self.subscription.team_id.id,
        })
        self.subscription._cron_update_kpi()
        self.assertEqual(self.subscription.kpi_1month_mrr_delta, 20.0)
        self.assertEqual(self.subscription.kpi_1month_mrr_percentage, 0.2)
        self.assertEqual(self.subscription.kpi_3months_mrr_delta, 40.0)
        self.assertEqual(self.subscription.kpi_3months_mrr_percentage, 0.5)
        self.assertEqual(self.subscription.health, 'done')

    def test_onchange_date_start(self):
        recurring_bound_tmpl = self.env['sale.order.template'].create({
            'name': 'Recurring Bound Template',
            'plan_id': self.plan_month.id,
            'is_unlimited': False,
            'duration_unit': 'month',
            'duration_value': 3,
            'sale_order_template_line_ids': [Command.create({
                'name': "monthly",
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'product_uom_id': self.product.uom_id.id
            })]
        })
        sub_form = Form(self.env['sale.order'])
        sub_form.partner_id = self.user_portal.partner_id
        sub_form.sale_order_template_id = recurring_bound_tmpl
        sub = sub_form.save()
        sub._onchange_sale_order_template_id()
        # The end date is set upon confirmation
        sub.action_confirm()
        self.assertEqual(sub.sale_order_template_id.is_unlimited, False)
        self.assertIsInstance(sub.end_date, datetime.date)

    def test_changed_next_invoice_date(self):
        # Test wizard to change next_invoice_date manually
        with freeze_time("2022-01-01"):
            self.subscription.write({'start_date': False, 'next_invoice_date': False})
            self.env['sale.order.line'].create({
                'name': self.product2.name,
                'order_id': self.subscription.id,
                'product_id': self.product2.id,
                'product_uom_qty': 3,
                'product_uom': self.product2.uom_id.id,
                'price_unit': 42})

            self.subscription.action_confirm()
            self.subscription._create_recurring_invoice()
            today = fields.Date.today()
            self.assertEqual(self.subscription.start_date, today, "start date should be set to today")
            self.assertEqual(self.subscription.next_invoice_date, datetime.date(2022, 2, 1))
            # We decide to invoice the monthly subscription on the 5 of february
            self.subscription.next_invoice_date = fields.Date.from_string('2022-02-05')
            # check the invoice state
            self.assertEqual(self.subscription.invoice_status, 'invoiced')

        with freeze_time("2022-02-01"):
            # Nothing should be invoiced
            self.subscription._cron_recurring_create_invoice()
            # next_invoice_date : 2022-02-5 but the previous invoice deferred_end_date was set on the 2022-02-01
            # We can't prevent it to be re-invoiced.
            inv = self.subscription.invoice_ids.sorted('date')
            # Nothing was invoiced
            self.assertEqual(inv.date, datetime.date(2022, 1, 1))

        with freeze_time("2022-02-05"):
            self.subscription._cron_recurring_create_invoice()
            inv = self.subscription.invoice_ids.sorted('date')
            self.assertEqual(inv[-1].date, datetime.date(2022, 2, 5))
            self.assertEqual(self.subscription.invoice_status, 'invoiced')

    def test_product_change(self):
        """Check behaviour of the product onchange (taxes mostly)."""
        # check default tax
        self.sub_product_tmpl.product_subscription_pricing_ids = [(6, 0, self.pricing_month.ids)]
        self.pricing_month.price = 50

        self.subscription.order_line.unlink()
        sub_form = Form(self.subscription)
        sub_form.plan_id = self.plan_month
        with sub_form.order_line.new() as line:
            line.product_id = self.product
        sub = sub_form.save()
        self.assertEqual(sub.order_line.tax_id, self.tax_10, 'Default tax for product should have been applied.')
        self.assertEqual(sub.amount_tax, 5.0,
                         'Default tax for product should have been applied.')
        self.assertEqual(sub.amount_total, 55.0,
                         'Default tax for product should have been applied.')
        # Change the product
        line_id = sub.order_line.ids
        sub.write({
            'order_line': [(1, line_id[0], {'product_id': self.product4.id})]
        })
        self.assertEqual(sub.order_line.tax_id, self.tax_20,
                         'Default tax for product should have been applied.')
        self.assertEqual(sub.amount_tax, 3,
                         'Default tax for product should have been applied.')
        self.assertEqual(sub.amount_total, 18,
                         'Default tax for product should have been applied.')

    def test_log_change_pricing(self):
        """ Test subscription log generation when template_id is changed """
        self.sub_product_tmpl.product_subscription_pricing_ids.price = 120 # 120 for monthly and yearly
        # Create a subscription and add a line, should have logs with MMR 120
        subscription = self.env['sale.order'].create({
            'name': 'TestSubscription',
            'start_date': False,
            'next_invoice_date': False,
            'plan_id': self.plan_month.id,
            'partner_id': self.user_portal.partner_id.id,
            'sale_order_template_id': self.subscription_tmpl.id,
        })
        self.cr.precommit.clear()
        subscription.write({'order_line': [(0, 0, {
            'name': 'TestRecurringLine',
            'product_id': self.product.id,
            'product_uom_qty': 1,
            'product_uom': self.product.uom_id.id})]})
        subscription.action_confirm()
        self.flush_tracking()
        init_nb_log = len(subscription.order_log_ids)
        self.assertEqual(subscription.order_line.recurring_monthly, 120)
        subscription.plan_id = self.plan_year
        self.assertEqual(subscription.order_line.recurring_monthly, 10)
        self.flush_tracking()
        # Should get one more log with MRR 10 (so change is -110)
        self.assertEqual(len(subscription.order_log_ids), init_nb_log + 1,
                         "Subscription log not generated after change of the subscription template")
        self.assertRecordValues(subscription.order_log_ids[-1],
                                [{'recurring_monthly': 10.0, 'amount_signed': -110}])

    def test_fiscal_position(self):
        # Test that the fiscal postion FP is applied on recurring invoice.
        # FP must mapped an included tax of 21% to an excluded one of 0%
        tax_include_id = self.env['account.tax'].create({'name': "Include tax",
                                                         'amount': 21.0,
                                                         'price_include_override': 'tax_included',
                                                         'type_tax_use': 'sale'})
        tax_exclude_id = self.env['account.tax'].create({'name': "Exclude tax",
                                                         'amount': 0.0,
                                                         'type_tax_use': 'sale'})

        product_tmpl = self.env['product.template'].create(dict(name="Voiture",
                                                                list_price=121,
                                                                taxes_id=[(6, 0, [tax_include_id.id])]))

        fp = self.env['account.fiscal.position'].create({'name': "fiscal position",
                                                         'sequence': 1,
                                                         'auto_apply': True,
                                                         'tax_ids': [(0, 0, {'tax_src_id': tax_include_id.id,
                                                                             'tax_dest_id': tax_exclude_id.id})]})
        self.subscription.fiscal_position_id = fp.id
        self.subscription.partner_id.property_account_position_id = fp
        sale_order = self.env['sale.order'].create({
            'name': 'TestSubscription',
            'fiscal_position_id': fp.id,
            'partner_id': self.user_portal.partner_id.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'order_line': [Command.create({
                'product_id': product_tmpl.product_variant_id.id,
                'product_uom': self.env.ref('uom.product_uom_unit').id,
                'product_uom_qty': 1
            })]
        })
        sale_order.action_confirm()
        inv = sale_order._create_invoices()
        self.assertEqual(100, inv.invoice_line_ids[0].price_unit, "The included tax must be subtracted to the price")

    def test_quantity_on_product_invoice_ordered_qty(self):
        # This test checks that the invoiced qty and to_invoice qty have the right behavior
        # Service product
        self.product.write({
            'type': 'service'
        })
        with freeze_time("2021-01-01"):
            self.subscription.order_line = False
            self.subscription.write({
                'start_date': False,
                'next_invoice_date': False,
                'plan_id': self.plan_month.id,
                'partner_id': self.partner.id,
                'order_line': [Command.create({'product_id': self.product2.id,
                                               'price_unit': 420,
                                               'product_uom_qty': 3,
                                               }),
                                Command.create({'product_id': self.product.id,
                                               'price_unit': 42,
                                               'product_uom_qty': 1,
                                               }),
                               ]
            })
            self.subscription.action_confirm()
            val_confirm = self._get_quantities(self.subscription.order_line)
            self.assertEqual(val_confirm['to_invoice'], [3, 1], "To invoice should be equal to quantity")
            self.assertEqual(val_confirm['invoiced'], [0, 0], "To invoice should be equal to quantity")
            self.assertEqual(val_confirm['delivered'], [0, 0], "Delivered qty not should be set")
            self.env['sale.order']._cron_recurring_create_invoice()
            self.subscription.order_line[0].write({'qty_delivered': 3})
            self.subscription.order_line[1].write({'qty_delivered': 1})
            val_invoice = self._get_quantities(self.subscription.order_line)
            self.assertEqual(val_invoice['invoiced'], [3, 1], "To invoice should be equal to quantity")
            self.assertEqual(val_invoice['to_invoice'], [0, 0], "To invoice should be 0")
            self.assertEqual(val_invoice['delivered'], [3, 1], "Delivered qty should be set")

        with freeze_time("2021-01-05"):
            val_invoice = self._get_quantities(self.subscription.order_line)
            self.assertEqual(val_invoice['invoiced'], [3, 1], "To invoice should be equal to quantity")
            self.assertEqual(val_invoice['to_invoice'], [0, 0], "To invoice should be 0")
            self.assertEqual(val_invoice['delivered'], [3, 1], "Delivered qty should be set")

        with freeze_time("2021-02-02"):
            self.env['sale.order']._cron_recurring_create_invoice()
            val_invoice = self._get_quantities(self.subscription.order_line)
            self.assertEqual(val_invoice['to_invoice'], [0, 0], "To invoice should be 0")
            self.assertEqual(val_invoice['invoiced'], [3, 1], "To invoice should be equal to quantity")
            self.assertEqual(val_invoice['delivered'], [3, 1], "Delivered qty should be equal to quantity")

        with freeze_time("2021-02-15"):
            self.subscription.order_line[1].write({'qty_delivered': 3, 'product_uom_qty': 3})
            val_invoice = self._get_quantities(
                self.subscription.order_line
            )
            self.assertEqual(val_invoice['to_invoice'], [0, 2], "To invoice should be equal to quantity")
            self.assertEqual(val_invoice['invoiced'], [3, 1], "invoiced should be correct")
            self.assertEqual(val_invoice['delivered'], [3, 3], "Delivered qty should be equal to quantity")

        with freeze_time("2021-03-01"):
            self.env['sale.order']._cron_recurring_create_invoice()
            self.env.invalidate_all()
            val_invoice = self._get_quantities(self.subscription.order_line)
            self.assertEqual(val_invoice['to_invoice'], [0, 0], "To invoice should be equal to quantity")
            self.assertEqual(val_invoice['delivered'], [3, 3], "Delivered qty should be equal to quantity")
            self.assertEqual(val_invoice['invoiced'], [3, 3], "To invoice should be equal to quantity delivered")

    def test_update_prices_template(self):
        recurring_bound_tmpl = self.env['sale.order.template'].create({
            'name': 'Subscription template without discount',
            'duration_unit': 'year',
            'is_unlimited': False,
            'duration_value': 2,
            'plan_id': self.plan_month.id,
            'note': "This is the template description",
            'sale_order_template_line_ids': [
                Command.create({
                    'name': "monthly",
                    'product_id': self.product.id,
                    'product_uom_id': self.product.uom_id.id
                }),
                Command.create({
                    'name': "yearly",
                    'product_id': self.product.id,
                    'product_uom_id': self.product.uom_id.id,
                }),
            ],
            'sale_order_template_option_ids': [
                Command.create({
                    'name': "option",
                    'product_id': self.product.id,
                    'quantity': 1,
                    'uom_id': self.product2.uom_id.id
                }),
            ],
        })

        sub_form = Form(self.env['sale.order'])
        sub_form.partner_id = self.user_portal.partner_id
        sub_form.sale_order_template_id = recurring_bound_tmpl
        sub = sub_form.save()
        self.assertEqual(len(sub.order_line.ids), 2)

    def test_product_invoice_delivery(self):
        sub = self.subscription
        sub.order_line = [Command.clear()]
        context_no_mail = {'no_reset_password': True, 'mail_create_nosubscribe': True, 'mail_create_nolog': True, }
        delivered_product_tmpl = self.env['product.template'].with_context(context_no_mail).create({
            'name': 'Delivery product',
            'type': 'service',
            'recurring_invoice': True,
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'invoice_policy': 'delivery',
        })
        product = delivered_product_tmpl.product_variant_id
        product.write({
            'list_price': 50.0,
            'taxes_id': [(6, 0, [self.tax_10.id])],
            'property_account_income_id': self.account_income.id,
        })

        with freeze_time("2021-01-03"):
            # January
            sub.plan_id = self.plan_month
            sub.start_date = False
            sub.next_invoice_date = False
            sub.order_line = [Command.create({'product_id': product.id,
                                              'name': "coucou",
                                              'price_unit': 42,
                                              'product_uom_qty': 1,
                                              })]
            sub.action_confirm()
            sub._create_recurring_invoice()
            self.assertFalse(sub.order_line.qty_delivered)
            # We only invoice what we deliver
            self.assertFalse(sub.order_line.qty_to_invoice)
            self.assertFalse(sub.invoice_count, "We don't invoice if we don't deliver the product")
            self.assertEqual(sub.next_invoice_date, datetime.date(2021, 2, 3), 'But we still update the next invoice date')

        with freeze_time("2021-02-03"):
            # Deliver some product
            sub.order_line.qty_delivered = 1
            self.assertEqual(sub.order_line.qty_to_invoice, 1)
            inv = sub._create_recurring_invoice()
            self.assertEqual(inv.invoice_line_ids.deferred_start_date, datetime.date(2021, 1, 3))
            self.assertEqual(inv.invoice_line_ids.deferred_end_date, datetime.date(2021, 2, 2))
            self.assertTrue(sub.invoice_count, "We should have invoiced")
            self.assertEqual(sub.next_invoice_date, datetime.date(2021, 3, 3))

        with freeze_time("2021-03-03"):
            inv = sub._create_recurring_invoice()
            # The quantity to invoice and delivered are reset after the creation of the invoice
            self.assertTrue(sub.order_line.qty_delivered)
            self.assertEqual(inv.invoice_line_ids.quantity, 1)

        with freeze_time("2021-04-03"):
            # February
            sub.order_line.qty_delivered = 1
            sub._create_recurring_invoice()
            self.assertEqual(sub.order_line.qty_delivered, 1)
            inv = sub.invoice_ids.sorted('date')[-1]
            self.assertEqual(inv.invoice_line_ids.quantity, 1)

        with freeze_time("2021-05-03"):
            # March
            sub.order_line.qty_delivered = 2
            sub._create_recurring_invoice()
            inv = sub.invoice_ids.sorted('date')[-1]
            self.assertEqual(inv.invoice_line_ids.quantity, 2)
            self.assertEqual(sub.order_line.product_uom_qty, 1)

        with freeze_time("2021-04-03"):
            # February
            sub.order_line.qty_delivered = 1
            sub._create_recurring_invoice()
            self.assertEqual(sub.order_line.qty_delivered, 1)
            inv = sub.invoice_ids.sorted('date')[-1]
            self.assertEqual(inv.invoice_line_ids.quantity, 2)

        with freeze_time("2021-05-03"):
            # March
            sub.order_line.qty_delivered = 2
            sub._create_recurring_invoice()
            inv = sub.invoice_ids.sorted('date')[-1]
            self.assertEqual(inv.invoice_line_ids.quantity, 2)
            self.assertEqual(sub.order_line.product_uom_qty, 1)

    def test_mixed_delivered_ordered_products(self):
        self.product.name = "ordered Product"
        self.assertEqual(self.product.invoice_policy, 'order')
        self.assertEqual(self.product.type, 'service')
        sub = self.subscription
        sub.order_line = [Command.clear()]
        context_no_mail = {'no_reset_password': True, 'mail_create_nosubscribe': True, 'mail_create_nolog': True}
        delivered_product_tmpl = self.env['product.template'].with_context(context_no_mail).create({
            'name': 'Delivery product',
            'type': 'service',
            'recurring_invoice': True,
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'invoice_policy': 'delivery',
        })
        product = delivered_product_tmpl.product_variant_id
        product.write({
            'list_price': 50.0,
            'taxes_id': [(6, 0, [self.tax_10.id])],
            'property_account_income_id': self.account_income.id,
        })
        with freeze_time("2021-01-03"):
            # January
            sub.plan_id = self.plan_month.id
            sub.start_date = False
            sub.next_invoice_date = False
            sub.order_line = [Command.create({
                'product_id': product.id,
                'name': "delivered product",
                'price_unit': 10,
                'product_uom_qty': 1,
            }), Command.create({
                'product_id': self.product.id,
                'name': "ordered product",
                'price_unit': 5,
                'product_uom_qty': 1,
            })]
            sub.action_confirm()
            inv = sub._create_recurring_invoice()
            # We only invoice what we deliver
            self.assertEqual(sub.order_line.mapped('qty_invoiced'), [0, 1])
            self.assertEqual(sub.order_line.mapped('qty_to_invoice'), [0, 0])
            self.assertEqual(sub.order_line.mapped('qty_delivered'), [0, 0])
            self.assertEqual(sub.invoice_count, 1, "First invoice is created")
            self.assertEqual(sub.next_invoice_date, datetime.date(2021, 2, 3))

        with freeze_time("2021-02-03"):
            # Deliver some product
            sub.order_line[0].qty_delivered = 1
            inv = sub._create_recurring_invoice()
            self.assertEqual(inv.invoice_line_ids.mapped('deferred_start_date'), [datetime.date(2021, 1, 3), datetime.date(2021, 2, 3)])
            self.assertEqual(inv.invoice_line_ids.mapped('deferred_end_date'), [datetime.date(2021, 2, 2), datetime.date(2021, 3, 2)])
            self.assertTrue(sub.invoice_count, "We should have invoiced")
            self.assertEqual(sub.next_invoice_date, datetime.date(2021, 3, 3))

        with freeze_time("2021-02-15"):
            action = sub.prepare_upsell_order()
            upsell_so = self.env['sale.order'].browse(action['res_id'])
            self.assertEqual(upsell_so.order_line.product_id, self.product,
                         "deliver product should not be included in the upsell")

    def test_recurring_invoices_from_interface(self):
        # From the interface, all the subscription lines are invoiced
        sub = self.subscription
        sub.end_date = datetime.date(2029, 4, 1)
        with freeze_time("2021-01-01"):
            self.subscription.write({'start_date': False, 'next_invoice_date': False, 'plan_id': self.plan_month.id})
            sub.action_confirm()
            # first invoice: automatic or not, it's the same behavior. All line are invoiced
            sub._create_invoices()
            sub.order_line.invoice_lines.move_id._post()
            self.assertEqual("2021-02-01", sub.next_invoice_date.strftime("%Y-%m-%d"))
            inv = sub.invoice_ids.sorted('date')[-1]
            invoice_start_periods = inv.invoice_line_ids.mapped('deferred_start_date')
            invoice_end_periods = inv.invoice_line_ids.mapped('deferred_end_date')
            self.assertEqual(invoice_start_periods, [datetime.date(2021, 1, 1), datetime.date(2021, 1, 1)])
            self.assertEqual(invoice_end_periods, [datetime.date(2021, 1, 31), datetime.date(2021, 1, 31)])
        with freeze_time("2021-02-01"):
            sub._create_invoices()
            inv = sub.invoice_ids.sorted('date')[-1]
            invoice_start_periods = inv.invoice_line_ids.mapped('deferred_start_date')
            invoice_end_periods = inv.invoice_line_ids.mapped('deferred_end_date')
            self.assertEqual(invoice_start_periods, [datetime.date(2021, 2, 1), datetime.date(2021, 2, 1)], "monthly is updated everytime in manual action")
            self.assertEqual(invoice_end_periods, [datetime.date(2021, 2, 28), datetime.date(2021, 2, 28)], "both lines are invoiced")
            with self.assertRaisesRegex(UserError, 'The following recurring orders have draft invoices. Please Confirm them or cancel them'):
                sub._create_invoices()
            inv._post()
            self.assertEqual("2021-03-01", sub.next_invoice_date.strftime("%Y-%m-%d"), "Next invoice date should be updated")
            sub._create_invoices()
            inv = sub.invoice_ids.sorted('id')[-1]
            inv._post()
            self.assertEqual("2021-04-01", sub.next_invoice_date.strftime("%Y-%m-%d"))
            invoice_start_periods = inv.invoice_line_ids.mapped('deferred_start_date')
            invoice_end_periods = inv.invoice_line_ids.mapped('deferred_end_date')
            self.assertEqual(invoice_start_periods, [datetime.date(2021, 3, 1), datetime.date(2021, 3, 1)], "monthly is updated everytime in manual action")
            self.assertEqual(invoice_end_periods, [datetime.date(2021, 3, 31), datetime.date(2021, 3, 31)], "monthly is updated everytime in manual action")

        with freeze_time("2021-04-01"):
            # Automatic invoicing, only one line generated
            inv = sub._create_recurring_invoice()
            invoice_start_periods = inv.invoice_line_ids.mapped('deferred_start_date')
            invoice_end_periods = inv.invoice_line_ids.mapped('deferred_end_date')
            self.assertEqual(invoice_start_periods, [datetime.date(2021, 4, 1), datetime.date(2021, 4, 1)], "Monthly is updated because it is due")
            self.assertEqual(invoice_end_periods, [datetime.date(2021, 4, 30), datetime.date(2021, 4, 30)], "Monthly is updated because it is due")
            self.assertEqual(inv.date, datetime.date(2021, 4, 1))

        with freeze_time("2021-05-01"):
            # Automatic invoicing, only one line generated
            sub._create_recurring_invoice()
            inv = sub.invoice_ids.sorted('date')[-1]
            invoice_start_periods = inv.invoice_line_ids.mapped('deferred_start_date')
            invoice_end_periods = inv.invoice_line_ids.mapped('deferred_end_date')
            self.assertEqual(invoice_start_periods, [datetime.date(2021, 5, 1), datetime.date(2021, 5, 1)], "Monthly is updated because it is due")
            self.assertEqual(invoice_end_periods, [datetime.date(2021, 5, 31), datetime.date(2021, 5, 31)], "Monthly is updated because it is due")
            self.assertEqual(inv.date, datetime.date(2021, 5, 1))

        with freeze_time("2022-02-02"):
            # We prevent the subscription to be automatically closed because the next invoice date is passed for too long
            sub.plan_id.auto_close_limit = 999
            # With non-automatic, we invoice all line prior to today once
            inv = sub._create_invoices()
            inv._post()
            self.assertEqual("2021-07-01", sub.next_invoice_date.strftime("%Y-%m-%d"), "on the 1st of may, nid is updated to 1fst of june and here we force the line to be apdated again")
            inv = sub.invoice_ids.sorted('date')[-1]
            invoice_start_periods = inv.invoice_line_ids.mapped('deferred_start_date')
            invoice_end_periods = inv.invoice_line_ids.mapped('deferred_end_date')
            self.assertEqual(invoice_start_periods, [datetime.date(2021, 6, 1), datetime.date(2021, 6, 1)], "monthly is updated when prior to today")
            self.assertEqual(invoice_end_periods, [datetime.date(2021, 6, 30), datetime.date(2021, 6, 30)], "monthly is updated when prior to today")

    def test_renew_kpi_mrr(self):
        # Test that renew with MRR transfer give correct result
        # First, whe create a sub with MRR = 21
        # Then we renew it with a MRR of 42
        # After a few months the MRR of the renewal is 63
        # We also create and renew a free subscription
        SaleOrder = self.env["sale.order"]
        with freeze_time("2021-01-01"), patch.object(type(SaleOrder), '_get_unpaid_subscriptions', lambda x: []):
            self.subscription.plan_id.auto_close_limit = 5000 # don't close automatically contract if unpaid invoices
            # so creation with mail tracking
            context_mail = {'tracking_disable': False}
            sub = self.env['sale.order'].with_context(context_mail).create({
                'name': 'Parent Sub',
                'is_subscription': True,
                'note': "original subscription description",
                'partner_id': self.user_portal.partner_id.id,
                'pricelist_id': self.company_data['default_pricelist'].id,
                'sale_order_template_id': self.subscription_tmpl.id,
            })
            free_sub = self.env['sale.order'].with_context(context_mail).create({
                'name': 'Parent free Sub',
                'is_subscription': True,
                'note': "original subscription description",
                'partner_id': self.user_portal.partner_id.id,
                'pricelist_id': self.company_data['default_pricelist'].id,
                'plan_id': self.plan_month.id,
                'client_order_ref': 'free',
                'order_line': [
                    (0, 0, {
                        'name': self.product.name,
                        'product_id': self.product.id,
                        'product_uom_qty': 3.0,
                        'product_uom': self.product.uom_id.id,
                        'price_unit': 0,
                    })],
            })

            future_sub = self.env['sale.order'].with_context(context_mail).create({
                'name': 'FutureSub',
                'is_subscription': True,
                'note': "original subscription description",
                'partner_id': self.user_portal.partner_id.id,
                'pricelist_id': self.company_data['default_pricelist'].id,
                'plan_id': self.plan_month.id,
                'start_date': '2021-06-01',
                'order_line': [
                    (0, 0, {
                        'name': self.product.name,
                        'product_id': self.product.id,
                        'product_uom_qty': 1.0,
                        'product_uom': self.product.uom_id.id,
                    })],
            })

            self.assertFalse(free_sub.amount_total)
            self.flush_tracking()
            sub._onchange_sale_order_template_id()
            # Same product for both lines
            sub.order_line.product_uom_qty = 1
            (free_sub | sub).end_date = datetime.date(2022, 1, 1)
            (free_sub | sub | future_sub).action_confirm()
            self.flush_tracking()
            self.assertEqual(sub.recurring_monthly, 21, "20 + 1 for both lines")
            self.assertEqual(sub.subscription_state, "3_progress")
            self.env['sale.order'].with_context(tracking_disable=False)._cron_recurring_create_invoice()
        with freeze_time("2021-02-01"):
            self.env['sale.order'].with_context(tracking_disable=False)._cron_recurring_create_invoice()
        with freeze_time("2021-03-01"):
            self.env['sale.order'].with_context(tracking_disable=False)._cron_recurring_create_invoice()
        with freeze_time("2021-04-01"):
            # We create a renewal order in april for the new year
            self.env['sale.order']._cron_recurring_create_invoice()
            action = sub.with_context(tracking_disable=False).prepare_renewal_order()
            renewal_so = self.env['sale.order'].browse(action['res_id'])
            renewal_so = renewal_so.with_context(tracking_disable=False)
            renewal_so.order_line.product_uom_qty = 3
            renewal_so.name = "Renewal"
            self.flush_tracking()
            action = free_sub.with_context(tracking_disable=False).prepare_renewal_order()
            free_renewal_so = self.env['sale.order'].browse(action['res_id'])
            free_renewal_so = free_renewal_so.with_context(tracking_disable=False)
            free_renewal_so.order_line.write({'product_uom_qty': 2, 'price_unit': 0})
            self.flush_tracking()
            self.assertEqual(renewal_so.subscription_state, '2_renewal')
            (sub | free_sub).pause_subscription() # we pause the contracts to make sure no parasite log are created
            self.flush_tracking()
            self.env['sale.order']._cron_recurring_create_invoice()
            self.flush_tracking()
            (renewal_so | free_renewal_so).action_confirm()
            self.flush_tracking()
            self.assertEqual(sub.subscription_state, '5_renewed')
            self.assertEqual(renewal_so.subscription_state, '3_progress')
            (sub | free_sub).resume_subscription() # we resume the contracts to make sure no parasite log are created
            self.flush_tracking()
            # Most of the time, the renewal invoice is created by the salesman
            # before the renewal start date
            renewal_invoices = (free_renewal_so | renewal_so)._create_invoices()
            renewal_invoices._post()
            self.flush_tracking()
            # "upsell" of the simple sub that did not start yet
            future_sub.order_line.product_uom_qty = 4
            self.flush_tracking()
            self.assertEqual(sub.recurring_monthly, 21, "MRR should still be non null")
            self.assertEqual(sub.subscription_state, '5_renewed')
            self.assertEqual(renewal_so.recurring_monthly, 63, "MRR of renewal should not be computed before start_date of the lines")
            self.flush_tracking()
            # renew is still not ongoing;  Total MRR is 21 coming from the original sub
            self.env['sale.order'].sudo()._cron_subscription_expiration()
            self.assertEqual(sub.recurring_monthly, 21)
            self.assertEqual(renewal_so.recurring_monthly, 63)
            self.env['sale.order']._cron_recurring_create_invoice()
            self.flush_tracking()
            self.subscription._cron_update_kpi()
            self.assertEqual(sub.kpi_1month_mrr_delta, 0)
            self.assertEqual(sub.kpi_1month_mrr_percentage, 0)
            self.assertEqual(sub.kpi_3months_mrr_delta, 0)
            self.assertEqual(sub.kpi_3months_mrr_percentage, 0)
            self.assertEqual(sub.subscription_state, '5_renewed')

        with freeze_time("2021-04-20"):
            # We upsell the renewal after it's confirmation but before its start_date The event date must be "today"
            self.flush_tracking()
            renewal_so.order_line[1].product_uom_qty += 1
            self.flush_tracking()

        with freeze_time("2021-05-05"): # We switch the cron the X of may to make sure the day of the cron does not affect the numbers
            # Renewal period is from 2021-05 to 2021-06
            self.env['sale.order']._cron_recurring_create_invoice()
            self.assertEqual(sub.recurring_monthly, 21)
            self.assertEqual(sub.subscription_state, '5_renewed')
            self.assertEqual(renewal_so.next_invoice_date, datetime.date(2021, 6, 1))
            self.assertEqual(renewal_so.recurring_monthly, 83)
            self.flush_tracking()

        with freeze_time("2021-05-15"):
            self.env['sale.order']._cron_recurring_create_invoice()
            sub.order_line._compute_recurring_monthly()
            self.flush_tracking()

        with freeze_time("2021-06-01"):
            self.subscription._cron_update_kpi()
            self.env['sale.order']._cron_recurring_create_invoice()
            self.assertEqual(sub.recurring_monthly, 21)
            self.assertEqual(renewal_so.recurring_monthly, 83)
            self.flush_tracking()

        with freeze_time("2021-07-01"), patch.object(type(SaleOrder), '_get_unpaid_subscriptions', lambda x: []):
            # Total MRR is 42 coming from renew
            self.subscription._cron_update_kpi()
            self.env['sale.order']._cron_recurring_create_invoice()
            self.env['sale.order']._cron_subscription_expiration()
            # we trigger the compute because it depends on today value.
            self.assertEqual(sub.recurring_monthly, 21)
            self.assertEqual(renewal_so.recurring_monthly, 83)
            self.flush_tracking()

        with freeze_time("2021-08-03"), patch.object(type(SaleOrder), '_get_unpaid_subscriptions', lambda x: []):
            # We switch the cron the X of august to make sure the day of the cron does not affect the numbers
            renewal_so.end_date = datetime.date(2032, 1, 1)
            self.flush_tracking()
            # Total MRR is 80 coming from renewed sub
            self.env['sale.order']._cron_recurring_create_invoice()
            self.env['sale.order'].sudo()._cron_subscription_expiration()
            self.assertEqual(sub.recurring_monthly, 21)
            self.assertEqual(renewal_so.recurring_monthly, 83)
            self.assertEqual(sub.subscription_state, '5_renewed')
            self.flush_tracking()
        with freeze_time("2021-09-01"), patch.object(type(SaleOrder), '_get_unpaid_subscriptions', lambda x: []):
            renewal_so.order_line.product_uom_qty = 5
            # We update the MRR of the renewed
            self.env['sale.order']._cron_recurring_create_invoice()
            self.env['sale.order']._cron_subscription_expiration()
            self.assertEqual(renewal_so.recurring_monthly, 105)
            # free subscription is not free anymore
            free_renewal_so.order_line.price_unit = 10
            self.flush_tracking()
            self.subscription._cron_update_kpi()
            self.assertEqual(sub.kpi_1month_mrr_delta, 0)
            self.assertEqual(sub.kpi_1month_mrr_percentage, 0)
            self.assertEqual(sub.kpi_3months_mrr_delta, 0)
            self.assertEqual(sub.kpi_3months_mrr_percentage, 0)
            self.assertEqual(renewal_so.kpi_1month_mrr_delta, 22)
            self.assertEqual(round(renewal_so.kpi_1month_mrr_percentage, 2), 0.27)
            self.assertEqual(renewal_so.kpi_3months_mrr_delta, 22)
            self.assertEqual(round(renewal_so.kpi_3months_mrr_percentage, 2), 0.27)

        order_log_ids = sub.order_log_ids.sorted('event_date')
        sub_data = [(log.event_type, log.event_date, log.subscription_state, log.amount_signed, log.recurring_monthly) for log in order_log_ids]
        self.assertEqual(sub_data, [('0_creation', datetime.date(2021, 1, 1), '1_draft', 21, 21),
                                    ('3_transfer', datetime.date(2021, 4, 1), '5_renewed', -21, 0)])
        renew_logs = renewal_so.order_log_ids.sorted(key=lambda log: (log.event_date, log.id))
        renew_data = [(log.event_type, log.event_date, log.subscription_state, log.amount_signed, log.recurring_monthly) for log in renew_logs]
        self.assertEqual(renew_data, [('3_transfer', datetime.date(2021, 4, 1), '2_renewal', 21.0, 21.0),
                                      ('1_expansion', datetime.date(2021, 4, 1), '3_progress', 42.0, 63.0),
                                      ('1_expansion', datetime.date(2021, 4, 20), '3_progress', 20.0, 83.0),
                                      ('1_expansion', datetime.date(2021, 9, 1), '3_progress', 22, 105.0)])
        self.assertEqual(renewal_so.start_date, datetime.date(2021, 5, 1), "the renewal starts on the firsts of May even if transfer occurs on first of April")
        free_log_ids = free_sub.order_log_ids.sorted(key=lambda log: (log.event_date, log.id))
        sub_data = [(log.event_type, log.event_date, log.subscription_state, log.amount_signed, log.recurring_monthly) for log in
                    free_log_ids]
        self.assertEqual(sub_data, [('0_creation', datetime.date(2021, 1, 1), '1_draft', 0, 0),
                                    ('3_transfer', datetime.date(2021, 4, 1), '5_renewed', 0, 0)])
        renew_logs = free_renewal_so.order_log_ids.sorted(key=lambda log: (log.event_date, log.id))
        renew_data = [(log.event_type, log.event_date, log.subscription_state, log.amount_signed, log.recurring_monthly) for log
                      in renew_logs]
        self.assertEqual(renew_data, [('3_transfer', datetime.date(2021, 4, 1), '2_renewal', 0, 0),
                                      ('1_expansion', datetime.date(2021, 9, 1), '3_progress', 20.0, 20.0)])

        future_data = future_sub.order_log_ids.sorted(key=lambda log: (log.event_date, log.id)) # several events aggregated on the same date
        simple_data = [(log.event_type, log.event_date, log.subscription_state, log.amount_signed, log.recurring_monthly) for log
                       in future_data]
        self.assertEqual(simple_data, [('0_creation', datetime.date(2021, 1, 1), '1_draft', 1.0, 1.0),
                                       ('1_expansion', datetime.date(2021, 4, 1), '3_progress', 3.0, 4.0)])
        self.assertEqual(future_sub.start_date, datetime.date(2021, 6, 1), "the start date is in june but the events are recorded as today")

    def test_option_template(self):
        self.product.product_tmpl_id.product_subscription_pricing_ids = [(6, 0, 0)]
        self.env['sale.subscription.pricing'].create({
            'price': 10,
            'plan_id': self.plan_year.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'product_template_id': self.product.product_tmpl_id.id
        })
        other_pricelist = self.env['product.pricelist'].create({
            'name': 'New pricelist',
            'currency_id': self.company.currency_id.id,
        })
        self.env['sale.subscription.pricing'].create({
            'plan_id': self.plan_year.id,
            'pricelist_id': other_pricelist.id,
            'price': 15,
            'product_template_id': self.product.product_tmpl_id.id
        })
        template = self.env['sale.order.template'].create({
            'name': 'Subscription template without discount',
            'is_unlimited': True,
            'note': "This is the template description",
            'plan_id': self.plan_year.id,
            'sale_order_template_line_ids': [Command.create({
                'name': "monthly",
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'product_uom_id': self.product.uom_id.id
            })],
            'sale_order_template_option_ids': [Command.create({
                'name': "line 1",
                'product_id': self.product.id,
                'quantity': 1,
                'uom_id': self.product.uom_id.id,
            })],
        })
        subscription = self.env['sale.order'].create({
            'name': 'TestSubscription',
            'is_subscription': True,
            'partner_id': self.user_portal.partner_id.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'sale_order_template_id': template.id,
        })
        subscription._onchange_sale_order_template_id()
        self.assertEqual(subscription.order_line.price_unit, 10, "The second pricing should be applied")
        self.assertEqual(subscription.sale_order_option_ids.price_unit, 10, "The second pricing should be applied")
        subscription.pricelist_id = other_pricelist.id
        subscription._onchange_sale_order_template_id()
        self.assertEqual(subscription.pricelist_id.id, other_pricelist.id, "The second pricelist should be applied")
        self.assertEqual(subscription.order_line.price_unit, 15, "The second pricing should be applied")
        self.assertEqual(subscription.sale_order_option_ids.price_unit, 15, "The second pricing should be applied")
        # Note: the pricing_id on the line is not saved on the line, but it is used to calculate the price.

    def test_update_subscription_company(self):
        """ Update the taxes of confirmed lines when the subscription company is updated """
        tax_group_1 = self.env['account.tax.group'].create({
            'name': 'Test tax group',
            'tax_receivable_account_id': self.company_data['default_tax_account_receivable'].copy().id,
            'tax_payable_account_id': self.company_data['default_tax_account_payable'].copy().id,
        })
        sale_tax_percentage_incl_1 = self.env['account.tax'].create({
            'name': 'sale_tax_percentage_incl_1',
            'amount': 20.0,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'price_include_override': 'tax_included',
            'tax_group_id': tax_group_1.id,
        })
        other_company_data = self.setup_other_company(name="Company 3")
        tax_group_2 = self.env['account.tax.group'].create({
            'name': 'Test tax group',
            'company_id': other_company_data['company'].id,
            'tax_receivable_account_id': other_company_data['default_tax_account_receivable'].copy().id,
            'tax_payable_account_id': other_company_data['default_tax_account_payable'].copy().id,
        })
        sale_tax_percentage_incl_2 = self.env['account.tax'].create({
            'name': 'sale_tax_percentage_incl_2',
            'amount': 40.0,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'price_include_override': 'tax_included',
            'tax_group_id': tax_group_2.id,
            'company_id': other_company_data['company'].id,
        })
        self.product.write({
            'taxes_id': [(6, 0, [sale_tax_percentage_incl_1.id, sale_tax_percentage_incl_2.id])],
        })
        simple_product = self.product.copy({'recurring_invoice': False})
        simple_so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'company_id': self.company_data['company'].id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': simple_product.id,
                    'product_uom_qty': 2.0,
                    'product_uom': simple_product.uom_id.id,
                    'price_unit': 12,
                })],
        })
        self.assertEqual(simple_so.order_line.tax_id.id, sale_tax_percentage_incl_1.id, 'The so has the first tax')
        subscription = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'company_id': self.company_data['company'].id,
            'plan_id': self.plan_month.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 2.0,
                    'product_uom': self.product.uom_id.id,
                    'price_unit': 12,
                })],
        })
        self.assertEqual(subscription.order_line.tax_id.id, sale_tax_percentage_incl_1.id)
        (simple_so | subscription).write({'company_id': other_company_data['company'].id})
        self.assertEqual(simple_so.order_line.tax_id.id, sale_tax_percentage_incl_2.id, "Simple SO taxes must be recomputed on company change")
        self.assertEqual(subscription.order_line.tax_id.id, sale_tax_percentage_incl_2.id, "Subscription taxes must be recomputed on company change")

    def test_onchange_product_quantity_with_different_currencies(self):
        # onchange_product_quantity compute price unit into the currency of the sale_order pricelist
        # when currency of the product (Gold Coin) is different from subscription pricelist (USD)
        self.subscription.order_line = False
        self.subscription.plan_id = self.plan_month
        self.pricing_month.pricelist_id = self.subscription.pricelist_id
        self.pricing_month.price = 50
        self.sub_product_tmpl.product_subscription_pricing_ids = [(6, 0, self.pricing_month.ids)]
        self.subscription.write({
            'order_line': [(0, 0, {
                'name': 'TestRecurringLine',
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'product_uom': self.product.uom_id.id,
            })],
        })
        self.assertEqual(self.subscription.currency_id.name, 'USD')
        line = self.subscription.order_line
        self.assertEqual(line.price_unit, 50, 'Price unit should not have changed')
        currency = self.other_currency
        self.product.currency_id = currency
        self.pricing_month.currency_id = currency
        line._compute_price_unit()
        conversion_rate = self.env['res.currency']._get_conversion_rate(
            self.product.currency_id,
            self.subscription.currency_id,
            self.product.company_id or self.env.company,
            fields.Date.today())
        self.assertEqual(line.price_unit, self.subscription.currency_id.round(50 * conversion_rate),
                         'Price unit must be converted into the currency of the pricelist (USD)')

    def test_archive_partner_invoice_shipping(self):
        # archived a partner must not remain set on invoicing/shipping address in subscription
        # here, they are set manually on subscription
        self.subscription.action_confirm()
        self.subscription.write({
            'partner_invoice_id': self.partner_a_invoice.id,
            'partner_shipping_id': self.partner_a_shipping.id,
        })
        self.assertEqual(self.partner_a_invoice, self.subscription.partner_invoice_id,
                         "Invoice address should have been set manually on the subscription.")
        self.assertEqual(self.partner_a_shipping, self.subscription.partner_shipping_id,
                         "Delivery address should have been set manually on the subscription.")
        invoice = self.subscription._create_recurring_invoice()
        self.assertEqual(self.partner_a_invoice, invoice.partner_id,
                         "On the invoice, invoice address should be the same as on the subscription.")
        self.assertEqual(self.partner_a_shipping, invoice.partner_shipping_id,
                         "On the invoice, delivery address should be the same as on the subscription.")
        with self.assertRaises(ValidationError):
            self.partner_a.child_ids.write({'active': False})

    def test_subscription_invoice_shipping_address(self):
        """Test to check that subscription invoice first try to use partner_shipping_id and partner_id from
        subscription"""
        partner = self.env['res.partner'].create(
            {'name': 'Stevie Nicks',
             'email': 'sti@fleetwood.mac',
             'company_id': self.env.company.id})

        partner2 = self.env['res.partner'].create(
            {'name': 'Partner 2',
             'email': 'sti@fleetwood.mac',
             'company_id': self.env.company.id})

        subscription = self.env['sale.order'].create({
            'partner_id': partner.id,
            'company_id': self.company_data['company'].id,
            'plan_id': self.plan_month.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 2.0,
                    'product_uom': self.product.uom_id.id,
                    'price_unit': 12,
                })],
        })
        subscription.action_confirm()

        invoice_id = subscription._create_recurring_invoice()
        addr = subscription.partner_id.address_get(['delivery', 'invoice'])
        self.assertEqual(invoice_id.partner_shipping_id.id, addr['invoice'])
        self.assertEqual(invoice_id.partner_id.id, addr['delivery'])

        subscription.write({
            'partner_id': partner.id,
            'partner_shipping_id': partner2.id,
        })
        invoice_id = subscription._create_invoices() # force a new invoice with all lines
        self.assertEqual(invoice_id.partner_shipping_id.id, partner2.id)
        self.assertEqual(invoice_id.partner_id.id, partner.id)

    def test_portal_pay_subscription(self):
        # When portal pays a subscription, a success mail is sent.
        # This calls AccountMove.amount_by_group, which triggers _compute_invoice_taxes_by_group().
        # As this method writes on this field and also reads tax_ids, which portal has no rights to,
        # it might cause some access rights issues. This test checks that no error is raised.
        portal_partner = self.user_portal.partner_id
        portal_partner.country_id = self.env['res.country'].search([('code', '=', 'US')])
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
        })
        provider = self.env['payment.provider'].create({
            'name': 'Test',
        })
        tx = self.env['payment.transaction'].create({
            'amount': 100,
            'provider_id': provider.id,
            'payment_method_id': self.payment_method_id,
            'currency_id': self.env.company.currency_id.id,
            'partner_id': portal_partner.id,
        })

    def test_upsell_date_check(self):
        """ Test what happens when the upsell invoice is not generated before the next invoice cron call """
        self.pricing_year.price = 100
        self.sub_product_tmpl.write({
            'product_subscription_pricing_ids': [(6, 0, self.pricing_year.ids)]
        })
        self.product_tmpl_2.write({
            'product_subscription_pricing_ids': [(6, 0, self.pricing_year_2.ids)]
        })
        self.product_tmpl_3.write({
            'product_subscription_pricing_ids': [(6, 0, self.pricing_year_3.ids)]
        })
        with freeze_time("2022-01-01"):
            sub = self.env['sale.order'].create({
                'name': 'TestSubscription',
                'is_subscription': True,
                'note': "original subscription description",
                'partner_id': self.user_portal.partner_id.id,
                'pricelist_id': self.company_data['default_pricelist'].id,
                'plan_id': self.plan_year.id,
                'order_line': [
                    (0, 0, {
                        'name': self.product.name,
                        'product_id': self.product.id,
                        'product_uom_qty': 1.0,
                        'product_uom': self.product.uom_id.id,
                    }),
                    (0, 0, {
                        'name': self.product2.name,
                        'product_id': self.product2.id,
                        'product_uom_qty': 1.0,
                        'product_uom': self.product.uom_id.id,
                    })
                ]
            })
            sub.action_confirm()
            self.env['sale.order']._cron_recurring_create_invoice()
            inv = sub.invoice_ids
            line_names = inv.invoice_line_ids.mapped('name')
            periods = [n.split('\n')[1] for n in line_names]
            for p in periods:
                self.assertEqual(p, '1 Years 01/01/2022 to 12/31/2022', 'the first year should be invoiced')

        with freeze_time("2022-06-20"):
            action = sub.prepare_upsell_order()
            upsell_so = self.env['sale.order'].browse(action['res_id'])
            upsell_so.order_line[0].product_uom_qty = 2
            upsell_so.order_line = [(0, 0, {
                'product_id': self.product3.id,
                'product_uom_qty': 1.0,
                'product_uom': self.product.uom_id.id,
            })]
            self.assertEqual(upsell_so.next_invoice_date, datetime.date(2023, 1, 1), "The end date is the same than the parent sub")
            discounts = upsell_so.order_line.mapped('discount')
            self.assertEqual(discounts, [46.58, 46.58, 0.0, 46.58], "The discount is almost equal to 50%")
            self.assertEqual(sub.next_invoice_date, datetime.date(2023, 1, 1), 'the first year should be invoiced')
            upsell_so.action_confirm()
            self.assertEqual(upsell_so.next_invoice_date, datetime.date(2023, 1, 1), 'the first year should be invoiced')
            # We trigger the invoice cron before the generation of the upsell invoice
            self.env['sale.order']._cron_recurring_create_invoice()
            inv = sub.invoice_ids.sorted('date')[-1]
            self.assertEqual(inv.date, datetime.date(2022, 1, 1), "No invoice should be created")
        with freeze_time("2022-07-01"):
            discount = upsell_so.order_line.mapped('discount')[0]
            self.assertEqual(discount, 46.58, "The discount is almost equal to 50% and should not be updated for confirmed SO")
            self.assertEqual(upsell_so.order_line.mapped('qty_to_invoice'), [2, 0, 0, 1])
            upsell_invoice = upsell_so._create_invoices()
            inv_line_ids = upsell_invoice.invoice_line_ids.filtered('product_id')
            self.assertEqual(inv_line_ids.mapped('subscription_id'), upsell_so.subscription_id)
            self.assertEqual(inv_line_ids.mapped('deferred_start_date'), [datetime.date(2022, 6, 20), datetime.date(2022, 6, 20)])
            self.assertEqual(inv_line_ids.mapped('deferred_end_date'), [datetime.date(2022, 12, 31), datetime.date(2022, 12, 31)])
            (upsell_so | sub)._cron_recurring_create_invoice()
            inv = sub.invoice_ids.sorted('date')[-1]
            self.assertEqual(inv.date, datetime.date(2022, 1, 1), "No invoice should be created")
            self.assertEqual(upsell_invoice.amount_untaxed, 267.1, "The upsell amount should be equal to 267.1") # (1-0.4658)*(200+300)

        with freeze_time("2023-01-01"):
            (upsell_so | sub)._cron_recurring_create_invoice()
            inv = sub.invoice_ids.sorted('date')[-1]
            self.assertEqual(inv.date, datetime.date(2023, 1, 1), "A new invoice should be created")
            self.assertEqual(inv.amount_untaxed, 800, "A new invoice should be created, all the lines should be invoiced")

    def test_subscription_starts_in_future(self):
        """ Start a subscription in 2 weeks. The next invoice date should be aligned with start_date """
        with freeze_time("2022-05-15"):
            subscription = self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'sale_order_template_id': self.subscription_tmpl.id,
                'plan_id': self.plan_month.id,
                'start_date': '2022-06-01',
                'next_invoice_date': '2022-06-01',
                'order_line': [
                    (0, 0, {
                        'name': self.product.name,
                        'product_id': self.product.id,
                        'product_uom_qty': 1.0,
                        'product_uom': self.product.uom_id.id,
                        'price_unit': 12,
                    })],
            })
            subscription.action_confirm()
            self.assertEqual(subscription.order_line.invoice_status, 'no', "The line qty should be black.")
            self.assertEqual(subscription.start_date, datetime.date(2022, 6, 1), 'Start date should be in the future')
            self.assertEqual(subscription.next_invoice_date, datetime.date(2022, 6, 1), 'next_invoice_date should be in the future')
            subscription._create_invoices()
            with self.assertRaisesRegex(UserError, 'The following recurring orders have draft invoices. Please Confirm them or cancel them'):
                subscription._create_invoices()
            subscription.invoice_ids.filtered(lambda am: am.state == 'draft')._post()
            self.assertEqual(subscription.next_invoice_date, datetime.date(2022, 7, 1),
                             'next_invoice_date should updated')
            subscription._create_invoices()
            subscription.invoice_ids.filtered(lambda am: am.state == 'draft')._post()
            self.assertEqual(subscription.next_invoice_date, datetime.date(2022, 8, 1),
                             'next_invoice_date should updated')

    def test_invoice_status(self):
        with freeze_time("2022-05-15"):
            self.product.invoice_policy = 'delivery'
            subscription_future = self.env['sale.order'].create({
                'name': "subscription future",
                'partner_id': self.partner.id,
                'sale_order_template_id': self.subscription_tmpl.id,
                'plan_id': self.plan_month.id,
                'start_date': '2022-06-01',
                'next_invoice_date': '2022-06-01',
                'order_line': [
                    (0, 0, {
                        'name': self.product.name,
                        'product_id': self.product.id,
                        'product_uom_qty': 1.0,
                        'product_uom': self.product.uom_id.id,
                        'price_unit': 12,
                    })],
            })

            subscription_now = self.env['sale.order'].create({
                'name': "subscription now",
                'partner_id': self.partner.id,
                'sale_order_template_id': self.subscription_tmpl.id,
                'plan_id': self.plan_month.id,
                'start_date': '2022-05-15',
                'next_invoice_date': '2022-05-15',
                'order_line': [
                    (0, 0, {
                        'name': self.product.name,
                        'product_id': self.product.id,
                        'product_uom_qty': 1.0,
                        'product_uom': self.product.uom_id.id,
                        'price_unit': 12,
                    })],
            })

            subscription_past = subscription_now.copy({
                    'name': "subscription past",
                    'start_date': '2022-04-15',
                    'next_invoice_date': '2022-04-15',
            })

            subscriptions = subscription_future + subscription_now + subscription_past
            subscriptions.action_confirm()

            self.assertEqual(subscription_now.next_invoice_date, datetime.date(2022, 6, 15), "Postpaid subscription first invoice should be end of period")
            self.assertEqual(subscription_past.next_invoice_date, datetime.date(2022, 5, 15), "Postpaid subscription first invoice should be end of period")
            self.assertEqual(subscription_future.next_invoice_date, datetime.date(2022, 7, 1), "Postpaid subscription first invoice should be end of period")

            # Nothing delivered, nothing invoiced
            self.assertEqual(subscription_future.order_line.invoice_status, 'no', "The line qty should be black.")
            self.assertEqual(subscription_now.order_line.invoice_status, 'no', "The line qty should be black.")
            subscription_now.order_line.qty_delivered = 1
            self.assertEqual(subscription_now.order_line.invoice_status, 'to invoice', "The line qty should be blue.")

            # Status after delivery
            subscriptions.order_line.qty_delivered = 1
            self.assertEqual(
                subscription_future.order_line.invoice_status, 'no',
                "Nothing to invoice for future subscription yet.",
            )
            for subscription in (subscription_now, subscription_past):
                self.assertEqual(
                    subscription.order_line.invoice_status, 'to invoice',
                    "The line qty should be blue.",
            )
            subscriptions._create_recurring_invoice()
            self.assertEqual(subscription_past.order_line.invoice_status, 'invoiced', "The line qty should be invoiced.")
            self.assertEqual(subscription_now.order_line.invoice_status, 'to invoice', "The line qty should not be invoiced yet.")
            self.assertEqual(subscription_future.order_line.invoice_status, 'no', "The line qty should be black.")

        with freeze_time('2022-06-15'):
            subscriptions._create_recurring_invoice()
            self.assertEqual(subscription_past.order_line.invoice_status, 'invoiced', "The line qty should be invoiced.")
            self.assertEqual(subscription_now.order_line.invoice_status, 'invoiced', "The line qty should not be invoiced yet.")
            self.assertEqual(subscription_future.order_line.invoice_status, 'no', "The line qty should be black.")

    def test_product_pricing_respects_variants(self):
        # create a product with 2 variants
        ProductTemplate = self.env['product.template']
        ProductAttributeVal = self.env['product.attribute.value']
        SaleOrderTemplate = self.env['sale.order.template']
        Pricing = self.env['sale.subscription.pricing']
        product_attribute = self.env['product.attribute'].create({'name': 'Weight'})
        product_attribute_val1 = ProductAttributeVal.create({
            'name': '1kg',
            'attribute_id': product_attribute.id
        })
        product_attribute_val2 = ProductAttributeVal.create({
            'name': '2kg',
            'attribute_id': product_attribute.id
        })
        product = ProductTemplate.create({
            'recurring_invoice': True,
            'type': 'service',
            'name': 'Variant Products',
            'list_price': 5,
        })
        product.attribute_line_ids = [(Command.create({
            'attribute_id': product_attribute.id,
            'value_ids': [Command.set([product_attribute_val1.id, product_attribute_val2.id])],
        }))]

        product_product_1 = product.product_variant_ids[0]
        product_product_2 = product.product_variant_ids[-1]

        # Define extra price for variant without temporal pricing
        self.assertEqual(product_product_2.list_price, 5.0)
        self.assertEqual(product_product_2.lst_price, 5.0)
        product_product_2.product_template_attribute_value_ids.price_extra = 15.0
        self.assertEqual(product_product_2.lst_price, 20.0)
        template = SaleOrderTemplate.create({
            'name': 'Variant Products Plan',
            'plan_id': self.plan_week.id,
            'sale_order_template_line_ids': [Command.create({
                'product_id': product_product_2.id
            })]
        })

        sale_order_form = Form(self.env['sale.order'])
        sale_order_form.partner_id = self.user_portal.partner_id
        sale_order_form.sale_order_template_id = template
        sale_order = sale_order_form.save()
        self.assertEqual(sale_order.order_line.price_unit, 20.0)

        # set pricing for variants. make sure the cheaper one is not for the variant we're testing
        cheaper_pricing = Pricing.create({
            'plan_id': self.plan_week.id,
            'price': 10,
            'product_template_id': product.id,
            'product_variant_ids': [Command.link(product_product_1.id)],
        })

        pricing2 = Pricing.create({
            'plan_id': self.plan_week.id,
            'price': 25,
            'product_template_id': product.id,
            'product_variant_ids': [Command.link(product_product_2.id)],
        })

        product.write({
            'product_subscription_pricing_ids': [Command.set([cheaper_pricing.id, pricing2.id])]
        })

        # create SO with product variant having the most expensive pricing
        sale_order = self.env['sale.order'].create({
            'name': 'TestSubscription',
            'is_subscription': True,
            'partner_id': self.user_portal.partner_id.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'plan_id': self.plan_week.id,
            'order_line': [
                Command.create({
                    'product_id': product_product_2.id,
                    'product_uom_qty': 1
                }),
                Command.create({
                    'product_id': product_product_1[0].id,
                    'product_uom_qty': 1
                })
            ]
        })
        # check that correct pricings are being used
        self.assertEqual(sale_order.order_line[0].price_unit, pricing2.price)
        self.assertEqual(sale_order.order_line[1].price_unit, cheaper_pricing.price)

        # test constraints
        product2 = ProductTemplate.create({
            'recurring_invoice': True,
            'type': 'service',
            'name': 'Variant Products',
            'list_price': 5,
        })

        product2.attribute_line_ids = [(Command.create({
            'attribute_id': product_attribute.id,
            'value_ids': [Command.set([product_attribute_val1.id, product_attribute_val2.id])],
        }))]
        product2_product_2 = product2.product_variant_ids[-1]
        Pricing.create({
            'plan_id': self.plan_week.id,
            'price': 25,
            'product_template_id': product2.id,
            'product_variant_ids': [Command.link(product2_product_2.id)],
        })
        product2_product_1 = product2.product_variant_ids[0]
        product2_product_2 = product2.product_variant_ids[-1]
        with self.assertRaises(UserError):
            Pricing.create({
                'plan_id': self.plan_week.id,
                'price': 32,
                'product_template_id': product2.id,
                'product_variant_ids': [Command.set([product2_product_1.id, product2_product_2.id])],
            })
        with self.assertRaises(UserError):
        # Check constraint without product variants
            Pricing.create({
                'plan_id': self.plan_month.id,
                'price': 32,
                'product_template_id': product2.id,
                'product_variant_ids': [],
            })
            Pricing.create({
                'plan_id': self.plan_month.id,
                'price': 40,
                'product_template_id': product2.id,
                'product_variant_ids': [],
            })

        with self.assertRaises(UserError):
            Pricing.create({
                'plan_id': self.plan_month.id,
                'price': 32,
                'product_template_id': product2.id,
                'product_variant_ids': [],
            })
            Pricing.create({
                'plan_id': self.plan_month.id,
                'price': 88,
                'product_template_id': product2.id,
                'product_variant_ids': [Command.set([product2_product_1.id])],
            })

    def test_upsell_parent_line_id(self):
        with freeze_time("2022-01-01"):
            self.subscription.order_line = False
            self.subscription.write({
                'partner_id': self.partner.id,
                'plan_id': self.plan_month.id,
                'start_date': False,
                'next_invoice_date': False,
                'order_line': [
                    Command.create({
                        'product_id': self.product.id,
                        'name': "month: original",
                        'price_unit': 50,
                        'product_uom_qty': 1,
                    })
                ]
            })
            self.subscription.action_confirm()
            self.subscription._create_recurring_invoice()

        with freeze_time("2022-01-20"):
            action = self.subscription.prepare_upsell_order()
            upsell_so = self.env['sale.order'].browse(action['res_id'])
            # Create new lines that should be aligned with existing ones
            parent_line_id = upsell_so.order_line.parent_line_id
            self.assertEqual(self.subscription.order_line, parent_line_id, "The parent line is the one from the subscription")
            first_line_id = upsell_so.order_line[0] # line 0 is the upsell line
            first_line_id.product_id = self.product2
            self.assertFalse(first_line_id.parent_line_id, "The new line should not have a parent line")
            upsell_so.currency_id = False
            self.assertFalse(first_line_id.parent_line_id, "The new line should not have a parent line even without currency_id")
            self.subscription._compute_pricelist_id() # reset the currency_id
            upsell_so._compute_pricelist_id()
            first_line_id.product_id = self.product
            upsell_so.order_line[0].price_unit = parent_line_id.price_unit + 0.004 # making sure that rounding issue will not affect computed result
            self.assertEqual(upsell_so.order_line[0].parent_line_id, parent_line_id, "The parent line is the one from the subscription")
            self.assertEqual(upsell_so.order_line.parent_line_id, parent_line_id,
                             "The parent line is still the one from the subscription")
            # reset the product to another one to lose the link
            first_line_id.product_id = self.product2
            so_line_vals = [{
                'name': 'Upsell added: 1 month',
                'order_id': upsell_so.id,
                'product_id': self.product3.id,
                'product_uom_qty': 3,
                'product_uom': self.product.uom_id.id,
            }]
            self.env['sale.order.line'].create(so_line_vals)
            self.assertFalse(upsell_so.order_line[2].parent_line_id, "The new line should not have any parent line")
            upsell_so.order_line[2].product_id = self.product3
            upsell_so.order_line[2].product_id = self.product # it should recreate a link
            upsell_so.order_line[0].product_uom_qty = 2
            self.assertEqual(upsell_so.order_line.parent_line_id, parent_line_id,
                             "The parent line is the one from the subscription")
            upsell_so.action_confirm()
            self.assertEqual(self.subscription.order_line[0].product_uom_qty, 4, "The original line qty should be 4 (1 + 3 upsell line 1)")
            self.assertEqual(self.subscription.order_line[1].product_uom_qty, 2, "The new line qty should be 2 (upsell line 0)")

            action = self.subscription.prepare_renewal_order()
            renew_so = self.env['sale.order'].browse(action['res_id'])
            parent_line_id = renew_so.order_line.parent_line_id
            self.assertEqual(self.subscription.order_line, parent_line_id, "The parent line is the one from the subscription")
            renew_so.plan_id = self.plan_year
            self.assertFalse(renew_so.order_line.parent_line_id, "The lines should not have parent lines anymore")

    # test the general behavior of so when the compute_price_unit is called
        self.product_tmpl_4.recurring_invoice = False
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'sale_order_template_id': self.subscription_tmpl.id,
            'plan_id': self.plan_month.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 1.0,
                    'product_uom': self.product.uom_id.id,
                    'price_unit': 12,
                }),
                (0, 0, {
                    'name': self.product5.name, # non recurring product
                    'product_id': self.product5.id,
                    'product_uom_qty': 1.0,
                    'product_uom': self.product5.uom_id.id,
                    'price_unit': 12,
                })
            ],
        })
        self.assertTrue(order.is_subscription)
        self.assertEqual(order.order_line[1].price_unit, 12)
        order.order_line[1].product_id = self.product_tmpl_4.product_variant_id
        self.assertEqual(order.order_line[1].price_unit, 15, "The price should be updated")

    def test_subscription_constraint(self):
        sub = self.subscription.copy()
        self.subscription.plan_id = False
        with self.assertRaisesRegex(UserError, 'Please add a recurring plan on the subscription or remove the recurring product.'):
            self.subscription.action_confirm()
        self.subscription.plan_id = self.plan_month
        self.product.recurring_invoice = False
        self.product2.recurring_invoice = False
        with self.assertRaisesRegex(UserError, 'Please add a recurring product in the subscription or remove the recurring plan.'):
            sub2 = self.subscription.copy()
            sub2.action_confirm()
        # order linked to subscription with recurring product and no recurrence: it was created before the upgrade
        # of sale.subscription into sale.order
        context_no_mail = {'no_reset_password': True, 'mail_create_nosubscribe': True, 'mail_create_nolog': True, }
        delivered_product_tmpl = self.env['product.template'].with_context(context_no_mail).create({
            'name': 'Delivery product',
            'type': 'service',
            'recurring_invoice': False,
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'invoice_policy': 'delivery',
        })
        self.product.recurring_invoice = True
        self.product2.recurring_invoice = True
        sub.action_confirm()

        # Simulate the order without recurrence but linked to a subscription
        order = self.env['sale.order'].create({
            'partner_id': self.user_portal.partner_id.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'subscription_id': sub.id,
            'order_line': [Command.create({
                'name': "recurring line",
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'product_uom': self.product.uom_id.id
                }), Command.create({
                'name': "None recurring line",
                'product_id': delivered_product_tmpl.product_variant_id.id,
                'product_uom_qty': 1,
                'product_uom': delivered_product_tmpl.product_variant_id.uom_id.id
                }),
            ],
        })
        # Make sure the _constraint_subscription_recurrence is not triggered
        self.assertFalse(order.subscription_state)
        order.action_confirm()
        order.write({'order_line': [Command.create({
                    'name': "None recurring line",
                    'product_id': delivered_product_tmpl.product_variant_id.id,
                    'product_uom_qty': 1,
                    'qty_delivered': 3,
                    'product_uom': delivered_product_tmpl.product_variant_id.uom_id.id
        })],})

    def test_multiple_renew(self):
        """ Prevent to confirm several renewal quotation for the same subscription """
        self.subscription.write({'start_date': False, 'next_invoice_date': False})
        self.subscription.action_confirm()
        self.subscription._cron_recurring_create_invoice()
        action = self.subscription.prepare_renewal_order()
        renewal_so_1 = self.env['sale.order'].browse(action['res_id'])
        action = self.subscription.prepare_renewal_order()
        renewal_so_2 = self.env['sale.order'].browse(action['res_id'])
        renewal_so_1.action_confirm()
        self.assertEqual(renewal_so_2.state, 'cancel', 'The other quotation should be canceled')

    def test_next_invoice_date(self):
        with freeze_time("2022-01-20"):
            subscription = self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'sale_order_template_id': self.subscription_tmpl.id,
                'plan_id': self.plan_month.id,
                'order_line': [
                    (0, 0, {
                        'name': self.product.name,
                        'product_id': self.product.id,
                        'product_uom_qty': 1.0,
                        'product_uom': self.product.uom_id.id,
                        'price_unit': 12,
                    })],
            })
            self.assertFalse(subscription.next_invoice_date)
            self.assertFalse(subscription.start_date)

        with freeze_time("2022-02-10"):
            subscription.action_confirm()
            self.assertEqual(subscription.next_invoice_date, datetime.date(2022, 2, 10))
            self.assertEqual(subscription.start_date, datetime.date(2022, 2, 10))

    def test_refund_qty_invoiced(self):
        with freeze_time("2024-09-01"):
            subscription = self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'plan_id': self.plan_month.id,
                'order_line': [
                    (0, 0, {
                        'name': self.product.name,
                        'product_id': self.product.id,
                        'product_uom_qty': 3.0,
                        'product_uom': self.product.uom_id.id,
                        'price_unit': 12,
                    })],
            })
            subscription.action_confirm()
            subscription._create_recurring_invoice()
            self.assertEqual(subscription.order_line.qty_invoiced, 3, "The 3 products should be invoiced")
            subscription._get_invoiced()
            inv = subscription.invoice_ids
            inv.payment_state = 'paid'
            # We refund the invoice
            refund_wizard = self.env['account.move.reversal'].with_context(
                active_model="account.move",
                active_ids=inv.ids).create({
                'reason': 'Test refund tax repartition',
                'journal_id': inv.journal_id.id,
            })
            res = refund_wizard.refund_moves()
            refund_move = self.env['account.move'].browse(res['res_id'])
            self.assertEqual(inv.reversal_move_ids, refund_move, "The initial move should be reversed")
            refund_move._post()
        self.assertEqual(subscription.order_line.qty_invoiced, 0, "The products should not be invoiced")

    def test_discount_parent_line(self):
        with freeze_time("2022-01-01"):
            self.subscription.start_date = False
            self.subscription.next_invoice_date = False
            self.subscription.write({
                'partner_id': self.partner.id,
                'plan_id': self.plan_year.id,
            })
            self.subscription.order_line.discount = 10
            self.subscription.action_confirm()
            self.env['sale.order']._cron_recurring_create_invoice()
        with freeze_time("2022-10-31"):
            self.env['sale.order']._cron_recurring_create_invoice()
            action = self.subscription.prepare_upsell_order()
            upsell_so = self.env['sale.order'].browse(action['res_id'])
            # Discount is 55.61: 83% for pro rata temporis and 10% coming from the parent order
            # price_unit must be multiplied by (1-0.831) * 0,9
            # 100 * [1 - ((1 - 0.831) * 0.9)] = ~84%
            discount = [round(v, 2) for v in upsell_so.order_line.mapped('discount')]
            self.assertEqual(discount, [84.71, 84.71, 0])

    def test_upsell_renewal(self):
        """ Upselling a invoiced renewed order before it started should create a negative discount to invoice the previous
            period. If the renewal has not been invoiced yet, we should only invoice for the previous period.
        """
        with freeze_time("2022-01-01"):
            self.subscription.start_date = False
            self.subscription.next_invoice_date = False
            self.subscription.write({
                'partner_id': self.partner.id,
                'plan_id': self.plan_year.id,
            })
            subscription_2 = self.subscription.copy()
            (self.subscription | subscription_2).action_confirm()
            self.env['sale.order']._cron_recurring_create_invoice()

        with freeze_time("2022-09-10"):
            action = self.subscription.prepare_renewal_order()
            renewal_so = self.env['sale.order'].browse(action['res_id'])
            renewal_so.action_confirm()
            renewal_so._create_invoices()
            renewal_so.order_line.invoice_lines.move_id._post()
            self.assertEqual(renewal_so.start_date, datetime.date(2023, 1, 1))
            self.assertEqual(renewal_so.next_invoice_date, datetime.date(2024, 1, 1))
            action = subscription_2.prepare_renewal_order()
            renewal_so_2 = self.env['sale.order'].browse(action['res_id'])
            renewal_so_2.action_confirm()
            # We don't invoice renewal_so_2 yet to see what happens.
            self.assertEqual(renewal_so_2.start_date, datetime.date(2023, 1, 1))
            self.assertEqual(renewal_so_2.next_invoice_date, datetime.date(2023, 1, 1))
        with freeze_time("2022-10-2"):
            self.env['sale.order']._cron_recurring_create_invoice()
            action = renewal_so.prepare_upsell_order()
            upsell_so = self.env['sale.order'].browse(action['res_id'])
            upsell_so.order_line.filtered(lambda l: not l.display_type).product_uom_qty = 1
            renewal_so_2.next_invoice_date += relativedelta(days=1) # prevent validation error
            action = renewal_so_2.prepare_upsell_order()
            upsell_so_2 = self.env['sale.order'].browse(action['res_id'])
            upsell_so_2.order_line.filtered(lambda l: not l.display_type).product_uom_qty = 1
            parents = upsell_so.order_line.mapped('parent_line_id')
            line_match = [
                renewal_so.order_line[0],
                renewal_so.order_line[1],
            ]
            for idx in range(2):
                self.assertEqual(parents[idx], line_match[idx])
            self.assertEqual(self.subscription.order_line.mapped('product_uom_qty'), [1, 1])
            self.assertEqual(renewal_so.order_line.mapped('product_uom_qty'), [1, 1])
            upsell_so.action_confirm()
            self.assertEqual(upsell_so.order_line.mapped('product_uom_qty'), [1.0, 1.0, 0])
            self.assertEqual(renewal_so.order_line.mapped('product_uom_qty'), [2, 2])
            self.assertEqual(upsell_so.order_line.mapped('discount'), [-24.93, -24.93, 0])
            self.assertEqual(upsell_so.start_date, datetime.date(2022, 10, 2))
            self.assertEqual(upsell_so.next_invoice_date, datetime.date(2024, 1, 1))
            self.assertEqual(upsell_so_2.amount_untaxed, 30.25)
            # upsell_so_2.order_line.flush()
            line = upsell_so_2.order_line.filtered('display_type')
            self.assertEqual(line.display_type, 'line_note')
            self.assertFalse(line.product_uom_qty)
            self.assertFalse(line.price_unit)
            self.assertFalse(line.customer_lead)
            self.assertFalse(line.product_id)

            self.assertEqual(upsell_so_2.order_line.mapped('product_uom_qty'), [1.0, 1.0, 0])
            for discount, value in zip(upsell_so_2.order_line.mapped('discount'), [74.79, 74.79, 0.0]):
                self.assertAlmostEqual(discount, value)
            self.assertEqual(upsell_so_2.next_invoice_date, datetime.date(2023, 1, 2),
                             'We only invoice until the start of the renewal')

    def test_free_product_do_not_invoice(self):
        sub_product_tmpl = self.env['product.template'].create({
            'name': 'Free product',
            'type': 'service',
            'recurring_invoice': True,
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'list_price': 0,
        })

        self.subscription.start_date = False
        self.subscription.next_invoice_date = False
        self.subscription.order_line = [Command.clear()]
        self.subscription.write({
            'partner_id': self.partner.id,
            'plan_id': self.plan_year.id,
            'order_line': [Command.create({
                'name': sub_product_tmpl.name,
                'product_id': sub_product_tmpl.product_variant_id.id,
                'product_uom_qty': 1.0,
                'product_uom': sub_product_tmpl.uom_id.id,
            })]
        })
        self.assertEqual(self.subscription.amount_untaxed, 0, "The price shot be 0")
        self.assertEqual(self.subscription.order_line.price_subtotal, 0, "The price line should be 0")
        self.assertEqual(self.subscription.order_line.invoice_status, 'no', "Nothing to invoice here")

    def test_invoice_done_order(self):
        # Prevent to invoice order in subscription_state != 3_progress
        with freeze_time("2021-01-03"):
            self.subscription.action_confirm()
            self.env['sale.order']._cron_recurring_create_invoice()
            self.assertEqual(self.subscription.invoice_count, 1, "one invoice is created normally")

        with freeze_time("2021-02-03"):
            action = self.subscription.prepare_renewal_order()
            renewal_so = self.env['sale.order'].browse(action['res_id'])
            renewal_so.action_confirm()
            self.assertTrue(self.subscription.locked)
            self.env['sale.order']._cron_recurring_create_invoice()
            self.subscription._cron_recurring_create_invoice()
            self.assertEqual(self.subscription.invoice_count, 2, "locked state don't prevent invoices anymore")

    def test_create_alternative(self):
        self.subscription.next_invoice_date = fields.Date.today() + relativedelta(months=1)
        action = self.subscription.prepare_renewal_order()
        renewal_so = self.env['sale.order'].browse(action['res_id'])
        copy_so = renewal_so.copy()
        alternative_action = renewal_so.create_alternative()
        alternative_so = self.env['sale.order'].browse(alternative_action['res_id'])

        self.assertFalse(copy_so.origin_order_id)
        self.assertFalse(copy_so.subscription_id)
        self.assertEqual(renewal_so.origin_order_id.id, alternative_so.origin_order_id.id)
        self.assertEqual(renewal_so.subscription_id.id, alternative_so.subscription_id.id)

    def test_subscription_state(self):
        # test default value for subscription_state
        sub_1 = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan_month.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 3.0,
                    'product_uom': self.product.uom_id.id,
                    'price_unit': 12,
                })],
        })
        self.assertEqual(sub_1.subscription_state, '1_draft')
        sub_2 = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        self.assertFalse(sub_2.subscription_state, )
        sub_2.plan_id = self.plan_month
        sub_2.order_line = [
            (0, 0, {
                'name': self.product.name,
                'product_id': self.product.id,
                'product_uom_qty': 3.0,
                'product_uom': self.product.uom_id.id,
                'price_unit': 12,
            })]
        self.assertEqual(sub_2.subscription_state, '1_draft')

        sub_2.write({
            'order_line': False,
            'plan_id': False,
        })
        self.assertFalse(sub_2.is_subscription,
            "Subscription quotation without plan_id isn't a subscription")
        self.assertEqual(sub_2.subscription_state, False,
            "Draft subscription quotation without plan_id should lose subscription_state")
        sub_2.action_confirm()
        self.assertFalse(sub_2.subscription_state,
            "SO without subscription plan should lose subscription_state on confirmation")

    def test_free_subscription(self):
        with freeze_time("2023-01-01"):
            pricelist = self.env['product.pricelist'].create({
                'name': 'Pricelist A',
            })
            # We don't want to create invoice when the sum of recurring line is 0
            nr_product = self.env['product.template'].create({
                'name': 'Non recurring product',
                'type': 'service',
                'uom_id': self.product.uom_id.id,
                'list_price': 25,
                'invoice_policy': 'order',
            })
            # nr_product.taxes_id = False # we avoid using taxes in this example
            self.pricing_year.unlink()
            self.pricing_month.price = 25
            self.product2.list_price = -25.0
            # total = 0 & recurring amount = 0
            sub_0_0 = self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'plan_id': self.plan_month.id,
                'pricelist_id': pricelist.id,
                'order_line': [
                    (0, 0, {
                        'name': self.product.name,
                        'product_id': self.product.id,
                        'product_uom_qty': 2.0,
                        'product_uom': self.product.uom_id.id,
                    }),
                    (0, 0, {
                        'name': self.product.name,
                        'product_id': self.product2.id,
                        'product_uom_qty': 2.0,
                        'product_uom': self.product.uom_id.id,
                        'price_unit': -25,
                    })
                ],
            })
            # total = 0 & recurring amount > 0
            sub_0_1 = self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'plan_id': self.plan_month.id,
                'pricelist_id': pricelist.id,
                'order_line': [
                    (0, 0, {
                        'name': self.product.name,
                        'product_id': self.product.id,
                        'product_uom_qty': 2.0,
                        'product_uom': self.product.uom_id.id,
                    }),
                    (0, 0, {
                        'name': nr_product.name,
                        'product_id': nr_product.product_variant_id.id,
                        'product_uom_qty': 2.0,
                        'product_uom': nr_product.uom_id.id,
                        'price_unit': -25,
                    })
                ],
            })
            # total > 0 & recurring amount = 0
            sub_1_0 = self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'plan_id': self.plan_month.id,
                'pricelist_id': pricelist.id,
                'order_line': [
                    (0, 0, {
                        'name': self.product.name,
                        'product_id': self.product.id,
                        'product_uom_qty': 2.0,
                        'product_uom': self.product.uom_id.id,
                    }),
                    (0, 0, {
                        'name': self.product.name,
                        'product_id': self.product2.id,
                        'product_uom_qty': 2.0,
                        'product_uom': self.product2.uom_id.id,
                    }),
                    (0, 0, {
                        'name': nr_product.name,
                        'product_id': nr_product.product_variant_id.id,
                        'product_uom_qty': 2.0,
                        'product_uom': nr_product.uom_id.id,
                    }),
                ],
            })

            sub_negative_recurring = self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'plan_id': self.plan_month.id,
                'pricelist_id': pricelist.id,
                'order_line': [
                    (0, 0, {
                        'name': self.product.name,
                        'product_id': self.product.id,
                        'product_uom_qty': 2.0,
                        'product_uom': self.product.uom_id.id,
                        'price_unit': -30
                    }),
                    (0, 0, {
                        'name': self.product.name,
                        'product_id': self.product2.id,
                        'product_uom_qty': 2.0,
                        'product_uom': self.product2.uom_id.id,
                        'price_unit': -10
                    }),
                ],
            })

            # negative_nonrecurring_sub
            negative_nonrecurring_sub = self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'plan_id': self.plan_month.id,
                'pricelist_id': pricelist.id,
                'order_line': [
                    (0, 0, {
                        'name': self.product.name,
                        'product_id': self.product.id,
                        'product_uom_qty': 2.0,
                        'product_uom': self.product.uom_id.id,
                        'price_unit': -30
                    }),
                    (0, 0, {
                        'name': self.product.name,
                        'product_id': self.product2.id,
                        'product_uom_qty': 2.0,
                        'product_uom': self.product2.uom_id.id,
                        'price_unit': -10
                    }),
                    (0, 0, {
                        'name': nr_product.name,
                        'product_id': nr_product.product_variant_id.id,
                        'product_uom_qty': 4.0,
                        'product_uom': nr_product.uom_id.id,
                    }),
                ],
            })

            (sub_0_0 | sub_0_1 | sub_1_0 | sub_negative_recurring | negative_nonrecurring_sub).order_line.tax_id = False
            (sub_0_0 | sub_0_1 | sub_1_0 | sub_negative_recurring | negative_nonrecurring_sub).action_confirm()

            invoice_0_0 = sub_0_0._create_recurring_invoice()
            self.assertTrue(sub_0_0.currency_id.is_zero(sub_0_0.amount_total))
            self.assertFalse(invoice_0_0, "Free contract with recurring products should not create invoice")
            self.assertEqual(sub_0_0.order_line.mapped('invoice_status'), ['no', 'no'], 'No invoice needed')

            self.assertTrue(sub_0_1.currency_id.is_zero(sub_0_1.amount_total))
            self.assertTrue(sub_0_1.order_line.filtered(lambda l: l.recurring_invoice).price_subtotal > 0)
            invoice_0_1 = sub_0_1._create_recurring_invoice()
            self.assertEqual(invoice_0_1.amount_total, 0, "Total is 0 but an invoice should be created.")
            self.assertEqual(sub_0_1.order_line.mapped('invoice_status'), ['invoiced', 'invoiced'], 'No invoice needed')

            self.assertTrue(sub_1_0.amount_total > 0)
            invoice_1_0 = sub_1_0._create_recurring_invoice()
            self.assertEqual(invoice_1_0.amount_total, 50, "Total is 0 and an invoice should be created.")
            self.assertEqual(sub_1_0.order_line.mapped('invoice_status'), ['no', 'no', 'invoiced'], 'No invoice needed')
            self.assertFalse(all(invoice_1_0.invoice_line_ids.sale_line_ids.product_id.mapped('recurring_invoice')),
                             "The recurring line should be invoiced")

            # Negative subscription will be invoiced by cron the next day
            negative_invoice = sub_negative_recurring._create_recurring_invoice()
            self.assertEqual(sub_negative_recurring.amount_total, -80)
            self.assertFalse(negative_invoice, "Free contract with recurring products should not create invoice")
            self.assertEqual(sub_negative_recurring.order_line.mapped('invoice_status'), ['no', 'no'], 'No invoice needed')

            negative_non_recurring_inv = negative_nonrecurring_sub._create_recurring_invoice()
            self.assertEqual(negative_nonrecurring_sub.amount_total, 20)
            self.assertFalse(negative_non_recurring_inv, "negative contract with non recurring products should not create invoice")
            self.assertEqual(sub_negative_recurring.order_line.mapped('invoice_status'), ['no', 'no'],
                             'No invoice needed')
            self.assertTrue(negative_nonrecurring_sub.payment_exception, "The contract should be in exception")

    def test_subscription_unlink_flow(self):
        """
            Check that the user receives the correct messages when he deletes a subscription.
            Check that the flow to delete a subscription is confirm => close => cancel
        """
        subscription_a = self.env['sale.order'].create({
            'partner_id': self.user_portal.partner_id.id,
            'sale_order_template_id': self.subscription_tmpl.id,
        })
        subscription_b = self.env['sale.order'].create({
            'partner_id': self.user_portal.partner_id.id,
            'sale_order_template_id': self.subscription_tmpl.id,
        })
        subscription_c = self.env['sale.order'].create({
            'partner_id': self.user_portal.partner_id.id,
            'sale_order_template_id': self.subscription_tmpl.id,
        })
        subscription_d = self.env['sale.order'].create({
            'partner_id': self.user_portal.partner_id.id,
            'sale_order_template_id': self.subscription_tmpl.id,
        })
        subscription_a._onchange_sale_order_template_id()
        subscription_b._onchange_sale_order_template_id()
        subscription_c._onchange_sale_order_template_id()
        subscription_d._onchange_sale_order_template_id()
        # Subscription can be deleted if it is in draft
        subscription_a.unlink()
        # Subscription cannot be deleted if it was confirmed once before and it is not closed
        subscription_b.action_confirm()
        with self.assertRaisesRegex(UserError,
            r'You can not delete a confirmed subscription. You must first close and cancel it before you can delete it.'):
            subscription_b.unlink()
        # Subscription cannot be deleted if it is closed
        subscription_c.action_confirm()
        subscription_c.set_close()
        with self.assertRaisesRegex(UserError,
            r'You can not delete a sent quotation or a confirmed sales order. You must first cancel it.'):
            subscription_c.unlink()
        # Subscription can be deleted if it is cancel
        subscription_d.action_confirm()
        subscription_d._action_cancel()
        subscription_d.unlink()

    def test_downpayment_automatic_invoice(self):
        """ Test invoice with a way of downpayment and check downpayment's SO line is created
            and also check a total amount of invoice is equal to a respective sale order's total amount
        """

        context = {
            'active_model': 'sale.order',
            'active_ids': [self.subscription.id],
            'active_id': self.subscription.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }

        with freeze_time('2021-01-03'):
            self.subscription.action_confirm()
            total = self.subscription.amount_total

            downpayment = self.env['sale.advance.payment.inv'].with_context(context).create({
                'advance_payment_method': 'fixed',
                'fixed_amount': 10,
            })
            downpayment.create_invoices()
            downpayment_line = self.subscription.order_line.filtered(lambda l: l.is_downpayment and not l.display_type)
            self.assertEqual(len(downpayment_line), 1, 'SO line downpayment should be created on SO')

            self.assertEqual(self.subscription.invoice_count, 1)
            invoice = self.subscription.invoice_ids.sorted('id')[-1]
            self.assertAlmostEqual(invoice.amount_total, 10, 4, msg='Downpayment price should be 10')
            invoice._post()
            self.assertEqual(self.subscription.next_invoice_date, datetime.date(2021, 1, 3))
            invoice = self.subscription._create_invoices(final=True)  # manual
            self.assertAlmostEqual(invoice.amount_total, total - 10, 4, msg='Downpayment should be deducted from the price')
            invoice._post()
            self.assertEqual(self.subscription.next_invoice_date, datetime.date(2021, 2, 3))

        with freeze_time('2021-02-03'):
            inv = self.subscription._create_recurring_invoice()
            self.assertAlmostEqual(inv.amount_total, total, 4, msg='Downpayment should not be deducted from the price anymore')

    def test_downpayment_manual_invoice(self):
        """ Test invoice with a way of downpayment and check downpayment's SO line is created
            and also check a total amount of invoice is equal to a respective sale order's total amount
        """

        context = {
            'active_model': 'sale.order',
            'active_ids': [self.subscription.id],
            'active_id': self.subscription.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }

        with freeze_time('2021-01-03'):
            self.subscription.action_confirm()
            total = self.subscription.amount_total
            self.assertEqual(total, 23.1)
            downpayment = self.env['sale.advance.payment.inv'].with_context(context).create({
                'advance_payment_method': 'fixed',
                'fixed_amount': 10,
            })
            downpayment.create_invoices()
            downpayment_line = self.subscription.order_line.filtered(lambda l: l.is_downpayment and not l.display_type)
            self.assertEqual(len(downpayment_line), 1, 'SO line downpayment should be created on SO')

            self.assertEqual(self.subscription.invoice_count, 1)
            invoice = self.subscription.invoice_ids.sorted('id')[-1]
            self.assertAlmostEqual(invoice.amount_total, 10, 4, msg='Downpayment price should be 10')
            invoice._post()

            invoice = self.subscription._create_invoices(final=True)
            invoice._post()

            self.assertAlmostEqual(invoice.amount_total, total - 10, 4, msg='Downpayment should be deducted from the price')

        with freeze_time('2021-02-03'):
            invoice = self.subscription._create_invoices(final=True)
            self.assertAlmostEqual(invoice.amount_total, total, 4,
                                   msg='Downpayment should not be deducted from the price anymore')

    def test_upsell_with_different_currency_throws_error(self):
        pricelist_eur = self.env['product.pricelist'].create({
            'name': 'Euro pricelist',
            'currency_id': self.env.ref('base.EUR').id,
        })
        self.subscription.action_confirm()
        self.subscription._create_recurring_invoice()
        action = self.subscription.prepare_upsell_order()
        upsell_so = self.env['sale.order'].browse(action['res_id'])
        with self.assertRaises(ValidationError):
            upsell_so.pricelist_id = pricelist_eur.id

    def test_modify_discount_on_upsell(self):
        """
        Makes sure that you can edit the discount on an upsell, save it, and then confirm it,
        and it doesn't change/reset to default
        """
        with freeze_time("2022-10-31"):
            self.subscription.action_confirm()
            self.env['sale.order']._cron_recurring_create_invoice()
            action = self.subscription.prepare_upsell_order()
            upsell_so = self.env['sale.order'].browse(action['res_id'])
            upsell_line = upsell_so.order_line.filtered(lambda l: not l.display_type)[0]
            old_discount = upsell_line.discount
            new_discount = 42
            self.assertTrue(old_discount != new_discount,
                            "These discounts should be different, change the value of new_discount if this test fail.")
            upsell_line.write({'discount': new_discount})
            self.assertEqual(upsell_line.discount, new_discount,
                             "The line should have the new discount written.")
            upsell_so.action_confirm()
            self.assertEqual(upsell_line.discount, new_discount,
                             "The line should have the new discount after confirmation.")

    def test_subscription_change_partner(self):
        # This test check that action_confirm is only called once on SO when the partner is updated.
        sub = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan_month.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 3.0,
                    'product_uom': self.product.uom_id.id,
                    'price_unit': 12,
                })],
        })
        self.assertEqual(sub.partner_id, self.partner)
        sub.action_confirm()
        self.assertEqual(sub.subscription_state, '3_progress')
        action_confirm_orig = SaleOrder.action_confirm
        self.call_count = 0
        self1 = self
        def _action_confirm_mock(*args, **kwargs):
            self1.call_count += 1
            return action_confirm_orig(*args, **kwargs)

        with patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder.action_confirm', _action_confirm_mock):
            sub.partner_id = self.partner_a_invoice.id
            self.assertEqual(sub.partner_id, self.partner_a_invoice)
            self.assertEqual(self.call_count, 0)

    def test_reopen(self):
        with freeze_time("2023-03-01"):
            sub = self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'plan_id': self.plan_month.id,
                'order_line': [
                    (0, 0, {
                        'name': self.product.name,
                        'product_id': self.product.id,
                        'product_uom_qty': 3.0,
                        'product_uom': self.product.uom_id.id,
                    })],
            })
            sub_mrr_change = sub.copy()
            self.flush_tracking()
            (sub | sub_mrr_change).action_confirm()
            self.flush_tracking()
        with freeze_time("2023-03-02"):
            sub_mrr_change.order_line.product_uom_qty = 10
            sub.order_line.product_uom_qty = 10
            self.flush_tracking()
        with freeze_time("2023-03-05"):
            close_reason_id = self.env.ref('sale_subscription.close_reason_1').id
            (sub | sub_mrr_change).set_close(close_reason_id=close_reason_id)
            self.flush_tracking()
            # We change the quantity after cloing to see what happens to the logs when we reopen
            sub_mrr_change.order_line.product_uom_qty = 6
            self.flush_tracking()
            (sub | sub_mrr_change).set_close()
            self.flush_tracking()
            churn_log = sub.order_log_ids.sorted('event_date')[-1]
            self.assertEqual((churn_log.event_type, churn_log.amount_signed, churn_log.recurring_monthly),
                             ('2_churn', -10, 0), "The churn log should be created")
        with freeze_time("2023-03-10"):
            (sub | sub_mrr_change).reopen_order()
            self.flush_tracking()
            order_log_ids = sub.order_log_ids.sorted('event_date')
            sub_data = [
                (log.event_type, log.event_date, log.subscription_state, log.amount_signed, log.recurring_monthly)
                for log in order_log_ids]
            self.assertEqual(sub_data, [('0_creation', datetime.date(2023, 3, 1), '1_draft', 3.0, 3.0),
                                        ('1_expansion', datetime.date(2023, 3, 2), '3_progress', 7.0, 10.0)])
            order_log_ids = sub_mrr_change.order_log_ids.sorted('event_date')
            sub_data = [
                (log.event_type, log.event_date, log.subscription_state, log.amount_signed, log.recurring_monthly)
                for log in order_log_ids]

            self.assertEqual(sub_data, [('0_creation', datetime.date(2023, 3, 1), '1_draft', 3.0, 3.0),
                                        ('1_expansion', datetime.date(2023, 3, 2), '3_progress', 7.0, 10.0),
                                        ('15_contraction', datetime.date(2023, 3, 10), '3_progress', -4.0, 6.0)])

    def test_cancel_constraint(self):
        sub_progress = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan_month.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 3.0,
                    'product_uom': self.product.uom_id.id,
                })],
        })
        sub_paused = sub_progress.copy()
        sub_progress_no_invoice = sub_progress.copy()
        with freeze_time('2022-02-02'):
            (sub_progress | sub_paused | sub_progress_no_invoice).action_confirm()
            (sub_progress | sub_paused)._create_recurring_invoice()
        sub_paused.subscription_state = '4_paused'
        sub_progress_no_invoice._action_cancel()
        self.assertEqual(sub_progress_no_invoice.state, 'cancel')
        with self.assertRaises(ValidationError):
            # You cannot cancel a subscription that has been invoiced
            sub_paused._action_cancel()
        sub_paused.subscription_state = '6_churn'
        with self.assertRaises(ValidationError):
            sub_paused._action_cancel()
        sub_paused.invoice_ids.button_cancel()
        self.assertEqual(sub_paused.state, 'sale')
        sub_progress.subscription_state = '6_churn'
        with self.assertRaises(ValidationError):
            sub_progress._action_cancel()
        sub_progress.invoice_ids.button_cancel()
        sub_progress._action_cancel()
        sub_progress.set_open()
        action = sub_progress.prepare_renewal_order()
        renewal_so = self.env['sale.order'].browse(action['res_id'])
        renewal_so.action_confirm()
        self.assertEqual(sub_progress.subscription_state, '5_renewed', "sub was renewed")
        inv = renewal_so._create_invoices()
        inv._post()
        self.assertEqual(renewal_so.subscription_state, '3_progress')
        action = renewal_so.prepare_renewal_order()
        renewal_so2 = self.env['sale.order'].browse(action['res_id'])
        renewal_so2.action_confirm()
        self.assertEqual(renewal_so2.subscription_state, '3_progress')
        self.assertEqual(renewal_so.subscription_state, '5_renewed')
        self.assertEqual(renewal_so.state, 'sale')
        self.assertTrue(renewal_so.locked)
        with self.assertRaises(ValidationError):
            # You cannot cancel a subscription that has been invoiced
            renewal_so._action_cancel()

    def test_renew_different_currency(self):
        with freeze_time("2023-03-28"):
            self.product.product_subscription_pricing_ids.unlink()
            default_pricelist = self.company_data['default_pricelist']
            other_currency = self.env.ref('base.EUR')
            other_currency.action_unarchive()
            other_pricelist = self.env['product.pricelist'].create({
                'name': 'Test Pricelist (EUR)',
                'currency_id': other_currency.id,
            })
            other_currency.write({
                'rate_ids': [(0, 0, {
                    'rate': 20,
                })]
            })
            pricing_month_1 = self.env['sale.subscription.pricing'].create({
                'plan_id': self.plan_month.id,
                'price': 10,
                'pricelist_id': default_pricelist.id,
            })
            pricing_month_2 = self.env['sale.subscription.pricing'].create({
                'plan_id': self.plan_month.id,
                'price': 200,
                'pricelist_id': other_pricelist.id,
            })
            sub_product_tmpl = self.env['product.template'].create({
                'name': 'BaseTestProduct',
                'type': 'service',
                'recurring_invoice': True,
                'uom_id': self.env.ref('uom.product_uom_unit').id,
                'product_subscription_pricing_ids': [(6, 0, (pricing_month_1 | pricing_month_2).ids)]
            })
            subscription_tmpl = self.env['sale.order.template'].create({
                'name': 'Subscription template without discount',
                'duration_unit': 'year',
                'is_unlimited': False,
                'duration_value': 2,
                'note': "This is the template description",
                'plan_id': self.plan_month.copy(default={'auto_close_limit': 5}).id,
                'sale_order_template_line_ids': [Command.create({
                    'name': "Product 1",
                    'product_id': sub_product_tmpl.product_variant_id.id,
                    'product_uom_qty': 1,
                    'product_uom_id': sub_product_tmpl.product_variant_id.uom_id.id,
                })]
            })
            sub = self.subscription.create({
                'name': 'Company1 - Currency1',
                'sale_order_template_id': subscription_tmpl.id,
                'partner_id': self.user_portal.partner_id.id,
                'currency_id': self.company.currency_id.id,
                'plan_id': self.plan_month.id,
                'order_line': [(0, 0, {
                    'name': "Product 1",
                    'product_id': sub_product_tmpl.product_variant_id.id,
                    'product_uom_qty': 1,
                    'product_uom': sub_product_tmpl.uom_id.id
                })]
            })
            sub.pricelist_id = default_pricelist.id
            sub._onchange_sale_order_template_id() # recompute the pricings
            self.flush_tracking()
            sub.action_confirm()
            self.assertEqual(sub.recurring_monthly, 10)
            self.flush_tracking()
            self.env['sale.order']._cron_recurring_create_invoice()
            self.flush_tracking()

        with freeze_time("2023-04-29"):
            action = sub.prepare_renewal_order()
            renewal_so = self.env['sale.order'].browse(action['res_id'])
            renewal_so.write({
                'pricelist_id': other_pricelist.id,
            })
            renewal_so._onchange_sale_order_template_id()
            renewal_so.order_line.product_uom_qty = 3
            self.flush_tracking()
            renewal_so.action_confirm()
            self.flush_tracking()
            self.env['sale.order']._cron_recurring_create_invoice()
            order_log_ids = sub.order_log_ids.sorted(key=lambda log: (log.event_date, log.id))
            sub_data = [(log.event_type, log.event_date, log.amount_signed, log.recurring_monthly, log.currency_id)
                        for log in order_log_ids]
            self.assertEqual(sub_data,
                             [('0_creation', datetime.date(2023, 3, 28), 10, 10, default_pricelist.currency_id),
                              ('3_transfer', datetime.date(2023, 4, 29), -10, 0, default_pricelist.currency_id)
                              ])

            renew_logs = renewal_so.order_log_ids.sorted(key=lambda log: (log.event_date, log.id))
            renew_data = [(log.event_type, log.event_date, log.amount_signed, log.recurring_monthly, log.currency_id)
                          for log in renew_logs]
            self.assertEqual(renew_data, [
                ('3_transfer', datetime.date(2023, 4, 29), 200, 200, other_currency),
                ('1_expansion', datetime.date(2023, 4, 29), 400, 600, other_currency)
            ])

    def test_protected_close_reason(self):
        close_reason = self.env['sale.order.close.reason'].create({
            'name': 'Super close reason',
            'is_protected': True,
        })

        with self.assertRaises(AccessError):
            close_reason.unlink()

    def test_close_reason_end_of_contract(self):
        sub = self.subscription
        end_date = datetime.date(2022, 6, 20)
        sub.end_date = end_date
        with freeze_time(end_date):
            sub.action_confirm()
            sub._create_recurring_invoice()
        self.assertEqual(sub.close_reason_id.id, self.env.ref('sale_subscription.close_reason_end_of_contract').id)

    def test_sale_subscription_post_invoice(self):
        """ Test that the post invoice hook is correctly called
        """
        def patched_reset(self):
            self.name = "Called"

        with patch('odoo.addons.sale_subscription.models.sale_order_line.SaleOrderLine._reset_subscription_quantity_post_invoice', patched_reset), freeze_time("2021-01-01"):
            sub = self.subscription
            sub.action_confirm()
            self.env['sale.order']._cron_recurring_create_invoice()
            self.assertEqual(sub.order_line.mapped('name'), ['Called']*2)

    def test_close_reason_automatic_renewal_failed(self):
        sub = self.subscription
        sub.plan_id.auto_close_limit = 1
        start_date = datetime.date(2022, 6, 20)
        sub.start_date = start_date
        sub.payment_token_id = self.payment_token.id
        sub.action_confirm()

        with freeze_time(start_date + relativedelta(days=sub.plan_id.auto_close_limit)):
            with patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder._do_payment', wraps=self._mock_subscription_do_payment_rejected):
                sub._create_recurring_invoice()
        self.assertEqual(sub.close_reason_id.id, self.env.ref('sale_subscription.close_reason_auto_close_limit_reached').id)

    def test_renewal_churn(self):
        # Test what we expect when we
        # 1) create a renewal quote
        # 2) close the parent
        # 3) confirm the renewal
        SaleOrder = self.env["sale.order"]
        with freeze_time("2021-01-01"), patch.object(type(SaleOrder), '_get_unpaid_subscriptions', lambda x: []):
            # so creation with mail tracking
            context_mail = {'tracking_disable': False}
            sub = self.env['sale.order'].with_context(context_mail).create({
                'name': 'Parent Sub',
                'is_subscription': True,
                'note': "original subscription description",
                'partner_id': self.user_portal.partner_id.id,
                'sale_order_template_id': self.subscription_tmpl.id,
            })
            sub._onchange_sale_order_template_id()
            # Same product for both lines
            sub.order_line.product_uom_qty = 1
            self.flush_tracking()
            sub.action_confirm()
            sub._create_recurring_invoice()
            self.flush_tracking()
            action = sub.with_context(tracking_disable=False).prepare_renewal_order()
            renewal_so = self.env['sale.order'].browse(action['res_id'])
            renewal_so = renewal_so.with_context(tracking_disable=False)
            renewal_so.order_line.product_uom_qty = 3
            renewal_so.name = "Renewal"
            self.flush_tracking()
            sub.set_close()
            self.flush_tracking()
            renewal_so.action_confirm()
            self.flush_tracking()

            order_log_ids = sub.order_log_ids.sorted('id')
            sub_data = [(log.event_type, log.event_date, log.subscription_state, log.amount_signed, log.recurring_monthly)
                        for log in order_log_ids]
            self.assertEqual(sub_data,
                             [('0_creation', datetime.date(2021, 1, 1), '1_draft', 21.0, 21.0),
                              ('3_transfer', datetime.date(2021, 1, 1), '5_renewed', -21.0, 0.0)])
            order_log_ids = renewal_so.order_log_ids.sorted('id')
            renew_data = [(log.event_type, log.event_date, log.subscription_state, log.amount_signed, log.recurring_monthly) for log in order_log_ids]
            self.assertEqual(renew_data, [('3_transfer', datetime.date(2021, 1, 1), '2_renewal', 21, 21),
                                          ('1_expansion', datetime.date(2021, 1, 1), '3_progress', 42.0, 63)])

    def test_subscription_pricelist_discount(self):
        context_no_mail = {'no_reset_password': True, 'mail_create_nosubscribe': True, 'mail_create_nolog': True, }
        pricelist = self.company_data['default_pricelist']
        pricelist.item_ids.create({
            'pricelist_id': pricelist.id,
            'compute_price': 'percentage',
            'percent_price': 50,
        })
        sub = self.env["sale.order"].with_context(**context_no_mail).create({
            'name': 'TestSubscription',
            'is_subscription': True,
            'plan_id': self.plan_month.id,
            'note': "original subscription description",
            'partner_id': self.user_portal.partner_id.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'sale_order_template_id': self.subscription_tmpl.id,
        })
        sub._onchange_sale_order_template_id()
        sub.order_line.create({
            'order_id': sub.id,
            'product_id': self.product_a.id, # non-subscription product
        })
        self.assertEqual(sub.order_line.mapped('discount'), [0, 0, 50],
            "Regular pricelist discounts should't affect temporal items.")
        sub.order_line.discount = 20
        self.assertEqual(sub.order_line.mapped('discount'), [20, 20, 20])
        sub.action_confirm()
        self.assertEqual(sub.order_line.mapped('discount'), [20, 20, 20],
             "Discounts should not be reset on confirmation.")

    def test_non_subscription_pricelist_discount(self):
        context_no_mail = {'no_reset_password': True, 'mail_create_nosubscribe': True, 'mail_create_nolog': True, }
        pricelist = self.company_data['default_pricelist']
        pricelist.item_ids.create({
            'pricelist_id': pricelist.id,
            'compute_price': 'percentage',
            'percent_price': 50,
        })
        so = self.env["sale.order"].with_context(**context_no_mail).create({
            'name': 'TestNonSubscription',
            'is_subscription': False,
            'partner_id': self.user_portal.partner_id.id,
            'pricelist_id': pricelist.id,
            'order_line': [(0, 0, {'product_id': self.product_a.id})],
        })
        self.assertEqual(so.order_line.discount, 50)
        so.order_line.discount = 20
        self.assertEqual(so.order_line.discount, 20)
        so.action_confirm()
        self.assertEqual(so.order_line.discount, 20,
             "Discounts should not be reset on confirmation.")

    def test_churn_log_renew(self):
        """ Test the behavior of the logs when we confirm a renewal quote after the parent has been closed.
        """
        self.flush_tracking()
        with freeze_time("2024-01-22 08:00:00"):
            today = datetime.date.today()
            context_mail = {'tracking_disable': False}
            sub = self.env['sale.order'].with_context(context_mail).create({
                'name': 'TestSubscription',
                'is_subscription': True,
                'note': "original subscription description",
                'partner_id': self.user_portal.partner_id.id,
                'pricelist_id': self.company_data['default_pricelist'].id,
                'sale_order_template_id': self.subscription_tmpl.id,
            })
            sub._onchange_sale_order_template_id()
            # Same product for both lines
            sub.order_line.product_uom_qty = 1
            self.flush_tracking()
            sub.action_confirm()
            self.flush_tracking()
            sub.order_line.product_uom_qty = 2
            self.flush_tracking()

            self.env['sale.order'].with_context(tracking_disable=False)._cron_recurring_create_invoice()
            self.flush_tracking()
            action = sub.with_context(tracking_disable=False).prepare_renewal_order()
            renewal_so = self.env['sale.order'].browse(action['res_id'])
            renewal_so = renewal_so.with_context(tracking_disable=False)
            renewal_so.order_line.product_uom_qty = 3
            renewal_so.name = "Renewal"
            self.flush_tracking()
            sub.set_close()
            self.flush_tracking()
            renewal_so.action_confirm()
            self.flush_tracking()
            # Most of the time, the renewal invoice is created by the salesman
            # before the renewal start date
            renewal_invoices = renewal_so._create_invoices()
            renewal_invoices._post()
            order_log_ids = sub.order_log_ids.sorted('id')
            sub_data = [(log.event_type, log.event_date, log.subscription_state, log.amount_signed, log.recurring_monthly) for log in
                        order_log_ids]
            self.assertEqual(sub_data, [('0_creation', today, '1_draft', 21, 21),
                                        ('1_expansion', today, '3_progress', 21.0, 42.0),
                                        ('3_transfer', today, '5_renewed', -42, 0)])
            renew_logs = renewal_so.order_log_ids.sorted('id')
            renew_data = [(log.event_type, log.event_date, log.subscription_state, log.amount_signed, log.recurring_monthly) for log
                        in renew_logs]
            self.assertEqual(sub.subscription_state, '5_renewed')
            self.assertEqual(renew_data, [('3_transfer', today, '2_renewal', 42, 42),
                                        ('1_expansion', today, '3_progress', 21.0, 63.0)])

    def test_paused_resume_logs(self):
        self.flush_tracking()
        today = datetime.date.today()
        context_mail = {'tracking_disable': False}
        sub = self.env['sale.order'].with_context(context_mail).create({
            'name': 'TestSubscription',
            'is_subscription': True,
            'note': "original subscription description",
            'partner_id': self.user_portal.partner_id.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'sale_order_template_id': self.subscription_tmpl.id,
        })
        sub._onchange_sale_order_template_id()
        self.flush_tracking()
        sub.action_confirm()
        self.flush_tracking()
        sub.pause_subscription()
        self.flush_tracking()
        sub.pause_subscription()
        self.flush_tracking()
        sub.resume_subscription()
        self.flush_tracking()
        order_log_ids = sub.order_log_ids.sorted('id')
        sub_data = [(log.event_type, log.event_date, log.subscription_state, log.amount_signed, log.recurring_monthly)
                    for log in order_log_ids]
        self.assertEqual(sub_data, [('0_creation', today, '1_draft', 21, 21)])

    def test_renewal_different_period(self):
        """ When a renewal quote is negotiated for more than a month, we need to update the start date of the
        renewal quote if the parent is prolonged.
        """
        with freeze_time("2023-01-1"):
            # We reset the renew alert to make sure it will run with freezetime
            self.subscription.write({'start_date': False, 'next_invoice_date': False})
            self.subscription._onchange_sale_order_template_id()
            self.assertEqual(self.subscription.plan_id, self.plan_month)
            self.subscription.action_confirm()
            self.subscription._create_recurring_invoice()
            action = self.subscription.with_context(tracking_disable=False).prepare_renewal_order()
            renewal_so = self.env['sale.order'].browse(action['res_id'])
            renewal_so = renewal_so.with_context(tracking_disable=False)
            renewal_so.order_line.product_uom_qty = 3
            renewal_so.name = "Renewal"
            renewal_so.plan_id = self.plan_year
            self.assertEqual(self.subscription.next_invoice_date, datetime.date(2023, 2, 1))
            self.assertEqual(renewal_so.start_date, datetime.date(2023, 2, 1))
            self.assertEqual(renewal_so.next_invoice_date, datetime.date(2023, 2, 1))
        with freeze_time("2023-02-01"):
            # the new invoice is created and validated by the customer
            self.subscription._create_recurring_invoice()
            self.assertEqual(self.subscription.next_invoice_date, datetime.date(2023, 3, 1))
            self.assertEqual(renewal_so.start_date, datetime.date(2023, 3, 1))
            self.assertEqual(renewal_so.next_invoice_date, datetime.date(2023, 3, 1))

    def test_close_reason_wizard(self):
        self.subscription._onchange_sale_order_template_id()
        self.subscription.action_confirm()
        self.subscription._create_recurring_invoice()
        new_reason = self.env['sale.order.close.reason'].create({'name': "test reason"})
        wiz = self.env['sale.subscription.close.reason.wizard'].with_context(active_id=self.subscription.id).create({
            'close_reason_id': new_reason.id
        })
        wiz.set_close()
        self.assertEqual(self.subscription.close_reason_id, new_reason, "The reason should be saved on the order")

    def test_renew_with_different_currency(self):
        pricelist_eur = self.env['product.pricelist'].create({
            'name': 'Euro pricelist',
            'currency_id': self.env.ref('base.EUR').id,
        })
        self.pricing_month.write({'pricelist_id': self.subscription.pricelist_id.id, 'price': 42})
        pricing_month_eur = self.env['sale.subscription.pricing'].create({
            'plan_id': self.plan_month.id,
            'pricelist_id': pricelist_eur.id,
            'price': 420
        })
        self.sub_product_tmpl.product_subscription_pricing_ids = [Command.link(pricing_month_eur.id)]

        self.subscription_tmpl.sale_order_template_line_ids[1].unlink()
        self.subscription.order_line.product_id.taxes_id = [Command.clear()]
        self.subscription._onchange_sale_order_template_id()
        self.subscription.action_confirm()
        self.assertEqual(self.subscription.amount_total, 42)
        self.subscription._create_recurring_invoice()
        action = self.subscription.prepare_renewal_order()
        renew_so = self.env['sale.order'].browse(action['res_id'])
        self.assertEqual(renew_so.amount_total, 42)
        renew_so.pricelist_id = pricelist_eur.id
        renew_so.action_update_prices()
        self.assertEqual(renew_so.amount_total, 420)

    def test_renew_pricelist_currency_update(self):
        """
        Assert that after renewing a subscription, changing the pricelist
        to another one will recompute the order lines pricings.
        """
        with freeze_time("2023-04-04"):
            default_pricelist = self.company_data['default_pricelist']
            other_currency = self.env.ref('base.EUR')
            other_currency.action_unarchive()
            other_pricelist = self.env['product.pricelist'].create({
                'name': 'Test Pricelist (EUR)',
                'currency_id': other_currency.id,
            })
            other_currency.rate_ids = [Command.create({'rate': 20})]
            pricing_month_1_usd = self.env['sale.subscription.pricing'].create({
                'plan_id': self.plan_month.id,
                'price': 100,
                'pricelist_id': default_pricelist.id,
            })
            pricing_month_2_eur = self.env['sale.subscription.pricing'].create({
                'plan_id': self.plan_month.id,
                'price': 200,
                'pricelist_id': other_pricelist.id,
            })
            sub_product_tmpl = self.env['product.template'].create({
                'name': 'BaseTestProduct',
                'type': 'service',
                'recurring_invoice': True,
                'uom_id': self.env.ref('uom.product_uom_unit').id,
                'product_subscription_pricing_ids': [Command.set((pricing_month_1_usd | pricing_month_2_eur).ids)]
            })
            sub = self.subscription.create({
                'name': 'Company1 - Currency1',
                'partner_id': self.user_portal.partner_id.id,
                'currency_id': self.company.currency_id.id,
                'plan_id': self.plan_month.id,
                'pricelist_id': default_pricelist.id,
                'order_line': [Command.create({
                    'name': "Product 1",
                    'product_id': sub_product_tmpl.product_variant_id.id,
                    'product_uom_qty': 1,
                    'product_uom': sub_product_tmpl.uom_id.id
                })]
            })
            sub.action_confirm()
            self.flush_tracking()

            # Assert that order line was created with correct pricing and currency.
            self.assertEqual(sub.order_line[0].price_unit, 100.0, "Subscription product's order line must be created with default pricelist pricing (USD) having the price unit as 100.0.")
            self.assertEqual(sub.order_line[0].order_id.currency_id.id, self.company.currency_id.id, "Subscription product's order line must be created with the default company currency (USD).")
            self.assertEqual(sub.pricelist_id.id, default_pricelist.id, "Subscription must be created with the default company pricelist (in USD).")
            self.env['sale.order']._cron_recurring_create_invoice()
            self.flush_tracking()

        with freeze_time("2023-04-05"):
            action = sub.prepare_renewal_order()
            renewal_so = self.env['sale.order'].browse(action['res_id'])

            # Assert that parent_line_id is saved in renewed subscription.
            self.assertEqual(renewal_so.order_line[0].parent_line_id.id, sub.order_line[0].id, "The parent line of the order line should have been saved after subscription renewal.")
            renewal_so.pricelist_id = other_pricelist.id

            # Computes the updated price unit through 'Update Prices' button.
            renewal_so.action_update_prices()
            renewal_so.invalidate_recordset()

            # Assert that updated pricing has the correct currency, price_unit and pricelist.
            self.assertEqual(renewal_so.pricelist_id.id, other_pricelist.id, "Pricelist must update to the new one (in EUR) after performing a manual update.")
            self.assertEqual(renewal_so.order_line[0].currency_id.id, other_currency.id, "Order line's currency should have been updated from USD to EUR after changing the pricelist.")
            self.assertEqual(renewal_so.order_line[0].price_unit, 200.0, "Order line's price unit must update to 200.0 according to the new pricelist pricing (in EUR).")

            # Update prices button removes the parent_line_id of order lines to recalculate pricings.
            self.assertFalse(renewal_so.order_line[0].parent_line_id, "Parent order line should not exist anymore after updating prices, it was intentionally deleted for forcing price recalculation.")

    def test_plan_field_automatic_price_unit_update(self):
        """
        Assert that after changing the 'Recurrence' field of a subscription,
        prices will recompute automatically ONLY for subscription products.
        """
        default_pricelist = self.company_data['default_pricelist']
        other_currency = self.env.ref('base.EUR')
        other_currency.action_unarchive()
        pricing_month_1_eur = self.env['sale.subscription.pricing'].create({
            'plan_id': self.plan_month.id,
            'price': 100,
            'pricelist_id': default_pricelist.id,
        })
        pricing_year_1_eur = self.env['sale.subscription.pricing'].create({
            'plan_id': self.plan_year.id,
            'price': 1000,
            'pricelist_id': default_pricelist.id,
        })
        simple_product = self.product.copy({'recurring_invoice': False})
        simple_product_order_line = {
            'name': self.product.name,
            'product_id': simple_product.id,
            'product_uom_qty': 2.0,
            'product_uom': simple_product.uom_id.id
        }
        sub_product_tmpl = self.env['product.template'].create({
            'name': 'BaseTestProduct',
            'type': 'service',
            'recurring_invoice': True,
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'product_subscription_pricing_ids': [Command.set((pricing_month_1_eur | pricing_year_1_eur).ids)]
        })
        sub_product_order_line = {
            'name': "Product 1",
            'product_id': sub_product_tmpl.product_variant_id.id,
            'product_uom_qty': 1,
            'product_uom': sub_product_tmpl.uom_id.id
        }
        sub = self.subscription.create({
            'name': 'Company1 - Currency1',
            'partner_id': self.user_portal.partner_id.id,
            'currency_id': self.company.currency_id.id,
            'plan_id': self.plan_month.id,
            'pricelist_id': default_pricelist.id,
            'order_line': [
                Command.create(sub_product_order_line),
                Command.create(simple_product_order_line)
            ]
        })
        sub.action_confirm()
        self.flush_tracking()
        # Assert that order lines were created with correct pricing and currency.
        self.assertEqual(sub.order_line[0].price_unit, 100.0, "Subscription product's order line should have its price unit as 100.0 according to the 'Monthly' pricing during creation.")
        self.assertEqual(sub.order_line[1].price_unit, 50.0, "Simple product's order line must have its default price unit of 50.0 during creation.")

        # Change the 'Recurrence' field and check if price unit updated ONLY in the recurring order line.
        sub.plan_id = self.plan_year.id
        self.assertEqual(sub.order_line[0].price_unit, 1000.0, "Subscription product's order line must have its unit price as 1000.0 after 'Recurrence' is changed to 'Yearly'.")
        self.assertEqual(sub.order_line[1].price_unit, 50.0, "Simple product's order line must not update its price unit, it must be kept as 50.0 during the 'Recurrence' field changes.")

        # Update price of normal product and check if it is updated in recurrence (it should not!)
        sub.order_line[1].product_id.list_price = 70.0
        self.assertEqual(sub.order_line[1].price_unit, 50.0, "Simple product's price unit must be kept as 50.0 even though the product price was updated outside the subscription scope.")
        self.env['sale.order']._cron_recurring_create_invoice()
        self.flush_tracking()

        # Change again the 'Recurrence' field and check if the price unit update during renewal was done in the recurring order line.
        action = sub.prepare_renewal_order()
        renewal_so = self.env['sale.order'].browse(action['res_id'])
        renewal_so.plan_id = self.plan_month.id
        self.assertEqual(renewal_so.order_line[0].price_unit, 100.0, "Subscription product's order line must have its unit price as 100.0 after 'Recurrence' is changed to 'Monthly'.")

        # Change the 'Recurrence' field to yearly and ensure that price was updated accordingly for the subscription product.
        renewal_so.plan_id = self.plan_year.id
        self.assertEqual(renewal_so.order_line[0].price_unit, 1000.0, "Subscription product's order line must have its unit price as 1000.0 after 'Recurrence' is changed to 'Yearly'.")

    def test_new_plan_id_optional_products_price_update(self):
        """
        Assert that after changing the 'Recurrence' field of a subscription, prices will be recomputed
        for Optional Products with time-based pricing linked to the subscription template.
        """
        # Define a subscription template with a optional product having time-based pricing.
        self.product.product_tmpl_id.product_subscription_pricing_ids.unlink()
        self.env['sale.subscription.pricing'].create({
            'price': 150,
            'plan_id': self.plan_month.id,
            'product_template_id': self.product.product_tmpl_id.id
        })
        self.env['sale.subscription.pricing'].create({
            'price': 1000,
            'plan_id': self.plan_year.id,
            'product_template_id': self.product.product_tmpl_id.id
        })
        template = self.env['sale.order.template'].create({
            'name': 'Subscription template with time-based pricing on optional product',
            'note': "This is the template description",
            'plan_id': self.plan_year.id,
            'sale_order_template_line_ids': [Command.create({
                'name': "monthly",
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'product_uom_id': self.product.uom_id.id
            })],
            'sale_order_template_option_ids': [Command.create({
                'name': "line 1",
                'product_id': self.product.id,
                'quantity': 1,
                'uom_id': self.product.uom_id.id,
            })],
        })
        # Create the subscription based on the subscription template.
        subscription = self.env['sale.order'].create({
            'name': 'TestSubscription',
            'is_subscription': True,
            'partner_id': self.user_portal.partner_id.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'plan_id': self.plan_month.id,
            'sale_order_template_id': template.id,
        })
        subscription._onchange_sale_order_template_id()

        # Assert that optional product has its price updated after changing the 'recurrence' field.
        self.assertEqual(subscription.sale_order_option_ids.price_unit, 150, "The price unit for the optional product must be 150.0 due to 'Monthly' value in the 'Recurrence' field.")
        subscription.plan_id = self.plan_year.id
        self.assertEqual(subscription.sale_order_option_ids.price_unit, 1000, "The price unit for the optional product must update to 1000.0 after changing the 'Recurrence' field to 'Yearly'.")

    def test_qty_invoiced_after_revert(self):
        """ Test invoice quantity is correctly updated after a revert
            with modify move creation
        """
        self.subscription.write({
            'order_line': [
                Command.clear(),
                Command.create({
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 2.0,
                    'product_uom': self.product.uom_id.id,
                    'price_unit': 12,
                })],
        })
        self.subscription.action_confirm()
        self.env['sale.order']._cron_recurring_create_invoice()
        invoice = self.subscription.invoice_ids
        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=invoice.ids).create({
            'reason': 'no reason',
            'journal_id': invoice.journal_id.id,
        })
        reversal = move_reversal.modify_moves()
        new_move = self.env['account.move'].browse(reversal['res_id'])
        new_move.action_post()
        self.assertEqual(self.subscription.order_line.qty_invoiced, 2.0, "Invoiced quantity on the order line is not correct")

    def test_negative_subscription(self):
        nr_product = self.env['product.template'].create({
                'name': 'Non recurring product',
                'type': 'service',
                'uom_id': self.product.uom_id.id,
                'list_price': 25,
                'invoice_policy': 'order',
            })
            # nr_product.taxes_id = False # we avoid using taxes in this example
        self.pricing_year.unlink()
        self.pricing_month.price = 25
        self.product2.list_price = -25.0
        self.product.product_subscription_pricing_ids.unlink()
        self.sub_product_tmpl.list_price = -30
        self.product_tmpl_2.list_price = -10
        self.product2.product_subscription_pricing_ids.unlink()
        sub_negative_recurring = self.env['sale.order'].create({
            'name': 'sub_negative_recurring (1)',
            'partner_id': self.partner.id,
            'plan_id': self.plan_month.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 2.0,
                    'product_uom': self.product.uom_id.id,
                }),
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product2.id,
                    'product_uom_qty': 2.0,
                    'product_uom': self.product2.uom_id.id,
                }),
            ],
        })
        negative_nonrecurring_sub = self.env['sale.order'].create({
            'name': 'negative_nonrecurring_sub (2)',
            'partner_id': self.partner.id,
            'plan_id': self.plan_month.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 2.0,
                    'product_uom': self.product.uom_id.id,
                }),
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product2.id,
                    'product_uom_qty': 2.0,
                    'product_uom': self.product2.uom_id.id,
                }),
                (0, 0, {
                    'name': nr_product.name,
                    'product_id': nr_product.product_variant_id.id,
                    'product_uom_qty': 4.0,
                    'product_uom': nr_product.uom_id.id,
                }),
            ],
        })
        all_subs = sub_negative_recurring | negative_nonrecurring_sub
        with freeze_time("2023-01-01"):
            self.flush_tracking()
            all_subs.write({'start_date': False, 'next_invoice_date': False})
            all_subs.action_confirm()
            self.flush_tracking()
            all_subs.next_invoice_date = datetime.datetime(2023, 2, 1)
            self.flush_tracking()
        with freeze_time("2023-02-01"):
            sub_negative_recurring.order_line.product_uom_qty = 6 # update quantity
            negative_nonrecurring_sub.order_line[1].product_uom_qty = 4
            self.flush_tracking()
            all_subs._create_recurring_invoice() # should not create any invoice because negative
            self.flush_tracking()

        with freeze_time("2023-02-15"):
            action = sub_negative_recurring.prepare_renewal_order()
            renewal_so1 = self.env['sale.order'].browse(action['res_id'])
            renewal_so1.name = 'renewal_so1'
            renewal_so1.order_line.product_uom_qty = 12
            action = negative_nonrecurring_sub.prepare_renewal_order()
            renewal_so2 = self.env['sale.order'].browse(action['res_id'])
            renewal_so2.name = 'renewal_so2'
            renewal_so2.order_line[1].product_uom_qty = 8
            self.flush_tracking()
            all_subs |= renewal_so1|renewal_so2
            (renewal_so1|renewal_so2).action_confirm()
            self.flush_tracking()
        with freeze_time("2023-03-01"):
            (all_subs)._create_recurring_invoice()
            self.flush_tracking()
        with freeze_time("2023-04-01"):
            self.flush_tracking()
            self.assertFalse(renewal_so2.invoice_ids, "no invoice should have been created")
            close_reason_id = self.env.ref('sale_subscription.close_reason_1').id
            renewal_so2.set_close(close_reason_id=close_reason_id)
            self.flush_tracking()
            renewal_so2.reopen_order()
            self.flush_tracking()


        order_log_ids = self.env['sale.order.log'].search([('order_id', 'in', (sub_negative_recurring|renewal_so1).ids)], order='id')
        sub_data1 = [(log.event_type, log.event_date, log.subscription_state, log.amount_signed, log.recurring_monthly)
                    for log in order_log_ids]
        self.assertEqual(sub_data1, [('0_creation', datetime.date(2023, 1, 1), '1_draft', 0, 0),
                                     ('3_transfer', datetime.date(2023, 2, 15), '5_renewed', 0, 0),
                                     ('3_transfer', datetime.date(2023, 2, 15), '2_renewal', 0, 0)])

        order_log_ids = self.env['sale.order.log'].search([('order_id', 'in', (negative_nonrecurring_sub|renewal_so2).ids)], order='id')
        sub_data2 = [(log.event_type, log.event_date, log.subscription_state, log.amount_signed, log.recurring_monthly)
                    for log in order_log_ids]
        self.assertEqual(sub_data2, [('0_creation', datetime.date(2023, 1, 1), '1_draft', 0, 0),
                                     ('3_transfer', datetime.date(2023, 2, 15), '5_renewed', 0, 0),
                                     ('3_transfer', datetime.date(2023, 2, 15), '2_renewal', 0, 0)])
        self.assertEqual(renewal_so1.recurring_monthly, -480, "The MRR field is negative but it does not produce logs")
        self.assertEqual(renewal_so2.recurring_monthly, -140, "The MRR field is negative but it does not produce logs")

    def test_reopen_parent_child_canceled(self):
        """ Renew a contract a few time, invoice it, check the computed amount of invoices
        Then cancel a non invoiced renewal and see if it restart the parent
        """
        with freeze_time("2023-11-03"):
            self.flush_tracking()
            self.subscription.write({
                    'start_date': False,
                    'next_invoice_date': False,
                    'partner_invoice_id': self.partner_a_invoice.id,
                    'partner_shipping_id': self.partner_a_shipping.id,
                })
            self.subscription.action_confirm()
            self.flush_tracking()
            self.subscription._create_recurring_invoice()
            self.assertEqual(self.subscription.invoice_count, 1)
            self.flush_tracking()

        with freeze_time("2023-12-03"):
            action = self.subscription.prepare_renewal_order()
            renewal_so = self.env['sale.order'].browse(action['res_id'])
            self.flush_tracking()
            renewal_so.action_confirm()
            self.flush_tracking()
            renewal_so._create_recurring_invoice()
            self.assertEqual(renewal_so.invoice_count, 2)
            self.flush_tracking()
        with freeze_time("2024-01-03"):
            action = renewal_so.prepare_renewal_order()
            renewal_so2 = self.env['sale.order'].browse(action['res_id'])
            self.flush_tracking()
            renewal_so2.action_confirm()
            self.flush_tracking()

            self.assertEqual(renewal_so.subscription_state, '5_renewed')
            self.assertEqual(renewal_so2.subscription_state, '3_progress')

            renewal_so2._action_cancel()
            renewal_so.end_date = False

            self.flush_tracking()
            self.assertEqual(renewal_so.subscription_state, '3_progress')
            self.assertFalse(renewal_so2.subscription_state)
        with freeze_time("2024-02-03"):
            renewal_so._create_recurring_invoice()
            self.flush_tracking()
            (self.subscription | renewal_so | renewal_so2).invalidate_recordset(['invoice_ids', 'invoice_count'])
            self.assertEqual(renewal_so.invoice_count, 3, "All contracts have the same count")
            self.assertEqual(renewal_so2.invoice_count, 3, "All contracts have the same count")
            self.assertEqual(self.subscription.invoice_count, 3, "All contracts have the same count")

    def test_renew_simple_user(self):
        user_sales_salesman = self.company_data['default_user_salesman']
        self.assertTrue(user_sales_salesman.has_group('sales_team.group_sale_salesman'))
        subscription = self.env['sale.order'].with_user(user_sales_salesman).create({
                'partner_id': self.partner_a.id,
                'company_id': self.company_data['company'].id,
                'plan_id': self.plan_month.id,
                'order_line': [
                    (0, 0, {
                        'name': self.product.name,
                        'product_id': self.product.id,
                        'product_uom_qty': 2.0,
                        'product_uom': self.product.uom_id.id,
                        'price_unit': 12,
                    })],
        })
        subscription.with_user(user_sales_salesman).action_confirm()
        self.env['sale.order']._cron_recurring_create_invoice()
        action = subscription.with_user(user_sales_salesman).prepare_renewal_order()
        renewal_so = self.env['sale.order'].browse(action['res_id'])
        renewal_so.with_user(user_sales_salesman).action_confirm()

    def test_alert_next_activity(self):
        ''' Ensure correct functionality of sale order creation. This function validates the process of creating sale orders.
        Previously, there was an issue of infinite recursion during alert creation.
        The recursion occurred because calling _configure_alerts led to a call to write, which in turn would call _configure_alerts again.
        '''
        self.env['sale.order.alert'].create([{
            'name': 'Test Alert',
            'trigger_condition': 'on_create_or_write',
            'subscription_state_from': '3_progress',
            'subscription_state': '6_churn',
            'action': 'next_activity',
        }])

    def test_recurring_plan_price_recalc_adding_optional_product(self):
        """
        Test that when an optional recurring product is added to a subscription sale order that its price unit is
        correctly recalculated after subsequent edits to the order's recurring plan
        """
        self.sub_product_tmpl.write({'product_subscription_pricing_ids': [Command.set(self.pricing_year.id)]})
        product_a = self.sub_product_tmpl.product_variant_id
        product_a.list_price = 1.0

        self.product_tmpl_2.write({'product_subscription_pricing_ids': [Command.set(self.pricing_year_2.id)]})
        product_b = self.product_tmpl_2.product_variant_id
        product_b.list_price = 1.0

        sale_order = self.env['sale.order'].create({
            'plan_id': self.plan_month.id,
            'partner_id': self.user_portal.partner_id.id,
            'company_id': self.company_data['company'].id,
            'order_line': [
                Command.create({'product_id': product_a.id}),
                Command.create({'product_id': product_b.id})
            ],
            'sale_order_option_ids': [Command.create({'product_id': product_b.id})],
        })

        sale_order.sale_order_option_ids.line_id = sale_order.order_line[1].id
        sale_order.write({'plan_id': self.plan_year})

        self.assertEqual(sale_order.order_line[1].price_unit, 200.0)

    def test_upsell_total_qty(self):
        self.subscription.action_confirm()
        self.subscription._create_recurring_invoice()
        next_invoice_date = self.subscription.next_invoice_date
        action = self.subscription.prepare_upsell_order()
        upsell_so = self.env['sale.order'].browse(action['res_id'])
        upsell_so.order_line.filtered(lambda l: not l.display_type).product_uom_qty = 2
        upsell_so.action_confirm()
        for line in upsell_so.order_line.filtered(lambda l: not l.display_type):
            self.assertEqual(line.upsell_total, 3)
        invoice = upsell_so._create_invoices()
        # simulate wrong historical data
        invoice.invoice_line_ids.filtered('deferred_end_date').deferred_end_date = next_invoice_date + relativedelta(days=5)
        invoice._post()
        self.assertEqual(self.subscription.next_invoice_date, next_invoice_date, "The next Invoice date should not be updated by an upsell")

    def test_sale_subscription_upsell_does_not_copy_non_recurring_products(self):
        nr_product = self.env['product.template'].create({
            'name': 'Non recurring product',
            'type': 'service',
            'uom_id': self.product.uom_id.id,
            'list_price': 25,
            'invoice_policy': 'order',
        })
        self.subscription.action_confirm()
        self.subscription._create_recurring_invoice()

        action = self.subscription.prepare_upsell_order()
        upsell_so = self.env['sale.order'].browse(action['res_id'])
        upsell_so.order_line = [(6, 0, self.env['sale.order.line'].create({
            'name': nr_product.name,
            'order_id': upsell_so.id,
            'product_id': nr_product.product_variant_id.id,
            'product_uom_qty': 1,
        }).ids)]

        upsell_so._confirm_upsell()
        self.assertEqual(len(upsell_so.order_line), 1)
        self.assertEqual(len(self.subscription.order_line), 2)
        self.assertEqual(upsell_so.order_line.name, nr_product.name)
        self.assertFalse(nr_product in self.subscription.order_line.product_template_id)

    def test_upsell_descriptions(self):
        """ On invoicing upsells, only subscription-based items should display a duration. """
        with freeze_time("2022-10-31"):
            self.subscription.action_confirm()
            self.env['sale.order']._cron_recurring_create_invoice()

            action = self.subscription.prepare_upsell_order()
            upsell_so = self.env['sale.order'].browse(action['res_id'])
            upsell_so.order_line = [Command.create({'product_id': self.product_a.id})]
            upsell_so.order_line.filtered('product_id').product_uom_qty = 1
            upsell_so.action_confirm()
            invoice = upsell_so._create_invoices()

            self.assertEqual(len(invoice.invoice_line_ids), 4)
            for line in invoice.invoice_line_ids:
                name = line.name
                sol_name = line.sale_line_ids.name
                if line.sale_line_ids.recurring_invoice:
                    self.assertIn("1 Month", name, "Sub lines require duration")
                else:
                    self.assertEqual(name, sol_name, "Non-sub lines shouldn't add duration")

    def test_change_recurrence_plan_with_option(self):
        """
        A recurring order with a line for a recurring produce and a sale order option for a recurring product yields an
            exception when changing the recurring plan via Form, preventing the plan from being changed
        """
        order_1 = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({'product_id': self.product.id})],
        })
        self.env['sale.order.option'].create({
            'order_id': order_1.id,
            'product_id': self.product.id,
        })

        with Form(order_1) as order_form:
            order_form.plan_id = self.plan_week

        self.assertEqual(order_1.plan_id, self.plan_week)

    def test_subscription_lock_settings(self):
        """ The settings to automatically lock SO upon confirmation
        should never be applied to subscription orders. """
        self.env.user.groups_id += self.env.ref('sale.group_auto_done_setting')
        self.subscription.write({'start_date': False, 'next_invoice_date': False})
        self.subscription.action_confirm()
        self.assertEqual(self.subscription.state, 'sale')

    def test_web_read_group_sale_subscription(self):
        self.subscription.action_confirm()
        SaleSubscription = self.env['sale.order']
        domain = ['&', ['subscription_state', 'not in', ['2_renewal', '5_renewed', '7_upsell', False]], '|', ['subscription_state', '=', '3_progress'], ['subscription_state', '=', '4_paused']]
        fields = ['rating_last_value:sum', 'recurring_total:sum']
        groupby = ['subscription_state']
        result = SaleSubscription.web_read_group(domain, fields, groupby)

        self.assertEqual(result['groups'][0]['subscription_state_count'], 1)
        self.assertEqual(result['groups'][0]['subscription_state'], '3_progress')
        self.assertEqual(result['groups'][1]['subscription_state_count'], 0)
        self.assertEqual(result['groups'][1]['subscription_state'], '4_paused')

    def test_subscription_confirm_update_salesperson_on_partner(self):
        """ confirming sale order should update the salesperson on related partner. """
        self.assertFalse(self.subscription.partner_id.user_id)
        self.subscription.action_confirm()
        self.assertEqual(self.subscription.user_id, self.subscription.partner_id.user_id, "Salesperson on subscription and partner should be same")

    def test_subscription_salesperson_changes_partner_saleperson(self):
        """ changing salesperson on confirmed subscription should change salesperson on related partner. """
        self.subscription.action_confirm()
        self.assertEqual(self.subscription.user_id, self.subscription.partner_id.user_id, "Salesperson on subscription and partner should be same")

        new_user = self.env['res.users'].create({
            'name': 'new user',
            'login': 'new',
            'email': 'new@test.com',
        })
        self.subscription.write({'user_id': new_user.id})
        self.assertEqual(new_user, self.subscription.partner_id.user_id, "Subscription's salesperson should be updated on partner's salesperson")
        self.assertIn(new_user.partner_id.id, self.subscription.message_follower_ids.partner_id.ids)

        new_user_2 = self.env['res.users'].create({
            'name': 'new user 2',
            'login': 'new2',
            'email': 'new2@test.com',
        })
        self.subscription.write({'user_id': new_user_2.id})
        self.assertEqual(new_user_2, self.subscription.partner_id.user_id, "Subscription's salesperson should be updated on partner's salesperson")
        self.assertNotIn(new_user.partner_id.id, self.subscription.message_follower_ids.partner_id.ids, "Old salesperson should removed from message followers")

    def test_recurring_invoice_count(self):
        sub = self.env['sale.order'].create({
            'name': 'TestSubscription',
            'is_subscription': True,
            'plan_id': self.plan_month.id,
            'partner_id': self.user_portal.partner_id.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'order_line': [(0, 0, {'product_id': self.product.id})],
        })
        sub.action_confirm()
        inv = self.env['sale.order']._cron_recurring_create_invoice()
        new_invoice = inv.copy()
        self.assertEqual(sub.invoice_ids, inv | new_invoice)

    def test_recurring_invoice_cron_trigger(self):
        """
        Test that the cron job to create recurring invoices is triggered only
        when count of subscriptions to invoice is greater than batch size.
        """
        SaleOrder = self.env['sale.order']
        with freeze_time("2024-05-01"):
            subscriptions = []
            for i in range (4):
                subscriptions.append(SaleOrder.create({
                    'name': 'require payment %s' % str(i),
                    'is_subscription': True,
                    'partner_id': self.user_portal.partner_id.id,
                    'pricelist_id': self.company_data['default_pricelist'].id,
                    'plan_id': self.plan_month.id,
                    'order_line': [
                        Command.create({
                            'product_id': self.product.id,
                            'product_uom_qty': 1
                        }),
                    ],
                    'require_payment': True,
                }))
                subscriptions[-1].action_confirm()

            # no subscription should be invoiced which means we should not trigger cron job
            all_subscriptions, need_cron_trigger = SaleOrder._recurring_invoice_get_subscriptions(batch_size=3)
            self.assertFalse(need_cron_trigger)
            self.assertFalse(all_subscriptions)

    def test_recurring_invoice_cron_batch(self):
        """
        Check all subscriptions are processed by the cron when there are more than batch_size of them and
        some of them are filtered by _get_subscriptions_to_invoice.
        """
        SaleOrder = self.env['sale.order']
        subscriptions_to_invoice = self.env['sale.order']

        for i in range(5):
            sub_to_invoice = SaleOrder.create({
                'name': 'Payment not required',
                'is_subscription': True,
                'partner_id': self.user_portal.partner_id.id,
                'pricelist_id': self.company_data['default_pricelist'].id,
                'plan_id': self.plan_month.id,
                'order_line': [
                    Command.create({
                        'product_id': self.product.id,
                        'product_uom_qty': 1
                    }),
                ],
                'require_payment': False,
            })
            sub_to_invoice.action_confirm()
            subscriptions_to_invoice += sub_to_invoice

        for i in range(2):
            sub = SaleOrder.create({
                'name': 'require payment %s' % str(i),
                'is_subscription': True,
                'partner_id': self.user_portal.partner_id.id,
                'pricelist_id': self.company_data['default_pricelist'].id,
                'plan_id': self.plan_month.id,
                'order_line': [
                    Command.create({
                        'product_id': self.product.id,
                        'product_uom_qty': 1
                    }),
                ],
                'require_payment': True,
            })
            sub.action_confirm()

        SaleOrder._create_recurring_invoice(batch_size=3)

        self.assertTrue(all(sub.invoice_ids))

    def test_amount_to_invoice_with_subscription(self):
        one_shot_product_tmpl = self.env['product.template'].create({
            'name': 'One shot product',
            'type': 'service',
            'recurring_invoice': False,
            'uom_id': self.env.ref('uom.product_uom_unit').id,
        })
        one_shot_product = one_shot_product_tmpl.product_variant_id
        one_shot_product.write({
            'taxes_id': [Command.set([self.tax_10.id])],
            'property_account_income_id': self.account_income.id,
        })

        with freeze_time('2024-01-01'):
            # Create a monthly subscription
            sub = self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'sale_order_template_id': self.subscription_tmpl.id,
                'is_subscription': True,
                'plan_id': self.plan_month.id,
                'order_line': [
                    # Recurring product
                    Command.create({
                        'name': self.product.name,
                        'product_id': self.product.id,
                        'product_uom_qty': 1.0,
                        'product_uom': self.product.uom_id.id,
                        'price_unit': 100,
                    }),
                    # Non-recurring product
                    Command.create({
                        'name': one_shot_product.name,
                        'product_id': one_shot_product.id,
                        'product_uom_qty': 2.0,
                        'product_uom': one_shot_product.uom_id.id,
                        'price_unit': 50,
                    }),
                ]
            })
            sub.action_confirm()

            # Nothing has been invoiced --> total amount is due
            self.assertEqual(sub.amount_to_invoice, 220.0)
            posted_invoice_lines = sub.order_line.invoice_lines.filtered(lambda line: line.parent_state == 'posted')
            self.assertEqual(sum(posted_invoice_lines.mapped('price_total')), 0.0)

            sub._create_recurring_invoice()

            # First invoice created, which includes both recurring and non-recurring products
            self.assertEqual(sub.amount_to_invoice, 0.0)
            posted_invoice_lines = sub.order_line.invoice_lines.filtered(lambda line: line.parent_state == 'posted')
            self.assertEqual(sum(posted_invoice_lines.mapped('price_total')), 220.0)

        with freeze_time('2024-02-01'):
            # Invalidate the cache to force the re-computation of the un-invoiced balance with the new date.
            # It should be equal to the recurring amount, i.e. 110.0
            sub.invalidate_recordset(['amount_to_invoice'])
            sub.order_line.invalidate_recordset(['amount_to_invoice'])
            self.assertEqual(sub.amount_to_invoice, 110.0)

            sub._create_recurring_invoice()

            # Second invoice created, which only includes the recurring product
            self.assertEqual(sub.amount_to_invoice, 0.0)
            posted_invoice_lines = sub.order_line.invoice_lines.filtered(lambda line: line.parent_state == 'posted')
            self.assertEqual(sum(posted_invoice_lines.mapped('price_total')), 330.0)

    def test_subscription_online_payment_no_token(self):
        with freeze_time("2024-05-01"):
            self.subscription.require_payment = True
            self.subscription.action_confirm()
            self.env['sale.order']._cron_recurring_create_invoice()
            # it should not create a invoice
            self.assertEqual(self.subscription.invoice_count, 0)

        with self.mock_mail_gateway():
            with freeze_time("2024-04-17"):
                self.env['sale.order']._cron_recurring_send_payment_reminder()
                # it will send payment reminder mail to customer before 14
                self.assertEqual(len(self._new_mails), 1)
                self.assertEqual(self.subscription.last_reminder_date, fields.Date.today())
            with freeze_time("2024-04-24"):
                self.env['sale.order']._cron_recurring_send_payment_reminder()
                # it will send payment reminder mail to customer before 7 days
                self.assertEqual(len(self._new_mails), 2)
                self.assertEqual(self.subscription.last_reminder_date, fields.Date.today())
            with freeze_time("2024-04-29"):
                self.env['sale.order']._cron_recurring_send_payment_reminder()
                # it will send payment reminder mail to customer before 2 days
                self.assertEqual(len(self._new_mails), 3)
                self.assertEqual(self.subscription.last_reminder_date, fields.Date.today())
            with freeze_time("2024-05-01"):
                self.env['sale.order']._cron_recurring_send_payment_reminder()
                # it will send payment reminder mail to customer
                self.assertEqual(len(self._new_mails), 4)
                self.assertEqual(self.subscription.last_reminder_date, fields.Date.today())
            with freeze_time("2024-05-03"):
                self.env['sale.order']._cron_recurring_send_payment_reminder()
                # it will send payment reminder mail to customer
                self.assertEqual(len(self._new_mails), 5)
                self.assertEqual(self.subscription.last_reminder_date, fields.Date.today())
            with freeze_time("2024-05-08"):
                self.env['sale.order']._cron_recurring_send_payment_reminder()
                # it will send payment reminder mail to customer
                self.assertEqual(len(self._new_mails), 6)
                self.assertEqual(self.subscription.last_reminder_date, fields.Date.today())
            with freeze_time("2024-05-15"):
                self.env['sale.order']._cron_recurring_send_payment_reminder()
                # it will send payment reminder mail to customer
                self.assertEqual(len(self._new_mails), 7)
                self.assertEqual(self.subscription.last_reminder_date, fields.Date.today())
            with freeze_time("2024-05-16"):
                self.env['sale.order']._cron_recurring_send_payment_reminder()
                # it should close the subscription
                self.assertEqual(self.subscription.subscription_state, '6_churn')

    def test_cron_recurring_send_payment_reminder_failure(self):
        with freeze_time("2024-05-01"):
            self.subscription.require_payment = True
            self.subscription.action_confirm()
        with self.mock_mail_gateway():
            with freeze_time("2024-04-17"):
                self.env.ref('sale_subscription.send_payment_reminder').lastcall = False
                self.env['sale.order']._cron_recurring_send_payment_reminder()
                self.assertEqual(self.subscription.last_reminder_date, fields.Date.today())
                self.assertEqual(len(self._new_mails), 1)
            with freeze_time("2024-04-25"):
                # we will set lastcall of cron to 23/4.
                # if cron run on 24/4 then it should send reminder on that day but we skip 24/4 and run the cron on 25/4
                # it should send reminder mail on 25/4 as the cron failed to run on 24/4.
                self.env.ref('sale_subscription.send_payment_reminder').lastcall = datetime.datetime(2024, 4, 23, 0, 0, 0)
                self.env['sale.order']._cron_recurring_send_payment_reminder()
                self.assertEqual(self.subscription.last_reminder_date, fields.Date.today())
                self.assertEqual(len(self._new_mails), 2)

    def test_subscription_online_payment_with_token(self):
        with freeze_time("2024-05-01"):
            self.subscription.require_payment = True
            self.subscription.payment_token_id = self.payment_token.id
            self.subscription.end_date = datetime.date(2024, 8, 1)
            self.subscription.action_confirm()
            with patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder._do_payment', wraps=self._mock_subscription_do_payment):
                self.env['sale.order']._cron_recurring_create_invoice()
                self.subscription.transaction_ids._get_last()._post_process()
            # it should create an invoice
            self.assertEqual(self.subscription.invoice_count, 1)
        with freeze_time("2024-06-01"):
            with patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder._do_payment', wraps=self._mock_subscription_do_payment):
                self.env['sale.order']._cron_recurring_create_invoice()
                self.subscription.transaction_ids._get_last()._post_process()
            # it should create an invoice
            self.assertEqual(self.subscription.invoice_count, 2)
        with freeze_time("2024-07-01"):
            with patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder._do_payment', wraps=self._mock_subscription_do_payment):
                self.env['sale.order']._cron_recurring_create_invoice()
                self.subscription.transaction_ids._get_last()._post_process()
            # it should create an invoice
            self.assertEqual(self.subscription.invoice_count, 3)
        with freeze_time("2024-08-01"):
            with patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder._do_payment', wraps=self._mock_subscription_do_payment):
                self.env['sale.order']._cron_recurring_create_invoice()
            # subscription should be closed on end date
            self.assertEqual(self.subscription.subscription_state, '6_churn')

    def test_subscription_recurring_invoice_and_reminder_domain(self):
        SaleOrder = self.env['sale.order']
        with freeze_time("2024-05-01"):
            sub_1 = SaleOrder.create({
                'name': 'with token and online payment true',
                'is_subscription': True,
                'partner_id': self.user_portal.partner_id.id,
                'pricelist_id': self.company_data['default_pricelist'].id,
                'plan_id': self.plan_month.id,
                'order_line': [
                    Command.create({
                        'product_id': self.product.id,
                        'product_uom_qty': 1
                    }),
                ],
                'require_payment': True,
                'payment_token_id': self.payment_token.id,
            })
            sub_1.action_confirm()

            sub_2 = SaleOrder.create({
                'name': 'without token and online payment true',
                'is_subscription': True,
                'partner_id': self.user_portal.partner_id.id,
                'pricelist_id': self.company_data['default_pricelist'].id,
                'plan_id': self.plan_month.id,
                'order_line': [
                    Command.create({
                        'product_id': self.product.id,
                        'product_uom_qty': 1
                    }),
                ],
                'require_payment': True,
            })
            sub_2.action_confirm()

            sub_3 = SaleOrder.create({
                'name': 'with token and online payment false',
                'is_subscription': True,
                'partner_id': self.user_portal.partner_id.id,
                'pricelist_id': self.company_data['default_pricelist'].id,
                'plan_id': self.plan_month.id,
                'order_line': [
                    Command.create({
                        'product_id': self.product.id,
                        'product_uom_qty': 1
                    }),
                ],
                'payment_token_id': self.payment_token.id,
            })
            sub_3.action_confirm()

            sub_4 = SaleOrder.create({
                'name': 'without token and online payment false',
                'is_subscription': True,
                'partner_id': self.user_portal.partner_id.id,
                'pricelist_id': self.company_data['default_pricelist'].id,
                'plan_id': self.plan_month.id,
                'order_line': [
                    Command.create({
                        'product_id': self.product.id,
                        'product_uom_qty': 1
                    }),
                ],
            })
            sub_4.action_confirm()

            sub_5 = SaleOrder.create({
                'name': 'without token online payment true and prepayment percent < 100',
                'is_subscription': True,
                'partner_id': self.user_portal.partner_id.id,
                'pricelist_id': self.company_data['default_pricelist'].id,
                'plan_id': self.plan_month.id,
                'order_line': [
                    Command.create({
                        'product_id': self.product.id,
                        'product_uom_qty': 1
                    }),
                ],
                'require_payment': True,
                'prepayment_percent': 0.5,
            })
            sub_5.action_confirm()

            sub_6 = SaleOrder.create({
                'name': 'with token online payment true and prepayment percent < 100',
                'is_subscription': True,
                'partner_id': self.user_portal.partner_id.id,
                'pricelist_id': self.company_data['default_pricelist'].id,
                'plan_id': self.plan_month.id,
                'order_line': [
                    Command.create({
                        'product_id': self.product.id,
                        'product_uom_qty': 1
                    }),
                ],
                'require_payment': True,
                'prepayment_percent': 0.5,
                'payment_token_id': self.payment_token.id,
            })
            sub_6.action_confirm()

            # filter out subscription for which "_create_recurring_invoice" cron should run
            all_subscriptions, need_cron_trigger = SaleOrder._recurring_invoice_get_subscriptions()
            self.assertFalse(need_cron_trigger)
            self.assertEqual([sub_6.id, sub_5.id, sub_4.id, sub_3.id, sub_1.id], all_subscriptions.ids, "subscriptions are not filtered correctly.")
            self.assertNotIn(sub_2.id, all_subscriptions.ids, "second subscription should not filtered in this domain")

            # filter out subscription for which "_cron_recurring_send_payment_reminder" cron should run
            parameters = SaleOrder._subscription_reminder_parameters()
            send_reminder_sub = SaleOrder.search(parameters['domain'])
            self.assertEqual([sub_5.id, sub_2.id], send_reminder_sub.ids, "subscriptions are not filtered correctly.")

            # run both the crons
            with patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder._do_payment', wraps=self._mock_subscription_do_payment):
                SaleOrder._cron_recurring_create_invoice()
                sub_1.transaction_ids._get_last()._post_process()
                sub_3.transaction_ids._get_last()._post_process()
                sub_6.transaction_ids._get_last()._post_process()
            SaleOrder._cron_recurring_send_payment_reminder()

        with freeze_time("2024-05-03"):
            # Filter out subscription for which "_create_recurring_invoice" cron should run
            all_subscriptions, need_cron_trigger = SaleOrder._recurring_invoice_get_subscriptions()
            self.assertFalse(need_cron_trigger)
            # No subscription should be filterd out.
            self.assertFalse(all_subscriptions, "subscriptions are not filtered correctly.")

            # Filter out subscription for which "_cron_recurring_send_payment_reminder" cron should run
            parameters = SaleOrder._subscription_reminder_parameters()
            send_reminder_sub = SaleOrder.search(parameters['domain'])
            self.assertEqual([sub_2.id], send_reminder_sub.ids, "subscriptions are not filtered correctly.")

            SaleOrder._cron_recurring_send_payment_reminder()

        with freeze_time("2024-06-01"):
            # filter out subscription for which "_create_recurring_invoice" cron should run
            all_subscriptions, need_cron_trigger = SaleOrder._recurring_invoice_get_subscriptions()
            self.assertFalse(need_cron_trigger)
            # sub 5 should be invoiced only for first time after we will send email for payment reminder
            self.assertEqual([sub_6.id, sub_4.id, sub_3.id, sub_1.id], all_subscriptions.ids, "subscriptions are not filtered correctly.")
            self.assertNotIn([sub_5.id, sub_2.id], all_subscriptions.ids, "second subscription should not filtered in this domain")

            # filter out subscription for which "_cron_recurring_send_payment_reminder" cron should run
            parameters = SaleOrder._subscription_reminder_parameters()
            send_reminder_sub = SaleOrder.search(parameters['domain'])
            self.assertEqual([sub_5.id, sub_2.id], send_reminder_sub.ids, "subscriptions are not filtered correctly.")

            # run both the crons
            with patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder._do_payment', wraps=self._mock_subscription_do_payment):
                SaleOrder._cron_recurring_create_invoice()
                sub_1.transaction_ids._get_last()._post_process()
                sub_3.transaction_ids._get_last()._post_process()
                sub_6.transaction_ids._get_last()._post_process()

            SaleOrder._cron_recurring_send_payment_reminder()

    def test_compute_last_invoiced_date(self):
        with freeze_time("2024-09-01"):
            subscription = self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'plan_id': self.plan_month.id,
                'order_line': [
                    (0, 0, {
                        'name': self.product.name,
                        'product_id': self.product.id,
                        'product_uom_qty': 3.0,
                        'product_uom': self.product.uom_id.id,
                        'price_unit': 12,
                    })],
            })
            subscription.action_confirm()
            inv = subscription._create_recurring_invoice()
            self.assertEqual(subscription.order_line.last_invoiced_date, datetime.date(2024, 9, 30), "Last invoiced date is updated")
            self.assertEqual(subscription.next_invoice_date, datetime.date(2024, 10, 1), "Next invoice date is updated")

        with freeze_time("2024-10-01"):
            inv = subscription._create_recurring_invoice()
            self.assertEqual(subscription.next_invoice_date, datetime.date(2024, 11, 1), "Next invoice date is updated")
            self.assertEqual(subscription.order_line.last_invoiced_date, datetime.date(2024, 10, 31), "Last invoiced date is updated")

        with freeze_time("2024-10-05"):
            inv.button_draft()
            self.assertEqual(subscription.order_line.last_invoiced_date, datetime.date(2024, 9, 30), "Last invoiced date is reset to previous value")
            inv.button_cancel()
            # user update the next invoice date to recreate it
            subscription.next_invoice_date = datetime.date(2024, 10, 1)

        # with freeze_time("2024-11-01"):
            self.assertEqual(subscription.order_line.last_invoiced_date, datetime.date(2024, 9, 30), "Last invoiced date is unchanged")
            inv = subscription._create_recurring_invoice()
            self.assertEqual(subscription.order_line.last_invoiced_date, datetime.date(2024, 10, 31), "Last invoiced date is updated")

        with freeze_time("2024-12-01"):
            inv = subscription._create_recurring_invoice()
            self.assertEqual(subscription.order_line.last_invoiced_date, datetime.date(2024, 11, 30), "Last invoiced date is updated")
            inv.payment_state = 'paid'
            # We refund the invoice
            refund_wizard = self.env['account.move.reversal'].with_context(
                active_model="account.move",
                active_ids=inv.ids).create({
                'reason': 'Test refund tax repartition',
                'journal_id': inv.journal_id.id,
            })
            res = refund_wizard.refund_moves()
            refund_move = self.env['account.move'].browse(res['res_id'])
            self.assertEqual(inv.reversal_move_ids, refund_move, "The initial move should be reversed")
            refund_move._post()
            # user update the next invoice date to recreate it
            subscription.next_invoice_date = datetime.date(2024, 11, 1)
            self.assertEqual(subscription.order_line.last_invoiced_date, datetime.date(2024, 10, 31), "Last invoiced date is reverted")
            inv = subscription._create_recurring_invoice()
            self.assertEqual(subscription.order_line.last_invoiced_date, datetime.date(2024, 11, 30), "Last invoiced date is updated")

    def test_invoice_credit_email_template(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_line_ids': [(0, 0, {
                'name': 'Test',
                'quantity': 1,
                'price_unit': 100,
                'subscription_id': self.subscription.id,
            })],
        })
        template_invoice_id = self.env['account.move.send']._get_default_mail_template_id(invoice).id
        self.assertEqual(template_invoice_id, self.env.ref('account.email_template_edi_invoice').id, 'The email template id for an Invoice is not what it should be.')
        credit_note = self.env['account.move'].create({
            'move_type': 'out_refund',
            'invoice_line_ids': [(0, 0, {
                'name': 'Test',
                'quantity': 1,
                'price_unit': 100,
                'subscription_id': self.subscription.id,
            })],
        })
        template_credit_id = self.env['account.move.send']._get_default_mail_template_id(credit_note).id
        self.assertEqual(template_credit_id, self.env.ref('account.email_template_edi_credit_note').id, 'The email template id for a Credit Note is not what it should be.')


    def test_next_billing_details(self):
        with freeze_time("2024-11-20"):
            """Test the value displayed on the portal"""
            context_no_mail = {'no_reset_password': True, 'mail_create_nosubscribe': True, 'mail_create_nolog': True, }
            self.env.ref('base.MXN').active = True
            mxn_pricelist = self.env['product.pricelist'].create({
                'name': 'MXN pricelist',
                'currency_id': self.env.ref('base.MXN').id,
            })
            SubPricing = self.env['sale.subscription.pricing'].with_context(context_no_mail)
            SubPricing.create({
                'plan_id': self.plan_month.id,
                'price': 6,
                'pricelist_id': mxn_pricelist.id,
                'product_template_id': self.product.product_tmpl_id.id
            })
            SubPricing.create({
                'plan_id': self.plan_month.id,
                'price': 600,
                'pricelist_id': mxn_pricelist.id,
                'product_template_id': self.product2.product_tmpl_id.id
            })
            self.subscription.order_line[0].name = "First recurring product"
            self.subscription.order_line[1].name = "Second recurring product"
            self.product5.recurring_invoice = False
            self.subscription.order_line = [Command.create({
                'name': "Non recurring line",
                'product_id': self.product5.id, # non recurring product
                'product_uom_qty': 1
            })]
            self.subscription.action_confirm()
            details = self.subscription._next_billing_details()
            self.assertEqual(details["sale_order"], self.subscription, "self is the subscription")
            self.assertAlmostEqual(details["next_invoice_amount"], 69.3, 2, "The next invoice amount the total amount")
            self.subscription._create_recurring_invoice()
            details = self.subscription._next_billing_details()
            self.assertAlmostEqual(details["next_invoice_amount"], 23.1, 2, "Only the recurring product is invoiced")
        with freeze_time("2024-12-20"):
            action = self.subscription.prepare_renewal_order()
            renewal_so = self.env['sale.order'].browse(action['res_id'])
            renewal_so.pricelist_id = mxn_pricelist
            renewal_so.order_line = [Command.create({
                'name': "Non recurring line",
                'product_id': self.product5.id, # non recurring product
                'product_uom_qty': 2
            })]
            renewal_so.action_update_prices()
            renewal_so.action_confirm()
            details = renewal_so._next_billing_details()
            self.assertAlmostEqual(details["next_invoice_amount"], 759.0, 2, "Only the recurring product is invoiced")
            inv = renewal_so._create_recurring_invoice()
            details = renewal_so._next_billing_details()
            self.assertAlmostEqual(details["next_invoice_amount"], 666.6, 2, "Only the recurring product is invoiced")

    def test_postpaid_next_invoice_date(self):
        """" Ensure the next invoice date is correctly updated for postpaid orders
        This test fix a bug where a new invoice was created every day if postpaid line were mixed with non recurring lines
        """
        if self.env.ref('base.module_sale_subscription_stock').state == 'installed':
            self.skipTest("`stock` module is installed. The invoice amount depends on the stock.move validation")
        with freeze_time("2025-01-01"):
            sub_product_delivery = self.env['product.product'].create({
                'name': "Subscription consumable invoiced on delivery",
                'list_price': 42,
                'type': 'consu',
                'uom_id': self.uom_unit.id,
                'invoice_policy': 'delivery',
                'recurring_invoice': True,
            })
            product_non_recurring = self.env['product.product'].create({
                'name': "Consumable invoiced on order",
                'list_price': 30.0,
                'type': 'consu',
                'uom_id': self.uom_unit.id,
                'invoice_policy': 'order',
            })
            sub = self.env['sale.order'].create({
                'name': 'Delivery',
                'is_subscription': True,
                'partner_id': self.user_portal.partner_id.id,
                'plan_id': self.plan_month.id,
                'pricelist_id': self.company_data['default_pricelist'].id,
                'order_line': [Command.create({
                    'product_id': sub_product_delivery.id,
                    'product_uom_qty': 1,
                    'tax_id': [Command.clear()],
                }), Command.create({
                    'display_type': 'line_section',
                    'name': 'Test section',
                }), Command.create({
                    'product_id': product_non_recurring.id,
                    'product_uom_qty': 1,
                    'tax_id': [Command.clear()],
                })],
            })
            sub.action_confirm()
            inv = sub._create_recurring_invoice()
            self.assertEqual(sub.next_invoice_date, datetime.date(2025, 2, 1))
            self.assertAlmostEqual(inv.amount_untaxed, 30, msg="We invoice only the non recurring product")
            recurring_line = sub.order_line.filtered(lambda l: l.product_id.id == sub_product_delivery.id)
            recurring_line.qty_delivered = 1

        with freeze_time("2025-02-01"):
            inv = self.env['sale.order']._create_recurring_invoice()
            self.assertAlmostEqual(inv.amount_untaxed, 42, msg="We invoice recurring products")
            self.assertEqual(sub.next_invoice_date, datetime.date(2025, 3, 1))

        with freeze_time("2025-03-01"):
            inv = sub._create_recurring_invoice()
            self.assertAlmostEqual(inv.amount_untaxed, 42, msg="We invoice recurring products")
            self.assertEqual(sub.next_invoice_date, datetime.date(2025, 4, 1))

    def test_confirm_upsell_cancels_pending_upsells(self):
        delivered_product_tmpl = self.env['product.template'].create({
            'name': 'Delivery product',
            'type': 'consu',
            'recurring_invoice': True,
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'invoice_policy': 'order',
            'list_price': 50.0,
        })
        product = delivered_product_tmpl.product_variant_id
        # create a subscription with a custom price_unit
        subscription = self.env['sale.order'].create({
            'name': 'Original subscription',
            'is_subscription': True,
            'partner_id': self.partner.id,
            'plan_id': self.plan_month.id,
            'order_line': [
                Command.create({
                    'name': product.name,
                    'product_id': product.id,
                    'product_uom_qty': 1,
                    'product_uom': self.env.ref('uom.product_uom_unit').id,
                    'price_unit': 10,
                }),
            ]
        })

        subscription.action_confirm()
        move = subscription._create_invoices()
        move.action_post()
        # Create two upsells and confirm them later.
        action = subscription.prepare_upsell_order()
        upsell = self.env['sale.order'].browse(action['res_id'])
        upsell.name = "UPSELL 1"
        action2 = subscription.prepare_upsell_order()
        upsell2 = self.env['sale.order'].browse(action2['res_id'])
        upsell2.name = "UPSELL 2"
        self.assertEqual(upsell.order_line.parent_line_id, subscription.order_line, "The parent_line_id should be correctly set")
        self.assertEqual(upsell2.order_line.parent_line_id, subscription.order_line, "The parent_line_id should be correctly set")
        # upsell confirmation
        upsell.action_confirm()
        self.assertEqual(upsell.order_line.price_unit, 10, "The unit price should be the same as the original subscription")
        self.assertEqual(upsell.order_line.parent_line_id, subscription.order_line, "The parent_line_id should be correctly set")
        self.assertEqual(upsell2.order_line.price_unit, 10, "The unit price should be the same as the original subscription")
        self.assertEqual(upsell2.order_line.parent_line_id, subscription.order_line, "The unit price should be the same as the original subscription")
        upsell2.action_confirm()
        self.assertEqual(upsell2.order_line.price_unit, 10, "The unit price should be the same as the original subscription")
        self.assertEqual(upsell.order_line.parent_line_id, subscription.order_line, "The parent_line_id of first upsell should not be reset")
        self.assertEqual(upsell.order_line.price_unit, 10, "The unit price shouldn't get updated")

    def test_not_override_end_date_in_expiration_cron(self):
        """Ensure the expiration cron does not override an existing past end_date."""
        with freeze_time("2025-05-05"):
            self.subscription.write({'end_date': datetime.date(2025, 6, 4)})
            self.subscription.action_confirm()
            self.subscription._create_recurring_invoice()
            today = fields.Date.today()
            self.assertEqual(self.subscription.start_date, today, "start date set to today")
            self.assertEqual(self.subscription.next_invoice_date, datetime.date(2025, 6, 5))
            self.assertEqual(self.subscription.end_date, datetime.date(2025, 6, 4))

        with freeze_time("2025-06-10"):
            self.env["sale.order"].sudo()._cron_subscription_expiration()
            self.assertEqual(self.subscription.end_date, datetime.date(2025, 6, 4), "after expiration cron run, end_date should remain unchanged if already set and in the past")

    def test_null_ordered_quantity(self):
        """ Null recurring line should not appear in the invoice """
        with freeze_time("2025-06-03"):
            self.assertEqual(self.product3.invoice_policy, 'order', "We need invoice policy order for this test")
            self.subscription.order_line = [Command.create({
                    'name': self.product3.name,
                    'product_id': self.product3.id,
                    'product_uom_qty': 0,
                    'product_uom': self.env.ref('uom.product_uom_unit').id,
                    'price_unit': 10,

            })]
            self.subscription.action_confirm()
            inv = self.subscription._cron_recurring_create_invoice()
            self.assertEqual(len(inv.invoice_line_ids), 2)
            product_ids = inv.invoice_line_ids.product_id
            self.assertEqual(len(product_ids), 2)
            self.assertTrue(self.product.id in product_ids.ids)
            self.assertTrue(self.product2.id in product_ids.ids)

    def test_upsell_invoice_line_description(self):
        self.plan_year.billing_first_day = True
        with freeze_time("06/30/2025"):
            subscription = self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'plan_id': self.plan_year.id,
                'order_line': [
                    Command.create({
                        'name': self.product.name,
                        'product_id': self.product.id,
                        'product_uom_qty': 2.0,
                        'product_uom': self.product.uom_id.id,
                        'price_unit': 12,
                        })],
            })
            subscription.plan_id = self.plan_year
            subscription.action_confirm()
            subscription._cron_recurring_create_invoice()
            invoice = subscription._create_invoices()
            invoice.action_post()
            action = subscription.prepare_upsell_order()
            upsell = self.env['sale.order'].browse(action['res_id'])
            upsell.action_confirm()
            line = upsell.order_line[0]._prepare_invoice_line()

            self.assertIn("550 days 06/30/2025 to 12/31/2026", line['name'])

    def test_invoice_status_on_manual_invoices(self):
        postpaid_product = self.product.copy({
            'invoice_policy': 'delivery',
        })
        with freeze_time("2025-02-15"):
            # Subscription for a product invoiced based on delivered quantities
            subscription = self.env['sale.order'].create({
                'name': 'Subscription',
                'partner_id': self.partner.id,
                'plan_id': self.plan_month.id,
                'order_line': [
                    Command.create({
                        'name': postpaid_product.name,
                        'product_id': postpaid_product.id,
                        'product_uom_qty': 1.0,
                        'product_uom': postpaid_product.uom_id.id,
                        'price_unit': 10,
                    }),
                ]
            })
            subscription.action_confirm()
            self.assertEqual(subscription.order_line.invoice_status, 'no')
            subscription.order_line.qty_delivered = 1
            self.assertEqual(subscription.order_line.invoice_status, 'to invoice')
            subscription._create_invoices().action_post()
            self.assertEqual(subscription.order_line.invoice_status, 'invoiced')

            # Upsell
            action = subscription.prepare_upsell_order()
            upsell_subscription = self.env['sale.order'].browse(action['res_id'])
            upsell_subscription.order_line = [Command.create({
                'product_id': postpaid_product.id,
                'product_uom_qty': 1.0,
                'product_uom': postpaid_product.uom_id.id,
                'price_unit': 10,
            })]
            upsell_subscription_line = upsell_subscription.order_line.filtered(lambda l: not l.display_type)
            self.assertEqual(upsell_subscription_line.invoice_status, 'no')
            upsell_subscription_line.qty_delivered = 1
            upsell_subscription.action_confirm()
            self.assertEqual(upsell_subscription_line.invoice_status, 'to invoice')
            upsell_subscription._create_invoices().action_post()
            self.assertEqual(upsell_subscription_line.invoice_status, 'invoiced')

            # Subscription for a product invoiced based on ordered quantities
            subscription = self.env['sale.order'].create({
                'name': 'Subscription',
                'partner_id': self.partner.id,
                'plan_id': self.plan_month.id,
                'order_line': [
                    Command.create({
                        'name': self.product.name,
                        'product_id': self.product.id,
                        'product_uom_qty': 1.0,
                        'product_uom': self.product.uom_id.id,
                        'price_unit': 10,
                    }),
                ]
            })
            subscription.action_confirm()
            self.assertEqual(subscription.order_line.invoice_status, 'to invoice')
            subscription._create_invoices().action_post()
            self.assertEqual(subscription.order_line.invoice_status, 'invoiced')

            # Upsell
            action = subscription.prepare_upsell_order()
            upsell_subscription = self.env['sale.order'].browse(action['res_id'])
            upsell_subscription_line = upsell_subscription.order_line.filtered(lambda l: not l.display_type)
            upsell_subscription_line.product_uom_qty = 1.0
            self.assertEqual(upsell_subscription_line.invoice_status, 'no')
            upsell_subscription.action_confirm()
            self.assertEqual(upsell_subscription_line.invoice_status, 'to invoice')
            upsell_subscription._create_invoices().action_post()
            self.assertEqual(upsell_subscription_line.invoice_status, 'invoiced')


    def test_subscription_upsell_alternative_invoice(self):
        self.subscription.action_confirm()
        self.env['sale.order']._cron_recurring_create_invoice()
        action = self.subscription.prepare_upsell_order()
        upsell_so = self.env['sale.order'].browse(action['res_id'])
        action = upsell_so.create_alternative()
        alternative_upsell_so = self.env['sale.order'].browse(action['res_id'])
        alternative_upsell_order_line = alternative_upsell_so.order_line.filtered(lambda line: not line.display_type)
        for sol in alternative_upsell_order_line:
            sol.product_uom_qty = 1.0
        alternative_upsell_so.action_confirm()
        alternative_upsell_so._create_invoices()
        self.assertTrue(len(alternative_upsell_so.invoice_ids), "An invoice should have been created for the alternative upsell sale order.")


@tagged('post_install', '-at_install')
@freeze_time("2021-01-03")
class TestSubscriptionInvoiceSignature(TestInvoiceSignature, TestSubscription):
    def setUp(self):
        super().setUp()
        self.sale_subscription_cron = self.env.ref("sale_subscription.account_analytic_cron_for_invoice")
        self.another_user.groups_id += self.env.ref("sales_team.group_sale_salesman")
        self.subscription = self.env['sale.order'].with_user(self.another_user).create({
                'partner_id': self.partner_a.id,
                'company_id': self.company_data['company'].id,
                'plan_id': self.plan_month.id,
                'order_line': [
                    Command.create({
                        'name': self.product.name,
                        'product_id': self.product.id,
                        'product_uom_qty': 2.0,
                        'product_uom': self.product.uom_id.id,
                        'price_unit': 12,
                    })],
        })
        self.subscription.with_user(self.another_user).action_confirm()

    def test_subscription_automated_invoice_should_have_signing_user_set_to_salesman(self):
        self.assertEqual(self.subscription.invoice_count, 0)
        self.sale_subscription_cron.method_direct_trigger()
        self.assertEqual(self.subscription.invoice_count, 1)
        inv = self.subscription.invoice_ids
        self.assertEqual(
            inv.signing_user,
            self.another_user,
            "When the invoice is posted by odoobot, the signer should be the one that confirmed the subscription"
        )

    def test_subscription_automated_invoice_should_have_signing_user_set_to_representative_when_there_is_one(self):
        representative_user = self.company_data['default_user_salesman']
        self.env.company.signing_user = representative_user  # set the representative user of the company
        self.assertEqual(self.subscription.invoice_count, 0)
        self.sale_subscription_cron.method_direct_trigger()
        self.assertEqual(self.subscription.invoice_count, 1)
        inv = self.subscription.invoice_ids
        self.assertEqual(
            inv.signing_user,
            representative_user,
            "Signer should be representative if available"
        )

    def test_product_subscription_pricing_copy(self):
        """Check that product variants on product pricings after copying
        a product template.
        """
        product = self.product_tmpl_2
        product_attribute = self.env['product.attribute'].create({
            'name': 'Color',
            'value_ids': [Command.create({'name': name}) for name in ('Blue', 'Red')],
        })
        product.attribute_line_ids = 2 * [Command.create({
            'attribute_id': product_attribute.id,
            'value_ids': product_attribute.value_ids.ids,
        })]
        for i, variant in enumerate(product.product_variant_ids, start=1):
            self.env['sale.subscription.pricing'].create([{
                'product_template_id': product.id,
                'product_variant_ids': [Command.link(variant.id)],
                'plan_id': self.plan_week.id,
                'price': 10.0 * i,
                'pricelist_id': self.company_data['default_pricelist'].id,
            }, {
                'product_template_id': product.id,
                'product_variant_ids': [Command.link(variant.id)],
                'plan_id': self.plan_month.id,
                'price': 25.0 * i,
           }])
        pricings_1 = product.product_subscription_pricing_ids.sorted()
        pricings_2 = product.copy().product_subscription_pricing_ids.sorted()
        self.assertEqual(
            len(pricings_2),
            8,  # 2 attributes * 2 values * 2 plans = 8 pricings
            "copied product should get 8 pricings",
        )
        self.assertNotEqual(
            pricings_2.product_variant_ids,
            pricings_1.product_variant_ids,
            "copied pricings shouldn't be linked to the original products",
        )
        for pricing_1, pricing_2 in zip(pricings_1, pricings_2):
            self.assertEqual(pricing_2.price, pricing_1.price)
            self.assertEqual(pricing_2.plan_id, pricing_1.plan_id)
            self.assertEqual(pricing_2.pricelist_id, pricing_1.pricelist_id)
        mitchell_user = self.env['res.users'].create({
            'name': 'Mitchell not Admin',
            'login': 'm_user',
            'email': 'm@user.com',
            'groups_id': [(6, 0, self.env.ref('base.group_system').ids)],
        })
        product.invalidate_recordset(['product_subscription_pricing_ids'])
        with self.assertRaises(AccessError):
            product.with_user(mitchell_user).product_subscription_pricing_ids
        with self.assertRaises(UserError):
            product.with_user(mitchell_user).copy()

    def test_renewed_churned_canceled(self):
        context_no_mail = {'no_reset_password': True, 'mail_create_nosubscribe': True, 'mail_create_nolog': True}
        with freeze_time("2024-07-03"):
            subscription = self.env['sale.order'].with_context(context_no_mail).create({
                'name': 'TestSubscription',
                'is_subscription': True,
                'plan_id': self.plan_month.id,
                'note': "original subscription description",
                'partner_id': self.user_portal.partner_id.id,
                'pricelist_id': self.company_data['default_pricelist'].id,
                'sale_order_template_id': self.subscription_tmpl.id,
            })
            subscription._onchange_sale_order_template_id()
            subscription.start_date = False
            subscription.end_date = False
            self.flush_tracking()
            subscription.action_confirm()
            self.flush_tracking()
            subscription._create_recurring_invoice()
            self.assertEqual(subscription.invoice_count, 1)
        with freeze_time("2024-08-03"):
            action = subscription.prepare_renewal_order()
            renewal_so = self.env['sale.order'].browse(action['res_id'])
            self.flush_tracking()
            renewal_so.action_confirm()
            self.flush_tracking()
        with freeze_time("2024-09-03"):
            # customer never pays (happens when the token is not working).
            renewal_so.sudo()._cron_subscription_expiration()
            self.flush_tracking()
            self.assertEqual(renewal_so.subscription_state, '6_churn')
            self.assertEqual(subscription.subscription_state, '5_renewed')
            with self.assertRaises(ValidationError):
                # You cannot cancel a churned renewed subscription. You can reopen it and cancel it if you want to reopen the parent
                renewal_so._action_cancel()
            renewal_so.reopen_order()
            renewal_so._action_cancel()
            self.assertFalse(renewal_so.subscription_state, "renewal is canceled")
            self.assertEqual(renewal_so.state, 'cancel', "renewal is canceled")
            self.assertEqual(subscription.subscription_state, '3_progress')

    def test_sale_order_log_creation(self):
        """ Test that duplicating a canceled quotation is possible
        """
        with freeze_time("2024-07-30"):
            self.subscription.write({
                        'start_date': False,
                        'next_invoice_date': False,
            })
            self.subscription._onchange_sale_order_template_id()
            self.subscription._action_cancel()
            self.assertFalse(self.subscription.subscription_state)
            sub = self.subscription.copy()
            self.assertEqual(sub.subscription_state, '1_draft')
            self.assertEqual(sub.state, 'draft')
        with freeze_time("2024-07-31"):
            self.flush_tracking()
            sub.action_confirm()
            self.flush_tracking()
            self.assertEqual(sub.subscription_state, '3_progress')
            self.assertFalse(self.subscription.subscription_state)
            log = sub.order_log_ids
            self.assertEqual(len(log), 1)
            self.assertEqual(log.event_type, '0_creation')
            self.assertEqual(log.subscription_state, '1_draft')

    def test_recurring_create_invoice_branch(self):
        self.company.child_ids = [Command.create({'name': 'Branch'})]
        branch = self.company.child_ids[0]
        product = self.product.copy({'company_id': branch.id})
        sub = self.env['sale.order'].with_company(branch).create({
            'name': 'TestSubscription',
            'is_subscription': True,
            'plan_id': self.plan_month.id,
            'partner_id': self.user_portal.partner_id.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'order_line': [(0, 0, {'product_id': product.id})],
        })
        sub.action_confirm()
        self.env['sale.order']._cron_recurring_create_invoice()

        self.assertEqual(sub.invoice_count, 1)
        self.assertEqual(sub.invoice_ids.company_id, branch)
        self.assertEqual(sub.invoice_ids.state, 'posted')

    def test_sale_determine_order(self):
        """ If a subscription order is locked but has a renewal (child order), an attempt to
        expense some purchase order which is linked to the analytic account of the subscription
        should use the non-locked, renewed order.
        """
        required_modules = ('project_hr_expense', 'purchase')
        if not all(self.env['ir.module.module']._get(module).state == 'installed' for module in required_modules):
            self.skipTest(f'This test requires the installation of the following modules: {required_modules}')

        analytic_plan = self.env['account.analytic.plan'].create({'name': 'TSDO analytic plan'})
        analytic_account1, analytic_account2 = self.env['account.analytic.account'].create([{
            'name': f'TSDO analytic account {i}',
            'plan_id': analytic_plan.id,
        } for i in (1, 2)])

        project = self.env['project.project'].with_context({'mail_create_nolog': True}).create({
            'name': 'Project',
            'partner_id': self.partner_a.id,
            'account_id': analytic_account1.id,
        })
        recurring_service_with_linked_project = self.env['product.product'].create({
            'name': 'service_with_linked_project',
            'standard_price': 30,
            'list_price': 90,
            'type': 'service',
            'service_tracking': 'task_global_project',
            'project_id': project.id,
            'recurring_invoice': True,
        })
        expensable_service_product = self.env['product.product'].create({
            'name': 'Material',
            'type': 'service',
            'standard_price': 5,
            'list_price': 10,
            'can_be_expensed': True,
            'expense_policy': 'sales_price',
            'purchase_method': 'purchase',
        })
        subscription1, subscription2 = self.env['sale.order'].create([{
            'name': 'TestSubscription',
            'is_subscription': True,
            'plan_id': self.plan_month.id,
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'product_id': recurring_service_with_linked_project.id,
                'product_uom_qty': 1,
                'price_unit': 10,
            })],
            'project_account_id': analytic_account_id,
        } for analytic_account_id in [analytic_account1.id, analytic_account2.id]])
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'product_id': expensable_service_product.id,
                'product_uom_qty': 1,
                'analytic_distribution': {analytic_account1.id: 100.0},
            }), (0, 0, {
                'product_id': expensable_service_product.id,
                'product_uom_qty': 1,
                'analytic_distribution': {analytic_account2.id: 100.0},
            })],
        })
        subscriptions = subscription1 + subscription2
        subscriptions.action_confirm()
        subscriptions._create_invoices()
        subscriptions.invoice_ids[0].action_post()
        subscription1.prepare_renewal_order()
        subscription2.prepare_renewal_order()
        first_renewal_sub1 = subscription1.subscription_child_ids[0]
        first_renewal_sub1.action_confirm()
        first_renewal_sub1.with_context(disable_cancel_warning=True).action_cancel()
        subscription1.subscription_state = '3_progress'
        subscription1.prepare_renewal_order()
        second_renewal_sub1 = subscription1.subscription_child_ids.filtered(lambda so: so.state == 'draft')
        second_renewal_sub1.action_confirm()
        second_renewal_sub1._create_invoices()
        second_renewal_sub1.invoice_ids.filtered(lambda am: am.state == 'draft').action_post()
        second_renewal_sub1.prepare_renewal_order()
        second_renewal_renewal_sub1 = second_renewal_sub1.subscription_child_ids[0]
        second_renewal_renewal_sub1.action_confirm()

        purchase_order.button_confirm()
        purchase_order.action_create_invoice()
        purchase_order_invoice = purchase_order.invoice_ids[0]
        purchase_order_invoice.invoice_date = '2000-05-05'
        purchase_order_invoice.action_post()

        self.assertEqual(purchase_order_invoice.state, 'posted')

    def test_uspell_same_product_different_discount(self):
        subscription = self.env['sale.order'].create({
            'name': 'Original subscription',
            'is_subscription': True,
            'partner_id': self.user_portal.partner_id.id,
            'plan_id': self.plan_month.id,
            'order_line': [
                Command.create({
                    'name': self.product2.name,
                    'product_id': self.product2.id,
                    'product_uom_qty': 1,
                    'product_uom': self.env.ref('uom.product_uom_unit').id,
                    'discount': 0,
                }),
                Command.create({
                    'name': self.product2.name,
                    'product_id': self.product2.id,
                    'product_uom_qty': 1,
                    'product_uom': self.env.ref('uom.product_uom_unit').id,
                    'discount': 50,
                })
            ]
        })

        subscription.action_confirm()
        self.env['sale.order']._cron_recurring_create_invoice()
        action = subscription.prepare_upsell_order()
        upsell = self.env['sale.order'].browse(action['res_id'])
        self.assertEqual(set(upsell.order_line.mapped('discount')), {0, 50}, 'Upsell discounts should match subscription discounts')

    def test_churn_discount_removal(self):
        """ Test the following flow:
                Sub with first year discount -> Renew -> Discount is removed on original sub -> Cancel the renewal -> Churn the original sub
            This flow was causing an issue where the churn log amount was set as the full amount instead of the discounted amount which resulted negative MRR.
        """
        # create new subscription with discount
        self.product2.list_price = -1
        sub = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan_year.id,
            'order_line': [
                    (0, 0, {
                        'name': self.product.name,
                        'product_id': self.product.id,
                        'product_uom_qty': 10.0,
                    }),
                    (0, 0, {
                        'name': self.product2.name,
                        'product_id': self.product2.id,
                        'product_uom_qty': 1.0,
                    }),
                ],
        })
        self.flush_tracking()
        sub.action_confirm()
        self.flush_tracking()
        new_log = sub.order_log_ids
        self.assertEqual([new_log.event_type, new_log.amount_signed], ['0_creation', 83.25])
        sub._create_recurring_invoice()

        # renew the subscription without discount
        action = sub.prepare_renewal_order()
        renewal_so = self.env['sale.order'].browse(action['res_id'])
        renewal_so.order_line.filtered(lambda l: l.product_id == self.product2).unlink()
        self.flush_tracking()
        renewal_so.action_confirm()
        self.flush_tracking()

        # remove first year discount on original subscription
        # shoudln't be doable normally but this simulate first year discount removal via cron
        sub.order_line.filtered(lambda l: l.product_id == self.product2).unlink()

        # cancel renewal
        self.flush_tracking()
        renewal_so._action_cancel()
        self.flush_tracking()

        # churn
        sub.set_close()
        self.flush_tracking()
        self.assertEqual(sum(sub.order_log_ids.mapped('amount_signed')), 0)

    def test_subscription_discount_on_non_sub_lines(self):
        """
        Check that discounts manually set on non-subscription order lines are preserved after creating
        the subscription and when closing it.
        """
        DISCOUNT_10 = 10
        self.product2.recurring_invoice = False

        subscription = self.env['sale.order'].create({
            'name': 'Test subscription',
            'is_subscription': True,
            'partner_id': self.partner.id,
            'plan_id': self.plan_month.id,
            'order_line': [
                Command.create({
                    'name': 'Subscription product',
                    'product_id': self.product.id,
                    'product_uom_qty': 1,
                    'discount': DISCOUNT_10,
                }),
                Command.create({
                    'name': 'Non-subscription product',
                    'product_id': self.product2.id,
                    'product_uom_qty': 1,
                    'discount': DISCOUNT_10,
                })
            ]
        })

        self.assertEqual(subscription.order_line.mapped("discount"), [DISCOUNT_10, DISCOUNT_10])

        subscription.action_confirm()
        subscription._cron_recurring_create_invoice()
        subscription.set_close()

        self.assertEqual(subscription.order_line.mapped("discount"), [DISCOUNT_10, DISCOUNT_10])

    def test_partial_refund_reduces_invoiced_quantity_on_subscription(self):
        """
        Verify that a partial refund on a subscription invoice
        correctly updates the invoiced quantity on the order line.
        """
        with freeze_time("2024-09-01"):
            subscription = self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'plan_id': self.plan_month.id,
                'order_line': [
                    (0, 0, {
                        'name': self.product.name,
                        'product_id': self.product.id,
                        'product_uom_qty': 3.0,
                        'product_uom': self.product.uom_id.id,
                        'price_unit': 12,
                    })],
            })
            subscription.action_confirm()
            subscription._create_recurring_invoice()
            self.assertEqual(subscription.order_line.qty_invoiced, 3, "The 3 products should be invoiced")
            subscription._get_invoiced()
            inv = subscription.invoice_ids
            inv.payment_state = 'paid'
            refund_wizard = self.env['account.move.reversal'].with_context(
                active_model="account.move",
                active_ids=inv.ids).create({
                'reason': 'Partial refund for Product A',
                'journal_id': inv.journal_id.id,
            })
            refund_wizard.reverse_moves()

            credit_note = self.env['account.move'].search([
                ('reversed_entry_id', '=', inv.id),
                ('move_type', '=', 'out_refund'),
            ], limit=1)

            for line in credit_note.invoice_line_ids:
                if line.product_id.id == self.product.id:
                    line.quantity = 2

            credit_note._compute_amount()
            credit_note._compute_tax_totals()

            credit_note.action_post()

        self.assertEqual(subscription.order_line.qty_invoiced, 1, "The invoiced quantity should be reduced by the refund")

    def test_sale_subscription_optional_product_discount(self):
        """
        Check that the discount on an optional product is correctly applied when the option is added to a SO.
        """
        subscription = self.env['sale.order'].create({
            'name': "Test subscription",
            'is_subscription': True,
            'partner_id': self.partner.id,
            'plan_id': self.plan_month.id,
            'order_line': [
                Command.create({
                    'name': "Subscription product",
                    'product_id': self.product.id,
                    'product_uom_qty': 1,
                }),
            ],
            'sale_order_option_ids': [
                Command.create({
                    'product_id': self.product2.id,
                    'discount': 20,  # 20% discount
                })
            ],
        })
        subscription.sale_order_option_ids[0].button_add_to_order()

        self.assertEqual(subscription.order_line.mapped("discount"), [0, 20])

    def test_subscription_product_update_on_parent_line_in_upsell(self):
        """
        Check recurring product quantity on subscription after updating product
        on parent line in upsell and confirm.
        """
        # Non-recurring product
        nr_product = self.env['product.product'].create({
            'name': 'Non recurring product',
            'type': 'service',
            'uom_id': self.product.uom_id.id,
            'list_price': 25,
        })
        # Subscription
        subscription = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'company_id': self.company_data['company'].id,
            'plan_id': self.plan_month.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'product_uom_qty': 2.0,
                    'product_uom': self.product.uom_id.id,
                    'price_unit': 12,
                })
            ],
        })
        subscription.action_confirm()
        sub_line = subscription.order_line
        self.assertEqual(len(sub_line), 1)
        self.assertEqual(sub_line.product_uom_qty, 2.0)
        self.env['sale.order']._cron_recurring_create_invoice()

        # Upsell
        action = subscription.prepare_upsell_order()
        upsell_so = self.env['sale.order'].browse(action['res_id'])
        self.assertEqual(subscription.order_line, upsell_so.order_line.parent_line_id,
                         "The parent line is the one from the subscription")
        upsell_order_line = upsell_so.order_line.filtered(lambda line: not line.display_type)
        self.assertEqual(upsell_order_line.product_uom_qty, 0.0, 'The upsell order has 0 quantity')

        # Update the existing line with non-recurring product and quantity
        upsell_order_line.product_id = nr_product
        upsell_order_line.product_uom_qty = 11.0

        # Confirm upsell
        upsell_so._confirm_upsell()
        upsell_line = upsell_so.order_line.filtered(lambda line: not line.display_type)
        self.assertEqual(len(upsell_line), 1)
        self.assertFalse(upsell_line.parent_line_id)
        self.assertEqual(upsell_line.product_uom_qty, 11.0)
        # Check recurring product quantity after upsell
        self.assertEqual(len(subscription.order_line), 1)
        self.assertEqual(subscription.order_line.product_uom_qty, 2.0,
                         "The recurring product's quantity should not be changed in subscription")

    def test_invoice_after_deleting_invoiced_line(self):
        """ Test that invoicing works correctly after deleting an already invoiced subscription line.
        This test covers the fix for _get_max_invoiced_date when sale_line_ids is empty
        """
        product_a = self.env['product.product'].create({
            'name': 'Car Leasing (SUB)',
            'type': 'service',
            'recurring_invoice': True,
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'list_price': 20,
        })
        product_b = self.env['product.product'].create({
            'name': 'Office Cleaning Service (SUB)',
            'type': 'service',
            'recurring_invoice': True,
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'list_price': 10,
        })

        with freeze_time('2025-11-11'):
            subscription = self.env['sale.order'].create({
                'name': 'Test Subscription',
                'is_subscription': True,
                'plan_id': self.plan_month.id,
                'partner_id': self.partner.id,
                'order_line': [Command.create({
                    'product_id': product_a.id,
                    'product_uom_qty': 1.0,
                    'price_unit': 20,
                })],
            })
            subscription.action_confirm()

            invoice_1 = subscription._create_invoices()
            invoice_1._post()

            self.assertEqual(len(subscription.invoice_ids), 1, 'First invoice should be created')
            self.assertEqual(subscription.order_line.qty_invoiced, 1.0, 'Product A should be invoiced')

            subscription.write({
                'order_line': [Command.create({
                    'product_id': product_b.id,
                    'product_uom_qty': 1.0,
                    'price_unit': 10,
                })],
            })

            line_to_delete = subscription.order_line.filtered(lambda l: l.product_id == product_a)
            line_to_delete.unlink()

            self.assertEqual(len(subscription.order_line), 1, 'Only product B line should remain')
            self.assertEqual(subscription.order_line.product_id, product_b, 'Remaining line should be product B')
            self.assertEqual(len(subscription.invoice_ids), 1, 'Invoice for product A should still exist')

            invoice_2 = subscription._create_invoices()

            self.assertTrue(invoice_2, 'Second invoice should be created successfully')
            self.assertEqual(len(subscription.invoice_ids), 2, 'Should have two invoices total')

            invoice_2_lines = invoice_2.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
            self.assertEqual(len(invoice_2_lines), 1, 'Second invoice should have one product line')
            self.assertEqual(invoice_2_lines.product_id, product_b, 'Second invoice should be for product B')

            invoice_2._post()
            self.assertEqual(invoice_2.state, 'posted', 'Second invoice should be posted successfully')

    def test_next_invoice_date_with_invoice_quantities_summing_to_zero(self):
        """
        Verify that the next invoice date is correctly updated when having a
        subscription with several lines whose quantities add up to zero.
        """
        with freeze_time("2024-09-01"):
            subscription = self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'plan_id': self.plan_month.id,
                'order_line': [
                    (0, 0, {
                        'name': self.product.name,
                        'product_id': self.product.id,
                        'product_uom_qty': 1.0,
                        'product_uom': self.product.uom_id.id,
                        'price_unit': 50,
                    }),
                    (0, 0, {
                        'name': self.product.name,
                        'product_id': self.product.id,
                        'product_uom_qty': -1.0,
                        'product_uom': self.product.uom_id.id,
                        'price_unit': 20,
                    })],
            })
            subscription.action_confirm()
            self.assertEqual(subscription.next_invoice_date, datetime.date(2024, 9, 1))

            subscription._create_recurring_invoice()
            self.assertEqual(subscription.next_invoice_date, datetime.date(2024, 10, 1))

    def test_subscription_salesperson_propagates_to_company_child_contacts(self):
        """ Changing salesperson on a subscription linked to a company should propagate to all child contacts. """
        company_partner = self.env['res.partner'].create({'name': 'Test Company', 'is_company': True})
        contact_1 = self.env['res.partner'].create({'name': 'Contact 1', 'parent_id': company_partner.id})
        contact_2 = self.env['res.partner'].create({'name': 'Contact 2', 'parent_id': company_partner.id})
        subscription = self.env['sale.order'].create({
            'partner_id': company_partner.id,
            'plan_id': self.plan_month.id,
            'order_line': [Command.create({'product_id': self.product.id, 'product_uom_qty': 1})]
        })
        subscription.action_confirm()

        new_user = self.env['res.users'].create({'name': 'new user', 'login': 'new', 'email': 'new@test.com'})
        subscription.write({'user_id': new_user.id})
        self.assertEqual(new_user, company_partner.user_id, "Salesperson should be updated on the company partner.")
        self.assertEqual(new_user, contact_1.user_id, "Salesperson should be propagated to child contact 1.")
        self.assertEqual(new_user, contact_2.user_id, "Salesperson should be propagated to child contact 2.")

        new_user_2 = self.env['res.users'].create({'name': 'new user 2', 'login': 'new2', 'email': 'new2@test.com'})
        subscription.write({'user_id': new_user_2.id})
        self.assertEqual(new_user_2, company_partner.user_id, "Salesperson should be updated on the company partner after second change")
        self.assertEqual(new_user_2, contact_1.user_id, "Salesperson should be propagated to child contact 1 after second change")
        self.assertEqual(new_user_2, contact_2.user_id, "Salesperson should be propagated to child contact 2 after second change")
