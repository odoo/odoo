# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import UserError


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    @api.ondelete(at_uninstall=False)
    def _unlink_if_not_referenced_by_acquirer(self):
        referencing_acquirers = self.env['payment.acquirer'].search([
            '|', ('redirect_form_view_id', 'in', self.ids), ('inline_form_view_id', 'in', self.ids)
        ])
        if referencing_acquirers:
            raise UserError(_("You cannot delete a view that is used by a payment acquirer."))
