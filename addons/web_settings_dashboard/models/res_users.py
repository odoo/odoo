# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from openerp import models, api, _
from openerp.exceptions import RedirectWarning
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT


class Users(models.Model):
    _inherit = 'res.users'

    @api.model
    def web_dashboard_create_users(self, emails):

        # Reactivate already existing users if needed
        deactivated_users = self.with_context(active_test=False).search([('active', '=', False), '|', ('login', 'in', emails), ('email', 'in', emails)])
        for user in deactivated_users:
            user.active = True

        new_emails = set(emails) - set(deactivated_users.mapped('email'))

        # Process new email addresses : create new users
        for email in new_emails:
            default_values = {'login': email, 'name': email.split('@')[0], 'email': email, 'active': True}
            user = self.create(default_values)

        return True
