# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests import tagged, JsonRpcException
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.sale.controllers.portal import CustomerPortal as SaleCustomerPortal
from odoo.addons.sale_subscription.tests.test_sale_subscription import TestSubscriptionCommon
from odoo.addons.website.tools import MockRequest


@tagged('post_install', '-at_install')
class TestSubscriptionPaymentFlows(TestSubscriptionCommon, PaymentHttpCommon):

    @classmethod
    def setUpClass(cls, **kwargs):
        super().setUpClass(**kwargs)
        cls.order = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
        })
        cls.user_with_so_access = cls.env['res.users'].create({
            'groups_id': [(6, 0, [cls.env.ref('base.group_portal').id])],
            'login': 'user_a_pouet',
            'password': 'user_a_pouet',  # may the min password length burn in hell
            'name': 'User A',
        })
        cls.user_without_so_access = cls.env['res.users'].create({
            'groups_id': [(6, 0, [cls.env.ref('base.group_portal').id])],
            'login': 'user_b_pouet',
            'password': 'user_b_pouet',
            'name': 'User B',
        })
        # Portal access rule currently relies on mail follower(s) of the order
        cls.order._message_subscribe(partner_ids=[cls.user_with_so_access.partner_id.id])

    def test_tokenization_support_is_required(self):
        """ Test that tokenization support is required from both payment providers and payment
        methods when paying for a subscription on the portal. """
        if self.env['ir.module.module']._get('website').state != 'installed':
            self.skipTest("The website module is required to run this test with a request mock.")

        with MockRequest(self.env), patch(
            'odoo.addons.payment.models.payment_method.PaymentMethod'
            '._get_compatible_payment_methods'
        ) as patched:
            SaleCustomerPortal()._get_payment_values(self.subscription)
            self.assertTrue(patched.call_args.kwargs.get('force_tokenization'))

    def _my_sub_assign_token(self, **values):
        url = self._build_url(f"/my/subscriptions/assign_token/{self.order.id}")
        with mute_logger('odoo.addons.base.models.ir_rule', 'odoo.http'):
            return self.make_jsonrpc_request(url, params=values)

    def test_assign_token_route_with_so_access(self):
        """Test Assign Token Route with a user allowed to access the SO."""
        self.authenticate(self.user_with_so_access.login, self.user_with_so_access.login)
        dumb_token_so_user = self._create_token(
            partner_id=self.user_with_so_access.partner_id.id
        )
        _response = self._my_sub_assign_token(token_id=dumb_token_so_user.id)
        self.assertEqual(
            self.order.payment_token_id, dumb_token_so_user,
            "Logged Customer wasn't able to assign their token to their subscription."
        )

    def test_assign_token_without_so_access(self):
        """Test Assign Token Route with a user without access to the SO."""
        self.authenticate(
            self.user_without_so_access.login,
            self.user_without_so_access.login,
        )

        # 1) with access token
        own_token = self._create_token(
            partner_id=self.user_without_so_access.partner_id.id
        )
        response = self._my_sub_assign_token(
            token_id=own_token.id,
            access_token=self.order._portal_ensure_token(),
        )
        self.assertEqual(
            self.order.payment_token_id, own_token,
            "User wasn't able to assign their token to the subscription of another customer,"
            " even with the right access token.",
        )

        # 2) Without access token
        with self._assertNotFound():
            self._my_sub_assign_token(token_id=own_token.id)

        # 3) With wrong access token
        with self._assertNotFound():
            self._my_sub_assign_token(
                token_id=own_token.id,
                access_token="hohoho",
            )

    def test_assign_token_payment_token_access(self):
        self.authenticate(self.user_with_so_access.login, self.user_with_so_access.login)

        # correct token
        dumb_token_so_user = self._create_token(
            payment_details=f'token {self.user_with_so_access.name}',
            partner_id=self.user_with_so_access.partner_id.id,
        )
        _response = self._my_sub_assign_token(token_id=dumb_token_so_user.id)
        self.assertEqual(
            self.order.payment_token_id, dumb_token_so_user,
            "Logged Customer wasn't able to assign their token to their subscription."
        )

        # token of other user --> forbidden
        other_user_token = self._create_token(
            payment_details=f'token {self.user_without_so_access.name}',
            partner_id=self.user_without_so_access.partner_id.id,
        )
        with self.assertRaises(AccessError):
            # Make sure the test correctly tests what it should be testing
            # i.e. assigning a token not belonging to the user of the request
            other_user_token.with_user(self.user_with_so_access).read()

        with self._assertNotFound():
            self._my_sub_assign_token(token_id=other_user_token.id)

        # archived token --> forbidden
        archived_token = self._create_token(
            payment_details=f"archived token {self.user_with_so_access.name}",
            partner_id=self.user_with_so_access.partner_id.id,
        )
        archived_token.action_archive()
        with self._assertNotFound():
            self._my_sub_assign_token(token_id=archived_token.id)

        other_user_token.unlink()
        deleted_token_id = other_user_token.id

        with self._assertNotFound():
            self._my_sub_assign_token(token_id=deleted_token_id)

        self.assertEqual(
            self.order.payment_token_id, dumb_token_so_user,
            "Previous forbidden operations shouldn't have modified the SO token"
        )

    @mute_logger('odoo.http')
    def test_transaction_route_rejects_unexpected_kwarg(self):
        url = self._build_url(f'/my/subscriptions/{self.order.id}/transaction')
        route_kwargs = {
            'access_token': self.order._portal_ensure_token(),
            'partner_id': self.partner.id,  # This should be rejected.
        }
        with mute_logger("odoo.http"), self.assertRaises(
            JsonRpcException, msg='odoo.exceptions.ValidationError'
        ):
            self.make_jsonrpc_request(url, route_kwargs)
