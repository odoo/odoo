from odoo.addons.google_account.controllers.main import GoogleAuth
from odoo.http import request


class GoogleCalendarAuth(GoogleAuth):

    def _post_google_auth_success_hook(self):
        request.env.user.sudo().google_synchronization_stopped = False
        events = request.env['calendar.event'].search(request.env['calendar.event']._get_sync_domain())
        events._check_alarm_ids_sync_limit()
        return super()._post_google_auth_success_hook()
