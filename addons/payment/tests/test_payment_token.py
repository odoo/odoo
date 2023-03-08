# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.common import PaymentCommon


@tagged('-at_install', 'post_install')
class TestPaymentToken(PaymentCommon):

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_users_have_no_access_to_other_users_tokens(self):
        users = [self.public_user, self.portal_user, self.internal_user]
        token = self._create_token(partner_id=self.admin_partner.id)
        for user in users:
            with self.assertRaises(AccessError):
                token.with_user(user).read()

    def test_cannot_assign_token_to_public_partner(self):
        """ Test that no token can be assigned to the public partner. """
        token = self._create_token()
        with self.assertRaises(ValidationError):
            token.partner_id = self.public_user.partner_id

    def test_token_cannot_be_unarchived(self):
        """ Test that unarchiving disabled tokens is forbidden. """
        token = self._create_token(active=False)
        with self.assertRaises(UserError):
            token.active = True

    def test_display_name_is_padded(self):
        """ Test that the display name is built by padding the payment details. """
        token = self._create_token()
        self.assertEqual(token._build_display_name(), '•••• 1234')

    def test_display_name_for_empty_payment_details(self):
        """ Test that the display name is still built for token without payment details. """
        token = self._create_token(payment_details='')
        self.assertEqual(
            token._build_display_name(),
            f"Payment details saved on {date.today().strftime('%Y/%m/%d')}",
        )

    def test_display_name_is_shortened_to_max_length(self):
        """ Test that the display name is not fully padded when a `max_length` is passed. """
        token = self._create_token()
        self.assertEqual(token._build_display_name(max_length=6), '• 1234')

    def test_display_name_is_not_padded(self):
        """ Test that the display name is not padded when `should_pad` is `False`. """
        token = self._create_token()
        self.assertEqual(token._build_display_name(should_pad=False), '1234')
