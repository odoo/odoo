from odoo.addons.google_account.controllers.main import GoogleAuth


class MicrosoftCalendarAuth(GoogleAuth):

    def _post_google_auth_hook(self, auth_request):
        auth_request.env.user.sudo().google_synchronization_stopped = False
        return super()._post_google_auth_hook(auth_request)
