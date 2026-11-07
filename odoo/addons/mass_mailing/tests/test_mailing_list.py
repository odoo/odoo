# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from freezegun import freeze_time
from unittest.mock import patch

from odoo import exceptions
from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.tests.common import Form, tagged, users


@tagged('mailing_list')
class TestMailingContactToList(MassMailCommon):

    @users('user_marketing')
    def test_mailing_contact_to_list(self):
        contacts = self.env['mailing.contact'].create([{
            'name': 'Contact %02d',
            'email': 'contact_%02d@test.example.com',
        } for x in range(30)])

        self.assertEqual(len(contacts), 30)
        self.assertEqual(contacts.list_ids, self.env['mailing.list'])

        mailing = self.env['mailing.list'].create({
            'name': 'Contacts Agregator',
        })

        # create wizard with context values
        wizard_form = Form(self.env['mailing.contact.to.list'].with_context(default_contact_ids=contacts.ids))
        self.assertEqual(wizard_form.contact_ids.ids, contacts.ids)

        # set mailing list and add contacts
        wizard_form.mailing_list_id = mailing
        wizard = wizard_form.save()
        action = wizard.action_add_contacts()
        self.assertEqual(contacts.list_ids, mailing)
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertTrue(action.get("params", {}).get("next"), "Should return a notification with a next action")
        subaction = action["params"]["next"]
        self.assertEqual(subaction["type"], "ir.actions.act_window_close")

        # set mailing list, add contacts and redirect to mailing view
        mailing2 = self.env['mailing.list'].create({
            'name': 'Contacts Sublimator',
        })

        wizard_form.mailing_list_id = mailing2
        wizard = wizard_form.save()
        action = wizard.action_add_contacts_and_send_mailing()
        self.assertEqual(contacts.list_ids, mailing + mailing2)
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertTrue(action.get("params", {}).get("next"), "Should return a notification with a next action")
        subaction = action["params"]["next"]
        self.assertEqual(subaction["type"], "ir.actions.act_window")
        self.assertEqual(subaction["context"]["default_contact_list_ids"], [mailing2.id])


