# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment.tests.common import PaymentCommon


@tagged('-at_install', 'post_install')
class TestPaymentAcquirer(PaymentCommon):

    def test_published_acquirer_compatible_with_all_users(self):
        """ Test that a published acquirer is always available to all users. """
        for user in (self.public_user, self.portal_user):
            self.env = self.env(user=user)

            compatible_acquirers = self.env['payment.acquirer'].sudo()._get_compatible_acquirers(
                self.company.id, self.partner.id, self.amount
            )
            self.assertIn(self.acquirer, compatible_acquirers)

    def test_unpublished_acquirer_compatible_with_internal_user(self):
        """ Test that an unpublished acquirer is still available to internal users. """
        self.acquirer.is_published = False

        compatible_acquirers = self.env['payment.acquirer']._get_compatible_acquirers(
            self.company.id, self.partner.id, self.amount
        )
        self.assertIn(self.acquirer, compatible_acquirers)

    def test_unpublished_acquirer_not_compatible_with_non_internal_user(self):
        """ Test that an unpublished acquirer is not available to non-internal users. """
        self.acquirer.is_published = False
        for user in (self.public_user, self.portal_user):
            self.env = self.env(user=user)

            compatible_acquirers = self.env['payment.acquirer'].sudo()._get_compatible_acquirers(
                self.company.id, self.partner.id, self.amount
            )
            self.assertNotIn(self.acquirer, compatible_acquirers)

    def test_acquirer_compatible_when_maximum_amount_is_zero(self):
        """ Test that the maximum amount has no effect on the acquirer's compatibility when it is
        set to 0. """
        self.acquirer.maximum_amount = 0.

        compatible_acquirers = self.env['payment.acquirer']._get_compatible_acquirers(
            self.company.id, self.partner.id, self.amount, currency_id=self.env.company.currency_id.id,
        )
        self.assertIn(self.acquirer, compatible_acquirers)

    def test_acquirer_compatible_when_payment_below_maximum_amount(self):
        """ Test that an acquirer is compatible when the payment amount is less than the maximum
        amount. """
        self.acquirer.maximum_amount = self.amount + 10.0

        compatible_acquirers = self.env['payment.acquirer']._get_compatible_acquirers(
            self.company.id, self.partner.id, self.amount, currency_id=self.env.company.currency_id.id,
        )
        self.assertIn(self.acquirer, compatible_acquirers)

    def test_acquirer_not_compatible_when_payment_above_maximum_amount(self):
        """ Test that an acquirer is not compatible when the payment amount is more than the maximum
        amount. """
        self.acquirer.maximum_amount = self.amount - 10.0

        compatible_acquirers = self.env['payment.acquirer']._get_compatible_acquirers(
            self.company.id, self.partner.id, self.amount, currency_id=self.env.company.currency_id.id,
        )
        self.assertNotIn(self.acquirer, compatible_acquirers)
