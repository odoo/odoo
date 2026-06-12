from datetime import datetime

from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.tests import Form, tagged, users


@tagged('mailing_list')
class TestMailingContactToList(MassMailCommon):

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
        wizard_form.mailing_list_id = mailing
        wizard = wizard_form.save()
        frozen_time = datetime(2025, 1, 1, 0, 0)
        with self.mock_datetime_and_now(frozen_time):
            action = wizard.action_add_contacts()
            self.assertEqual(contacts.list_ids, mailing)
            create_dates = contacts.subscription_ids.mapped('create_date')
            self.assertTrue(all(date == frozen_time for date in create_dates), "All create dates should be equal to frozen datetime")
        self.assertEqual(action["type"], "ir.actions.act_window")
