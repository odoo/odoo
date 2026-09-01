# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, timedelta
from freezegun import freeze_time

from odoo import Command
from odoo.tests import JsonRpcException, tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.sale_loyalty.tests.common import TestSaleCouponCommon


@tagged('post_install', '-at_install')
class TestShopLoyaltyPayment(PaymentHttpCommon, TestSaleCouponCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.website = cls.env.company.website_id
        if not cls.website:
            cls.website = cls.env.ref('website.default_website')
            cls.website.company_id = cls.env.company

    @mute_logger('odoo.http')
    def test_expired_reward_validation(self):
        """Ensure payments don't process if any applied reward is no longer valid."""
        order = self.empty_order
        program = self.program_gift_card

        program.date_to = date.today()  # set program to expire after today
        self.product_a.type = 'service'  # prevent need for delivery method

        self.env['loyalty.generate.wizard'].with_context(active_id=program.id).create({
            'coupon_qty': 1,
            'points_granted': 100,
        }).generate_coupons()

        order.write({
            'partner_id': self.portal_partner.id,
            'website_id': self.website.id,
            'message_partner_ids': self.portal_partner.ids,
            'order_line': [Command.create({
                'product_id': self.product_a.id,
                'tax_id': None,
            })],
        })
        self._apply_promo_code(order, program.coupon_ids.code)

        with freeze_time(program.date_to + timedelta(days=1)):
            self.authenticate(self.portal_user.login, self.portal_user.login)
            with self.assertRaises(
                JsonRpcException,
                msg="Payment shouldn't succeed with expired reward",
            ):
                self.make_jsonrpc_request(
                    self._build_url(f'/shop/payment/transaction/{order.id}'),
                    {
                        'order_id': order.id,
                        'access_token': None,
                        'amount': order.amount_total,
                        'provider_id': self.provider.id,
                        'payment_method_id': self.payment_method.id,
                        'flow': 'direct',
                        'token_id': None,
                        'tokenization_requested': False,
                        'landing_route': order.get_portal_url(),
                    },
                )

            order._update_programs_and_rewards()
            tx_response = self.make_jsonrpc_request(
                self._build_url(f'/shop/payment/transaction/{order.id}'),
                {
                    'order_id': order.id,
                    'access_token': None,
                    'amount': order.amount_total,
                    'provider_id': self.provider.id,
                    'payment_method_id': self.payment_method.id,
                    'flow': 'direct',
                    'token_id': None,
                    'tokenization_requested': False,
                    'landing_route': order.get_portal_url(),
                },
            )
            self.assertEqual(
                tx_response['amount'],
                self.product_a.list_price,
                "Payment should succeed after removing expired reward",
            )

    def test_checkout_with_discount_and_avatax(self):
        if 'account_avatax' not in self.env['ir.module.module']._installed():
            self.skipTest("'account_avatax' is not installed")

        from odoo.addons.account_avatax.tests.common import TestAvataxCommon  # noqa: OLS03003, PLC0415

        avatax_category = self.env.ref('account_avatax.0040').id
        fpos = self.env["account.fiscal.position"].create({"is_avatax": True, "name": "avatax"})

        self.env.company.write({
            'avalara_api_id': 'dummy_api_id',
            'avalara_api_key': 'dummy_api_key',
            'avalara_environment': 'sandbox',
        })

        discount_program = self.env['loyalty.program'].create([{  # noqa: OLS03001
            'name': '10% off items',
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [
                Command.create({
                    'reward_point_amount': 1,
                    'reward_point_mode': 'unit',
                })
            ],
            'reward_ids': [
                Command.create({
                    'reward_type': 'discount',
                    'discount': 10.0,
                    'discount_applicability': 'specific',
                    'required_points': 1,
                })
            ],
        }])
        discount_program.reward_ids[0].discount_line_product_id.write({"avatax_category_id": avatax_category})

        shipping_product = self.env['product.product'].create({
            'name': 'Standard Delivery Fee',
            'type': 'service',
            'invoice_policy': 'order',
            'list_price': 0.00,
        })
        carrier = self.env['delivery.carrier'].create({  # noqa: OLS03001
            'name': 'Test Delivery Carrier',
            'delivery_type': 'fixed',
            'product_id': shipping_product.id,
            'fixed_price': 0.00,
        })
        self.product_A.write({"avatax_category_id": avatax_category, "list_price": 10})

        # Create sales order with is_tax_computed_externally set to true
        self.portal_partner.write({"zip": "90001", "country_id": self.env.ref("base.us").id, "state_id": self.env.ref("base.state_us_5").id})
        sale_order = self.empty_order
        sale_order.sudo().write({
            "partner_id": self.portal_partner.id,
            "fiscal_position_id": fpos.id,
            "order_line": [
                Command.create({
                    'product_id': self.product_A.id,
                    'product_uom_qty': 1,
                })
            ],
            "carrier_id": carrier.id,
        })

        # create the discount line in the sale order
        sale_order._update_programs_and_rewards()
        reward = discount_program.reward_ids[0]
        coupon = discount_program.coupon_ids[0]
        sale_order._apply_program_reward(reward, coupon)

        # this test is inspired by a ticket where client had AvaTax tax exempt customer giving an error, so we will model after it
        response = {
            'lines': [{'details': [{'jurisCode': '06', 'rate': 0.06, 'taxName': 'CA STATE TAX'},
                                    {'jurisCode': '075', 'rate': 0.0025, 'taxName': 'CA COUNTY TAX'},
                                    {'jurisCode': '57764', 'rate': 0.005, 'taxName': 'CA CITY TAX'},
                                    {'jurisCode': 'EMAN0', 'rate': 0.015, 'taxName': 'CA SPECIAL TAX'},
                                    {'jurisCode': 'EMTV0', 'rate': 0.01, 'taxName': 'CA SPECIAL TAX'}],
                        'lineAmount': line.price_subtotal,
                        'lineNumber': 'sale.order.line,' + str(line.id),
                        'tax': 0,
                        'exemptAmount': line.price_subtotal} for line in sale_order.order_line],
            'summary': [{'jurisCode': '06', 'exemption': 9.00, 'rate': 0.06, 'tax': 0, 'taxCalculated': 0, 'taxName': 'CA STATE TAX', 'taxable': 0},
                        {'jurisCode': '075', 'exemption': 9.00, 'rate': 0.0025, 'tax': 0, 'taxCalculated': 0, 'taxName': 'CA COUNTY TAX', 'taxable': 0},
                        {'jurisCode': '57764', 'exemption': 9.00, 'rate': 0.005, 'tax': 0, 'taxCalculated': 0, 'taxName': 'CA CITY TAX', 'taxable': 0},
                        {'jurisCode': 'EMAN0', 'exemption': 9.00, 'rate': 0.0015, 'tax': 0, 'taxCalculated': 0, 'taxName': 'CA SPECIAL TAX', 'taxable': 0},
                        {'jurisCode': 'EMTV0', 'exemption': 9.00, 'rate': 0.01, 'tax': 0, 'taxCalculated': 0, 'taxName': 'CA SPECIAL TAX', 'taxable': 0}]
        }

        with TestAvataxCommon._capture_request(return_value=response):
            sale_order._get_and_set_external_taxes_on_eligible_records()

        sale_order._portal_ensure_token()
        with TestAvataxCommon._capture_request(return_value=response):
            self.authenticate(self.portal_user.login, self.portal_user.login)
            self.make_jsonrpc_request(
                f'/shop/payment/transaction/{sale_order.id}',
                {
                    'access_token': sale_order.access_token,
                    'amount': 9,
                    'provider_id': self.provider.id,
                    'payment_method_id': self.payment_method_id,
                    'flow': 'direct',
                    'token_id': None,
                    'tokenization_requested': False,
                    'landing_route': sale_order.get_portal_url(),
                },
            )

        for line in sale_order.order_line:
            self.assertAlmostEqual(line.price_tax, 0.0, "The order line tax amount has been modified")
