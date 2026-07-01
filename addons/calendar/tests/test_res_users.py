# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import tagged, TransactionCase


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestResUsers(TransactionCase):

    def test_same_calendar_default_privacy_as_user_template(self):
        """
        The 'calendar default privacy' variable can be set in the Default User Template
        for defining which privacy the new user's calendars will have when creating a
        user. Ensure that when creating a new user, its calendar default privacy will
        have the same value as defined in the template.
        """
        def create_user(name, login, email):
            return self.env['res.users'].create({'name': name, 'login': login, 'email': email})

        # Get Default User Template and define expected outputs for each privacy update test.
        privacy_and_output = [
            (False, 'public'),
            ('public', 'public'),
            ('private', 'private'),
            ('confidential', 'confidential')
        ]
        for (privacy, expected_output) in privacy_and_output:
            # Update default privacy.
            if privacy:
                self.env['ir.config_parameter'].set_str("calendar.default_privacy", privacy)

            # If Calendar Default Privacy isn't defined in vals: get the privacy from Default User Template.
            username = 'test_%s_%s' % (str(privacy), expected_output)
            new_user = create_user(username, username, username + '@user.com')
            self.assertEqual(
                new_user.primary_calendar.calendar_default_privacy,
                expected_output,
                'Calendar default privacy %s should be %s, same as in the Default User Template.'
                % (new_user.primary_calendar.calendar_default_privacy, expected_output)
            )
