from odoo.http import request

from odoo.addons.account.controllers.portal import PortalAccount as CustomerPortal


class PortalAccount(CustomerPortal):
    def _prepare_my_account_rendering_values(self, *args, **kwargs):
        rendering_values = super()._prepare_my_account_rendering_values(*args, **kwargs)
        rendering_values["invoice_sending_methods"].update(
            {"snailmail": request.env._("by Post")}
        )
        return rendering_values
