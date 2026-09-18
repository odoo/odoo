from odoo.addons.microsoft_account.controllers.main import MicrosoftAuth


class MicrosoftCalendarAuth(MicrosoftAuth):

    def _post_microsoft_auth_hook(self, auth_request):
        auth_request.env.user.sudo().microsoft_synchronization_stopped = False
        return super()._post_microsoft_auth_hook(auth_request)
