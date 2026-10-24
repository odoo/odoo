from datetime import datetime

from odoo.addons.microsoft_account.controllers.main import MicrosoftAuth
from odoo.http import request


class MicrosoftCalendarAuth(MicrosoftAuth):

    def _post_microsoft_auth_success_hook(self):
        request.env.user.sudo().microsoft_last_sync_date = datetime.now()
        return super()._post_microsoft_auth_success_hook()
