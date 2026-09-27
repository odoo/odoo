from odoo.addons.microsoft_account.controllers.main import MicrosoftAuth
from odoo.http import request


class MicrosoftCalendarAuth(MicrosoftAuth):

    def _post_microsoft_auth_success_hook(self):
        request.env.user.sudo().microsoft_synchronization_stopped = False
        return super()._post_microsoft_auth_success_hook()
