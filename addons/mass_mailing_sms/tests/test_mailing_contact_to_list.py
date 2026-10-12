# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mass_mailing.tests.common import MailingContactToListCommon
from odoo.addons.mass_mailing_sms.tests.common import MassSMSCommon
from odoo.tests import users, warmup


class TestMailingContactToListSms(MassSMSCommon, MailingContactToListCommon):

    @users('user_marketing')
    @warmup
    def test_from_partners_sms_create_link_and_match(self):
        """Create, link by mobile, partial overlap match, conflict, and duplicate resolution for SMS."""
        self.PHONE_NUMBERS = ['+32456998877', '+32456000000', '+32456999999', '+32495123456', '+32495654321']

        kate_partner, noah_partner, lea_partner, dave_partner, liam_partner, bob_partner = (
            self.env['res.partner'].create([
                {'name': 'Kate', 'phone': self.PHONE_NUMBERS[0]},
                {'name': 'Noah', 'email': 'noah@example.com', 'phone': self.PHONE_NUMBERS[1]},
                {'name': 'Lea', 'email': 'lea@example.com'},
                {'name': 'Dave', 'phone': self.PHONE_NUMBERS[3]},
                {'name': 'Liam', 'email': 'liam@example.com', 'phone': self.PHONE_NUMBERS[4]},
                {'name': 'Bob', 'email': 'bob@example.com', 'phone': self.PHONE_NUMBERS[4]},
            ])
        )
        kate_contact, noah_contact, lea_contact, _dave_contact, dave_dup_contact, _liam_contact = (
            self.env['mailing.contact'].create([
                {'name': 'Kate', 'mobile': self.PHONE_NUMBERS[0]},
                {'name': 'Noah', 'email': 'noah@example.com'},
                {'name': 'Lea', 'email': 'lea@example.com', 'mobile': self.PHONE_NUMBERS[2]},
                {'name': 'Dave', 'mobile': self.PHONE_NUMBERS[3]},
                {'name': 'Dave Duplicate', 'mobile': self.PHONE_NUMBERS[3]},
                {'name': 'Liam', 'email': 'liam@example.com', 'mobile': self.PHONE_NUMBERS[2]},
            ])
        )

        self._assert_from_partner_uses_contacts(kate_partner, kate_contact, query_count=6)
        self._assert_from_partner_uses_contacts(kate_partner, kate_contact, query_count=2)  # Already linked

        new_contact = self._assert_from_partner_creates_contacts(bob_partner, query_count=9)
        self.assertEqual(new_contact.mobile, bob_partner.phone)

        # Partial field overlaps match (non-conflicting subset of fields suffices)
        for case, partner, contact, query_count in zip(
                ('email+phone on partner, email-only on contact',
                 'email on partner, email+phone on contact'),
                (noah_partner, lea_partner),
                (noah_contact, lea_contact),
                (6, 6)
        ):
            with self.subTest(case=case):
                self._assert_from_partner_uses_contacts(partner, contact, query_count=query_count)

        self._assert_from_partner_creates_contacts(liam_partner, query_count=9, msg="New contact expected < phone conflict")
        self._assert_from_partner_uses_contacts(dave_partner, dave_dup_contact, msg="Most recent expected")