@tagged('mailing_list')
class TestMailingListMerge(MassMailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailingListMerge, cls).setUpClass()
        cls._create_mailing_list()

        cls.mailing_list_3 = cls.env['mailing.list'].with_context(cls._test_context).create({
            'name': 'ListC',
            'contact_ids': [
                (0, 0, {'name': 'Norberto', 'email': 'norbert@example.com'}),
            ]
        })

    @users('user_marketing')
    def test_mailing_contact_create(self):
        default_list_ids = (self.mailing_list_2 | self.mailing_list_3).ids

        # simply set default list in context
        new = self.env['mailing.contact'].with_context(default_list_ids=default_list_ids).create([{
            'name': 'Contact_%d' % x,
            'email': 'contact_%d@test.example.com' % x,
        } for x in range(0, 5)])
        self.assertEqual(new.list_ids, (self.mailing_list_2 | self.mailing_list_3))

        # default list and subscriptions should be merged
        new = self.env['mailing.contact'].with_context(default_list_ids=default_list_ids).create([{
            'name': 'Contact_%d' % x,
            'email': 'contact_%d@test.example.com' % x,
            'subscription_ids': [(0, 0, {
                'list_id': self.mailing_list_1.id,
                'opt_out': True,
            }), (0, 0, {
                'list_id': self.mailing_list_2.id,
                'opt_out': True,
            })],
        } for x in range(0, 5)])
        self.assertEqual(new.list_ids, (self.mailing_list_1 | self.mailing_list_2 | self.mailing_list_3))
        # should correctly take subscription opt_out value
        for list_id in (self.mailing_list_1 | self.mailing_list_2).ids:
            new = new.with_context(default_list_ids=[list_id])
            self.assertTrue(all(contact.opt_out for contact in new))
        # not opt_out for new subscription without specific create values
        for list_id in self.mailing_list_3.ids:
            new = new.with_context(default_list_ids=[list_id])
            self.assertFalse(any(contact.opt_out for contact in new))

        with freeze_time('2022-01-01 12:00'), \
             patch.object(self.env.cr, 'now', lambda: datetime(2022, 1, 1, 12, 0, 0)):
            contact_form = Form(self.env['mailing.contact'])
            contact_form.name = 'Contact_test'
            with contact_form.subscription_ids.new() as subscription:
                subscription.list_id = self.mailing_list_1
                subscription.opt_out = True
            with contact_form.subscription_ids.new() as subscription:
                subscription.list_id = self.mailing_list_2
                subscription.opt_out = False
            contact = contact_form.save()
        self.assertEqual(contact.subscription_ids[0].opt_out_datetime, datetime(2022, 1, 1, 12, 0, 0))
        self.assertFalse(contact.subscription_ids[1].opt_out_datetime)

    @users('user_marketing')
    def test_mailing_list_action_send_mailing(self):
        mailing_ctx = self.mailing_list_1.action_send_mailing().get('context', {})
        form = Form(self.env['mailing.mailing'].with_context(mailing_ctx))
        form.subject = 'Test Mail'
        mailing = form.save()
        # Check that mailing model and mailing list are set properly
        self.assertEqual(
            mailing.mailing_model_id, self.env['ir.model']._get('mailing.list'),
            'Should have correct mailing model set')
        self.assertEqual(mailing.contact_list_ids, self.mailing_list_1, 'Should have correct mailing list set')
        self.assertEqual(mailing.mailing_type, 'mail', 'Should have correct mailing_type')

    @users('user_marketing')
    def test_mailing_list_contact_copy_in_context_of_mailing_list(self):
        MailingContact = self.env['mailing.contact']
        contact_1 = MailingContact.create({
            'name': 'Sam',
            'email': 'gamgee@shire.com',
            'subscription_ids': [(0, 0, {'list_id': self.mailing_list_3.id})],
        })
        # Copy the contact with default_list_ids in context, which should not raise anything
        contact_2 = contact_1.with_context(default_list_ids=self.mailing_list_3.ids).copy()
        self.assertEqual(contact_1.list_ids, contact_2.list_ids, 'Should copy the existing mailing list(s)')

    @users('user_marketing')
    def test_mailing_list_merge(self):
        # TEST CASE: Merge A,B into the existing mailing list C
        # The mailing list C contains the same email address than 'Norbert' in list B
        # This test ensure that the mailing lists are correctly merged and no
        # duplicates are appearing in C
        merge_form = Form(self.env['mailing.list.merge'].with_context(
            active_ids=[self.mailing_list_1.id, self.mailing_list_2.id],
            active_model='mailing.list'
        ))
        merge_form.new_list_name = False
        merge_form.merge_options = 'existing'
        # Need to set `merge_options` before `dest_lid_id` so `dest_list_id` is visible
        # `'invisible': [('merge_options', '=', 'new')]`
        merge_form.dest_list_id = self.mailing_list_3
        merge_form.archive_src_lists = False
        result_list = merge_form.save().action_mailing_lists_merge()

        # Assert the number of contacts is correct
        self.assertEqual(
            len(result_list.contact_ids.ids), 5,
            'The number of contacts on the mailing list C is not equal to 5')

        # Assert there's no duplicated email address
        self.assertEqual(
            len(list(set(result_list.contact_ids.mapped('email')))), 5,
            'Duplicates have been merged into the destination mailing list. Check %s' % (result_list.contact_ids.mapped('email')))

    @users('user_marketing')
    def test_mailing_list_merge_cornercase(self):
        """ Check wrong use of merge wizard """
        with self.assertRaises(exceptions.UserError):
            merge_form = Form(self.env['mailing.list.merge'].with_context(
                active_ids=[self.mailing_list_1.id, self.mailing_list_2.id],
            ))

        merge_form = Form(self.env['mailing.list.merge'].with_context(
            active_ids=[self.mailing_list_1.id],
            active_model='mailing.list',
            default_src_list_ids=[self.mailing_list_1.id, self.mailing_list_2.id],
            default_dest_list_id=self.mailing_list_3.id,
            default_merge_options='existing',
        ))
        merge = merge_form.save()
        self.assertEqual(merge.src_list_ids, self.mailing_list_1 + self.mailing_list_2)
        self.assertEqual(merge.dest_list_id, self.mailing_list_3)


