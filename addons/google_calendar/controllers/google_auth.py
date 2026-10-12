from odoo.addons.google_account.controllers.main import GoogleAuth
from odoo.http import request


class GoogleCalendarAuth(GoogleAuth):

    def _post_google_auth_success_hook(self):
        request.env.user.sudo().google_synchronization_stopped = False
        return super()._post_google_auth_success_hook()
