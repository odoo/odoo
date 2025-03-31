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

    def test_avoid_res_users_settings_creation_portal(self):
        """
        This test ensures that 'res.users.settings' entries are not created for portal
        and public users through the new 'calendar_default_privacy' field, since it is
        not useful tracking these fields for non-internal users.
        """
        username_and_group = {
            'PORTAL': 'base.group_portal',
            'PUBLIC': 'base.group_public',
        }

        for username, group in username_and_group.items():
            # Create user and impersonate it as sudo for triggering the compute.
            user = self.env['res.users'].create({
                'name': username,
                'login': username,
                'email': username + '@email.com',
                'groups_id': [(6, 0, [self.env.ref(group).id])]
            })
            user.with_user(user).sudo()._compute_calendar_default_privacy()

            # Ensure default privacy fallback and also that no 'res.users.settings' entry got created.
            self.assertEqual(
                user.calendar_default_privacy, 'public',
                "Calendar default privacy of %s users must fallback to 'public'." % (username)
            )
            self.assertFalse(
                user.sudo().res_users_settings_id,
                "No res.users.settings record must be created for '%s' users." % (username)
            )
