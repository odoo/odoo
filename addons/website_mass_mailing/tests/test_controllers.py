# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
import odoo.tests


class TestSnippets(odoo.tests.HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.new_mailing_list = cls.env['mailing.list'].create({'name': 'test_subscribe_no_list'})
        cls.email_formatted = '"Ea-Nasir, Dilmun Goods" eanasir@urcopper.example.com'
        cls.email = 'eanasir@urcopper.example.com'
        cls.test_user = cls.env['res.users'].create({
            'email': cls.email_formatted,
            'group_ids': [Command.set([cls.env.ref('base.group_portal').id])],
            'name': 'Test User',
            'login': 'testuser',
            'password': 'testuser',
        })

    def test_subscribe_no_list(self):
        """Ensure subscription to removed/merged lists result in standalone contacts."""

        list_id = self.new_mailing_list.id
        self.new_mailing_list.unlink()

        self.assertFalse(self.env['mailing.list'].browse(list_id).exists(), 'Test assumption failed, list is not expected to exist')

        self.make_jsonrpc_request(
            '/website_mass_mailing/subscribe',
            {'list_id': list_id, 'subscription_type': 'email', 'value': self.email_formatted},
        )

        new_contact = self.env['mailing.contact'].search([('email', '=', self.email)], limit=1)
        self.assertTrue(new_contact, 'New contact should be created')
        self.assertFalse(new_contact.list_ids, 'Contact should not be in any list')

        # subscribe again
        self.make_jsonrpc_request(
            '/website_mass_mailing/subscribe',
            {'list_id': list_id, 'subscription_type': 'email', 'value': self.email_formatted},
        )

        self.assertFalse(new_contact.list_ids, 'Contact should not be in any list')

    def test_subscribe_authenticated_links_partner(self):
        """Ensure subscription as authenticated user links partner to new mailing contact."""
        other_email = 'other@example.com'
        self.new_mailing_list.is_public = True
        partner = self.test_user.partner_id
        # Unauthenticated
        self.make_jsonrpc_request(
            '/website_mass_mailing/subscribe',
            {'list_id': self.new_mailing_list.id, 'subscription_type': 'email', 'value': partner.email_normalized},
        )
        new_contact = self.env['mailing.contact'].search([('email_normalized', '=', partner.email_normalized)], limit=1)
        self.assertTrue(new_contact, 'New contact should be created')
        self.assertFalse(
            new_contact.partner_id,
            'Only authenticated users can link their partner to the mailing contact'
        )
        self.assertEqual(new_contact.list_ids, self.new_mailing_list)
        new_contact.unlink()

        self.authenticate('testuser', 'testuser')
        # Authenticated, enrolling neighbor
        self.make_jsonrpc_request(
            '/website_mass_mailing/subscribe',
            {'list_id': self.new_mailing_list.id, 'subscription_type': 'email', 'value': other_email},
        )
        new_contact = self.env['mailing.contact'].search([('email', '=', other_email)], limit=1)
        self.assertTrue(new_contact, 'New contact should be created')
        self.assertFalse(
            new_contact.partner_id,
            "Authenticated users should only be linked to the created mailing contact when subscribing with their email",
        )
        self.assertEqual(new_contact.list_ids, self.new_mailing_list)

        # Authenticated, Enrolling themselves
        self.make_jsonrpc_request(
            '/website_mass_mailing/subscribe',
            {'list_id': self.new_mailing_list.id, 'subscription_type': 'email', 'value': self.email_formatted},
        )
        new_contact = self.env['mailing.contact'].search([('email_normalized', '=', self.email)])
        self.assertTrue(new_contact, 'New contact should be created')
        self.assertEqual(new_contact.partner_id, partner)
        self.assertEqual(new_contact.list_ids, self.new_mailing_list)

    def test_subscribe_website_form_logs_subscription(self):
        """ Ensure subscribing through the website form logs the subscription
            in the chatter of the created mailing contact. """
        self.new_mailing_list.is_public = True
        self.assertFalse(self.env['mailing.contact'].search([
            ('email_normalized', '=', self.email),
        ]))

        self.authenticate('testuser', 'testuser')
        response = self.url_open('/website/form/mailing.contact', data={
            'csrf_token': self.csrf_token(),
            'email': self.email,
            'list_ids': str(self.new_mailing_list.id),
            'name': 'Test User',
        })
        contact = self.env['mailing.contact'].browse(response.json().get('id'))
        self.assertTrue(contact.exists())
        self.assertEqual(contact.partner_id, self.test_user.partner_id)
        self.assertEqual(contact.list_ids, self.new_mailing_list)
        self.assertIn(
            f'<p>{contact.display_name} subscribed to the following mailing list(s)</p>'
            f'<ul><li>{self.new_mailing_list.name}</li></ul>',
            contact.message_ids.mapped('body'),
        )
