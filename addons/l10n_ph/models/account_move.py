# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_open_l10n_ph_2307_wizard(self):
        vendor_bills = self.filtered_domain([('move_type', '=', 'in_invoice')])
        if vendor_bills:
            wizard_action = self.env["ir.actions.act_window"]._for_xml_id("l10n_ph.view_l10n_ph_2307_wizard_act_window")
            wizard_action.update({
                'context': {'default_moves_to_export': vendor_bills.ids}
            })
            return wizard_action
        else:
            raise UserError(_('Only Vendor Bills are available.'))
