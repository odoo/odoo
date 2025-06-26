from odoo import _
from odoo.addons.portal.controllers.portal import CustomerPortal


class PortalAccount(CustomerPortal):

    def _prepare_portal_layout_values(self):
        # EXTENDS 'portal'
        portal_layout_values = super()._prepare_portal_layout_values()
        portal_layout_values['invoice_sending_methods'].update({'snailmail': _('by Post')})
        return portal_layout_values
