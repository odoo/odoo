# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestForm(HttpCase):

    def test_submit_send_a_copy_form_without_email(self):
        self.start_tour(
            self.env['website'].get_client_action_url('/'),
            'make_email_field_non_required',
            login='admin',
        )
        self.start_tour(
            self.env['website'].get_client_action_url('/'),
            'submit_form_without_email',
        )
        copy_mails = self.env['mail.mail'].search([('subject', '=', "Your answers on Form")])
        self.assertFalse(
            copy_mails,
            'No copy mail should be created when the email field is empty.'
        )
