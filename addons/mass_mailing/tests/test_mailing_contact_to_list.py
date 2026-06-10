from datetime import datetime

from odoo import Command, exceptions
from odoo.addons.mass_mailing.tests.common import MailingContactToListCommon
from odoo.tests import Form, RecordCapturer, tagged, users, warmup


@tagged('mailing_list')
class TestMailingContactToList(MailingContactToListCommon):

    @users('user_marketing')
    @warmup
    def test_from_partners_and_compute_use_context_contact(self):
        mailing_list_context = {'default_list_ids': self.mailing_list_1.ids}

        partner = self.env['res.partner'].create({
            'name': 'Already Linked',
            'email': 'prelinked_context@test.example.com',
        })
        more_subs, many_subs_unsynced, current_list_opt_out = contacts = self.env['mailing.contact'].create([
            {
                'name': 'More Subs',
                'email': 'prelinked_context@test.example.com',
                'partner_id': partner.id,
                'subscription_ids': [
                    Command.create({'list_id': self.mailing_list_2.id}),
                    Command.create({'list_id': self.mailing_list_3.id}),
                ],
            },
            {
                'name': 'More Subs Unsynced',
                'email': 'prelinked_context_unsynced@test.example.com',
                'partner_id': partner.id,
                'subscription_ids': [
                    Command.create({'list_id': self.mailing_list_1.id}),
                    Command.create({'list_id': self.mailing_list_2.id}),
                    Command.create({'list_id': self.mailing_list_3.id}),
                ],
            },
            {
                'name': 'Subscribed',
                'email': 'prelinked_context@test.example.com',
                'partner_id': partner.id,
                'subscription_ids': [Command.create({'list_id': self.mailing_list_1.id, 'opt_out': True})],
            },
        ])

        self.assertEqual(more_subs._get_sort_key(
            self.mailing_list_1.id, partner=more_subs.partner_id),
            (False, False, 2, 1, more_subs.id))
        self.assertEqual(many_subs_unsynced._get_sort_key(
            self.mailing_list_1.id, partner=many_subs_unsynced.partner_id),
            (False, True, 3, 0, many_subs_unsynced.id))
        self.assertEqual(current_list_opt_out._get_sort_key(
            self.mailing_list_1.id, partner=current_list_opt_out.partner_id),
            (True, True, 0, 1, current_list_opt_out.id))

        self.assertEqual(partner.mailing_contact_ids, contacts)
        self.assertEqual(partner.mailing_contact_id, many_subs_unsynced,
                         'Contact with most subs should be preferred.')
        self.assertEqual(
            partner.with_context(mailing_list_context).mailing_contact_id, current_list_opt_out,
            'Contact opted out of context list should be preferred in _compute_mailing_contact_id.')

        with RecordCapturer(self.env['mailing.contact']) as capture:
            res_contacts, _ = self.env['mailing.contact'].with_context(mailing_list_context)._from_partners(partner)

        self.assertFalse(capture.records)
        self.assertEqual(res_contacts, current_list_opt_out,
                         'Contact opted out of context list should be preferred in _from_partners.')

        (many_subs_unsynced | current_list_opt_out).unlink()
        self.assertEqual(partner.mailing_contact_ids, more_subs)
        self.assertFalse(partner.with_context(mailing_list_context).mailing_contact_id)

    @users('user_marketing')
    @warmup
    def test_from_partners_create_or_link(self):
        partner_1, partner_2, partner_3, partner_4, partner_5, partner_6 = self.env['res.partner'].create([
            {'name': 'Alice', 'email': 'alice@test.example.com'},
            {'name': 'Bob', 'email': 'bob@test.example.com'},
            {'name': 'Grace', 'email': 'grace@test.example.com'},
            {'name': 'Henry', 'email': 'henry@test.example.com'},
            {'name': 'Iris', 'email': 'iris@test.example.com'},
            {'name': 'Jack', 'email': 'jack@test.example.com'},
        ])
        contact_1, contact_2, contact_4, contact_5 = self.env['mailing.contact'].create([
            {'name': 'Alice', 'email': 'alice@test.example.com', 'partner_id': partner_1.id},
            {'name': 'Bob', 'email': 'bob@test.example.com'},
            {'name': 'Henry', 'email': 'henry@test.example.com', 'partner_id': partner_4.id},
            {'name': 'Iris', 'email': 'iris@test.example.com'}
        ])

        self._assert_from_partner_uses_contacts(partner_1, contact_1, query_count=2)  # Already linked
        self._assert_from_partner_uses_contacts(partner_2, contact_2, query_count=7)  # Search & link
        new_contact = self._assert_from_partner_creates_contacts(partner_3, query_count=8)
        self.assertEqual(new_contact.email, partner_3.email)

        # And in batch
        (res_contacts, _), new_contact = self._mock_from_partners_with_capture(partner_4 | partner_6 | partner_5, 10)
        self.assertEqual(new_contact.partner_id, partner_6)
        self.assertEqual(res_contacts, (contact_4 | new_contact | contact_5))

    @users('user_marketing')
    @warmup
    def test_from_partners_duplicate_partners_to_one_contact(self):
        partner_one, partner_newer_duplicate = partners = self.env['res.partner'].create([
            {'name': 'Older', 'email': 'shared@test.example.com'},
            {'name': 'Newer', 'email': 'shared@test.example.com'},
        ])
        contact = self.env['mailing.contact'].create({
            'name': 'Shared',
            'email': 'shared@test.example.com',
        })

        (res_contacts, _), new_contacts = self._mock_from_partners_with_capture(partners, 6)
        self.assertFalse(new_contacts)
        self.assertEqual(contact.partner_id, partner_newer_duplicate, 'Newest partner should have been linked.')
        self.assertEqual(res_contacts, contact)

        contact.partner_id = partner_one

        (res_contacts, _), new_contacts = self._mock_from_partners_with_capture(partner_newer_duplicate, 3)
        self.assertFalse(new_contacts)
        self.assertEqual(res_contacts, contact, 'Contact should have been returned even if not linked to the partner.')
        self.assertEqual(contact.partner_id, partner_one, 'Existing partner_id should have persisted.')

    @users('user_marketing')
    @warmup
    def test_from_partners_mixed_many(self):
        """Check the limit and performance of calling _from_partners on lots of partners with matchable contacts."""
        vals = [
            {"name": f"Name {idx}", "email": f"email_{idx}@test.example.com"}
            for idx in range(self.MAX_FROM_PARTNERS * 2)
        ]
        partners = self.env["res.partner"].create(vals)
        contacts = self.env["mailing.contact"].create(vals[: self.MAX_FROM_PARTNERS])

        with self.assertRaises(exceptions.UserError):
            self._mock_from_partners_with_capture(partners[:self.MAX_FROM_PARTNERS + 1], 1)

        self._assert_from_partner_uses_contacts(partners[:self.MAX_FROM_PARTNERS], contacts, query_count=9)

        # only half to create now => no error even with all partners in input.
        (res_contacts, _), capture_records = self._mock_from_partners_with_capture(partners, 14)

        self.assertEqual(len(res_contacts), len(partners))
        self.assertEqual(res_contacts.partner_id, partners)
        new_records = res_contacts - contacts
        self.assertEqual(capture_records, new_records)
        self.assertEqual(len(new_records), self.MAX_FROM_PARTNERS)

    @users('user_marketing')
    @warmup
    def test_from_partners_no_link_unmatchable(self):
        """Check that conflicts prevent matching, while duplicates are resolved."""
        (
            partner_frank, partner_charlie_1, partner_charlie_2, partner_charlie_3,
            partner_eve_1, _partner_eve_2, partner_dave
        ) = self.env['res.partner'].create([
            {'name': 'Frank'},
            {'name': 'Charlie 1', 'email': 'charlie_a@test.example.com'},
            {'name': 'Charlie 2', 'email': 'charlie_a@test.example.com'},
            {'name': 'Charlie 3', 'email': 'charlie_b@test.example.com'},
            {'name': 'Eve 1', 'email': 'eve@test.example.com'},
            {'name': 'Eve 2', 'email': 'eve@test.example.com'},
            {'name': 'Dave', 'email': 'dave@test.example.com'},
        ])
        (
            _contact_frank, _contact_charlie, contact_eve, _contact_dave_1, contact_dave_2
        ) = self.env['mailing.contact'].create([
            {'name': 'Frank'},
            {'name': 'Charlie 3', 'email': 'charlie_not_b@test.example.com'},
            {'name': 'Eve', 'email': 'eve@test.example.com'},
            {'name': 'Dave', 'email': 'dave@test.example.com'},
            {'name': 'Dave Duplicate', 'email': 'dave@test.example.com'},
         ])
        partners = partner_frank | partner_charlie_1 | partner_charlie_2
        (res_contacts, nb_ignored), new_contacts = self._mock_from_partners_with_capture(partners, 8)
        self.assertEqual(nb_ignored, 1, "No contact should be returned created for a partner with no email.")
        self.assertEqual(len(new_contacts), 1, "No contact should be created for partner without email.")
        self.assertEqual(new_contacts.partner_id, partner_charlie_2)
        self.assertEqual(res_contacts, new_contacts)
        self._assert_from_partner_uses_contacts(partner_eve_1, contact_eve, query_count=6)
        self._assert_from_partner_creates_contacts(partner_charlie_3, query_count=8)
        self._assert_from_partner_uses_contacts(
            partner_dave, contact_dave_2, msg='Most recent contact should have been linked')

    @users('user_marketing')
    def test_from_partners_prefer_contact_already_subscribed_to_context_list(self):
        mailing_list_context = {"default_list_ids": self.mailing_list_1.ids}

        partner = self.env['res.partner'].create({'name': 'Partner', 'email': 'partner@test.example.com'})
        subscribed_contact, newer_contact = self.env['mailing.contact'].create([
            {
                'name': 'Subscribed',
                'email': 'partner@test.example.com',
                'subscription_ids': [(0, 0, {
                    'list_id': self.mailing_list_1.id,
                    'opt_out': True,
                })],
            },
            {'name': 'Newer Duplicate', 'email': 'partner@test.example.com'},
        ])

        with RecordCapturer(self.env['mailing.contact']) as capture:
            contacts, _ = self.env['mailing.contact'].with_context(mailing_list_context)._from_partners(partner)

        self.assertFalse(capture.records)
        self.assertEqual(contacts, subscribed_contact)
        self.assertEqual(subscribed_contact.partner_id, partner)
        self.assertEqual(newer_contact.partner_id, partner)
        self.assertTrue(
            subscribed_contact.subscription_ids.filtered(
                lambda subscription: subscription.list_id == self.mailing_list_1
            ).opt_out
        )
        self.assertEqual(subscribed_contact._get_sort_key(self.mailing_list_1.id), (1, 1, 0, 0, subscribed_contact.id))
        self.assertEqual(newer_contact._get_sort_key(self.mailing_list_1.id), (0, 0, 0, 0, newer_contact.id))

    @users('user_marketing')
    @warmup
    def test_from_partners_wizard_multiple_lists(self):
        """Check subscriptions, notifications, and query performance when adding partners to multiple lists."""
        n_new, n_sub_all, n_tot = 40, 40, 80
        all_mailing_lists = self.mailing_list_1 | self.mailing_list_2
        vals_list = [{'name': f'Partner {idx}', 'email': f'partner_{idx}@test.example.com'} for idx in range(n_tot)]
        all_partners = self.env['res.partner'].create(vals_list)
        all_contacts = self.env['mailing.contact'].create(
            [vals | {'partner_id': all_partners[idx].id} for idx, vals in enumerate(vals_list)]
        )
        contacts_no_sub, contacts_all_sub = all_contacts[:n_new], all_contacts[-n_sub_all:]
        partners_no_sub, all_partners = contacts_no_sub.partner_id, all_contacts.partner_id
        self.assertEqual(len(all_contacts), len(all_partners))

        self.env['mailing.subscription'].create(
            [{'contact_id': c.id, 'list_id': lst.id} for c in contacts_all_sub for lst in all_mailing_lists]
        )

        for idx, (case, mailing_lists, partners, exp_type, exp_message, query_count) in enumerate([
            ('20 subs() -> 1', self.mailing_list_1, partners_no_sub[:20], 'success', '20 added', 7),
            ('20 subs() -> 1+2', all_mailing_lists, partners_no_sub[20:], 'success', '20 added', 11),
            ('20 sub(1) -> 1+2', all_mailing_lists, partners_no_sub[:20], 'success',
             '20 added%(NOTIF_NEWLINE)s1 opted out', 10),
            ('80 sub(1, 2) -> 1+2', all_mailing_lists, all_partners, 'info',
             '0 added%(NOTIF_NEWLINE)s80 already subscribed%(NOTIF_NEWLINE)s1 opted out', 9),
        ]):
            with self.subTest(case=case):
                if idx == 2:
                    partners_no_sub[0].mailing_contact_ids.subscription_ids.filtered(
                        lambda s: s.list_id == self.mailing_list_1
                    ).opt_out = True

                all_partners.invalidate_recordset()
                all_contacts.invalidate_recordset()
                all_mailing_lists.invalidate_recordset()
                self.env['mailing.subscription'].invalidate_model()

                wizard = self.env['mailing.contact.to.list'].create(
                    {'partner_ids': partners.ids, 'mailing_list_ids': mailing_lists.ids})
                with (RecordCapturer(self.env['mailing.contact']) as contact_capture,
                        self.assertQueryCount(query_count)):
                    action = wizard._action_add_res_partners()

                self.assertFalse(len(contact_capture.records))
                notification = action['params']['notification']
                self.assertEqual(notification['type'], exp_type)
                self.assertIn(exp_message, notification['message'])

    @users('user_marketing')
    def test_mailing_contact_to_list(self):
        contacts = self.env['mailing.contact'].create([{
            'name': 'Contact %02d',
            'email': 'contact_%02d@test.example.com',
        } for __ in range(30)])

        self.assertEqual(len(contacts), 30)
        self.assertEqual(contacts.list_ids, self.env['mailing.list'])

        mailing = self.env['mailing.list'].create({
            'name': 'Contacts Agregator',
        })

        # create wizard with context values
        wizard_form = Form(self.env['mailing.contact.to.list'].with_context(default_contact_ids=contacts.ids))
        self.assertEqual(wizard_form.contact_ids.ids, contacts.ids)

        # set mailing list and add contacts
        wizard_form.mailing_list_ids.add(mailing)
        wizard = wizard_form.save()
        frozen_time = datetime(2025, 1, 1, 0, 0)
        with self.mock_datetime_and_now(frozen_time):
            action = wizard.action_add_contacts()
            self.assertEqual(contacts.list_ids, mailing)
            create_dates = contacts.subscription_ids.mapped('create_date')
            self.assertTrue(all(date == frozen_time for date in create_dates), "All create dates should be equal to frozen datetime")
        self.assertEqual(action["type"], "ir.actions.act_window")