@tagged('mailing_list')
class TestMailingContactImport(MassMailCommon):
    """Test the transient <mailing.contact.import>."""

    @users('user_marketing')
    def test_mailing_contact_import(self):
        first_list, second_list, third_list = self.env['mailing.list'].create([
            {'name': 'First mailing list'},
            {'name': 'Second mailing list'},
            {'name': 'Third mailing list'},
        ])

        self.env['mailing.contact'].create([
            {
                'name': 'Already Exists',
                'email': 'already_exists_list_1@example.com',
                'list_ids': first_list.ids,
            }, {
                'email': 'already_exists_list_2@example.com',
                'list_ids': second_list.ids,
            }, {
                'email': 'already_exists_list_1_and_2@example.com',
                'list_ids': (first_list | second_list).ids,
            },
        ])

        self.env['mailing.mailing'].create({
            'name': 'Test',
            'subject': 'Test',
            'contact_list_ids': (first_list | second_list).ids,
        })

        contact_import = Form(self.env['mailing.contact.import'].with_context(
            default_mailing_list_ids=first_list.ids,
        ))

        contact_import.contact_list = '''
            invalid line1
            alice@example.com
            bob@example.com
            invalid line2
            "Bob" <bob@EXAMPLE.com>
            "Test" <bob@example.com>

            invalid line3, with a comma
            already_exists_list_1@example.com
            already_exists_list_2@example.com
            "Test" <already_exists_list_1_and_2@example.com>
            invalid line4
        '''
        contact_import = contact_import.save()

        self.assertEqual(contact_import.mailing_list_ids, first_list)

        # Can not add many2many directly on a Form
        contact_import.mailing_list_ids |= third_list

        self.assertEqual(len(first_list.contact_ids), 2, 'Should not yet create the contact')
        self.assertEqual(len(second_list.contact_ids), 2, 'Should not yet create the contact')
        self.assertEqual(len(third_list.contact_ids), 0, 'Should not yet create the contact')

        # Test that the context key "default_list_ids" is ignored (because we manually set list_ids)
        contact_import.with_context(default_list_ids=(first_list | second_list).ids).action_import()

        self.env['mailing.list'].invalidate_model(['contact_ids'])
        # Check the contact of the first mailing list
        contacts = [
            (contact.name, contact.email)
            for contact in first_list.contact_ids
        ]
        self.assertIn(('', 'alice@example.com'), contacts, 'Should have imported the right email address')
        self.assertIn(('Bob', 'bob@example.com'), contacts, 'Should have imported the name of the contact')
        self.assertIn(
            ('', 'already_exists_list_2@example.com'), contacts,
            'The email already exists but in a different list. The contact must be imported.')
        self.assertEqual(len(second_list.contact_ids), 2, 'Should have ignored default_list_ids')
        self.assertNotIn(('Test', 'bob@example.com'), contacts, 'Should have ignored duplicated')
        self.assertNotIn(('', 'bob@example.com'), contacts, 'Should have ignored duplicated')
        self.assertNotIn(('Test', 'already_exists_list_1_and_2@example.com'), contacts, 'Should have ignored duplicated')
        self.assertEqual(len(contacts), 5, 'Should have imported 2 new contacts')

        # Check the contact of the third mailing list
        contacts = [
            (contact.name, contact.email)
            for contact in third_list.contact_ids
        ]
        self.assertIn(('', 'alice@example.com'), contacts, 'Should have imported the right email address')
        self.assertIn(('Bob', 'bob@example.com'), contacts, 'Should have imported the name of the contact')
        self.assertIn(
            ('', 'already_exists_list_2@example.com'), contacts,
            'The email already exists but in a different list. The contact must be imported.')
        self.assertIn(('Already Exists', 'already_exists_list_1@example.com'), contacts, 'This contact exists in the first mailing list, but not in the third mailing list')
        self.assertNotIn(('Test', 'already_exists_list_1_and_2@example.com'), contacts, 'Should have ignored duplicated')

        contact = self.env['mailing.contact'].search([('email', '=', 'already_exists_list_1@example.com')])
        self.assertEqual(len(contact), 1, 'Should have updated the existing contact instead of creating a new one')


@tagged('mailing_list')
class TestSubscriptionManagement(MassMailCommon):

    @users('user_marketing')
    def test_mailing_update_optout(self):
        _email_formatted = '"Mireille Labeille" <mireille@test.example.com>'
        _email_formatted_upd = '"Mireille Oreille-Labeille" <mireille@test.example.com>'
        _email_normalized = 'mireille@test.example.com'
        self._create_mailing_list()
        ml_1, ml_2 = self.mailing_list_1.with_env(self.env), self.mailing_list_2.with_env(self.env)
        ml_3 = self._create_mailing_list_of_x_contacts(3)
        self.assertEqual(ml_1.contact_count, 3)
        self.assertEqual(ml_1.contact_count_blacklisted, 0)
        self.assertEqual(ml_1.contact_count_email, 3)
        self.assertEqual(ml_1.contact_count_opt_out, 0)
        self.assertEqual(ml_2.contact_count, 4)
        self.assertEqual(ml_2.contact_count_blacklisted, 0)
        self.assertEqual(ml_2.contact_count_email, 4)
        self.assertEqual(ml_2.contact_count_opt_out, 0)
        self.assertEqual(ml_3.contact_count, 3)
        self.assertEqual(ml_3.contact_count_blacklisted, 0)
        self.assertEqual(ml_3.contact_count_email, 3)
        self.assertEqual(ml_3.contact_count_opt_out, 0)

        # create a new test contact
        contact = self.env['mailing.contact'].browse(
            self.env['mailing.contact'].name_create(_email_formatted)[0]
        )
        self.assertEqual(contact.email, _email_normalized)
        self.assertEqual(contact.name, 'Mireille Labeille')

        # add new subscriptions (and ensure email_normalized is used)
        (ml_1 + ml_2)._update_subscription_from_email(_email_formatted_upd, opt_out=False)
        subs = self.env['mailing.subscription'].search(
            [('contact_id', '=', contact.id)]
        )
        self.assertEqual(subs.list_id, ml_1 + ml_2)

        # opt-out from opted-in mailing list + 1 non opted-in mailing list
        (ml_2 + ml_3)._update_subscription_from_email(_email_formatted_upd, opt_out=True)
        subs = self.env['mailing.subscription'].search(
            [('contact_id', '=', contact.id)]
        )
        self.assertEqual(subs.list_id, ml_1 + ml_2)
