# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _

from odoo.addons.account.controllers.portal import PortalAccount as CustomerPortal


class PortalAccount(CustomerPortal):

    def _prepare_my_account_rendering_values(self, *args, **kwargs):
        rendering_values = super()._prepare_my_account_rendering_values(*args, **kwargs)
        rendering_values['invoice_sending_methods'].update({'snailmail': _("by Post")})
        return rendering_values
