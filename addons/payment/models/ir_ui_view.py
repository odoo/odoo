# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import UserError


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    @api.ondelete(at_uninstall=False)
    def _unlink_if_not_referenced_by_provider(self):
        referencing_providers_sudo = self.env['payment.provider'].sudo().search([
            '|', ('redirect_form_view_id', 'in', self.ids), ('inline_form_view_id', 'in', self.ids)
        ])  # In sudo mode to allow non-admin users (e.g., Website designers) to read the view ids.
        if referencing_providers_sudo:
            raise UserError(_("You cannot delete a view that is used by a payment provider."))
