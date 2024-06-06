from odoo.tests.common import TransactionCase


class TestResUsers(TransactionCase):

    def test_same_calendar_default_privacy_as_user_template(self):
        """
        The 'calendar default privacy' variable can be set in the Default User Template
        for defining which privacy the new user's calendars will have when creating a
        user. Ensure that when creating a new user, its calendar default privacy will
        have the same value as defined in the template.
        """
        def create_user(name, login, email, privacy=None):
            vals = {'name': name, 'login': login, 'email': email}
            if privacy is not None:
                vals['calendar_default_privacy'] = privacy
            return self.env['res.users'].create(vals)

        # Get Default User Template and define expected outputs for each privacy update test.
        default_user = self.env.ref('base.default_user', raise_if_not_found=False)
        privacy_and_output = [
            (False, 'public'),
            ('public', 'public'),
            ('private', 'private'),
            ('confidential', 'confidential')
        ]
        for (privacy, expected_output) in privacy_and_output:
            # Update privacy of Default User Template (required field).
            if privacy:
                default_user.write({'calendar_default_privacy': privacy})

            # If Calendar Default Privacy isn't defined in vals: get the privacy from Default User Template.
            username = 'test_%s_%s' % (str(privacy), expected_output)
            new_user = create_user(username, username, username + '@user.com')
            self.assertEqual(
                new_user.calendar_default_privacy,
                expected_output,
                'Calendar default privacy %s should be %s, same as in the Default User Template.'
                % (new_user.calendar_default_privacy, expected_output)
            )

            # If Calendar Default Privacy is defined in vals: override the privacy from Default User Template.
            for custom_privacy in ['public', 'private', 'confidential']:
                custom_name = str(custom_privacy) + username
                custom_user = create_user(custom_name, custom_name, custom_name + '@user.com', privacy=custom_privacy)
                self.assertEqual(
                    custom_user.calendar_default_privacy,
                    custom_privacy,
                    'Custom %s privacy from in vals must override the privacy %s from Default User Template.'
                    % (custom_privacy, privacy)
                )
