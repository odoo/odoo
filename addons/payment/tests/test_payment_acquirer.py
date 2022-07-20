# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment.tests.common import PaymentCommon


@tagged('-at_install', 'post_install')
class TestPaymentAcquirer(PaymentCommon):

    def test_published_acquirer_compatible_with_all_users(self):
        for user in (self.public_user, self.portal_user):
            self.env = self.env(user=user)

            compatible_acquirers = self.env['payment.acquirer'].sudo()._get_compatible_acquirers(
                self.company.id, self.partner.id
            )
        self.assertIn(self.acquirer, compatible_acquirers)

    def test_unpublished_acquirer_compatible_with_internal_user(self):
        self.acquirer.is_published = False

        compatible_acquirers = self.env['payment.acquirer']._get_compatible_acquirers(
            self.company.id, self.partner.id
        )
        self.assertIn(self.acquirer, compatible_acquirers)

    def test_unpublished_acquirer_not_compatible_with_non_internal_user(self):
        self.acquirer.is_published = False
        for user in (self.public_user, self.portal_user):
            self.env = self.env(user=user)

            compatible_acquirers = self.env['payment.acquirer'].sudo()._get_compatible_acquirers(
                self.company.id, self.partner.id
            )
        self.assertNotIn(self.acquirer, compatible_acquirers)
