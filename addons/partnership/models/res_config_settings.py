# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    partnership_label = fields.Char(related='company_id.partnership_label', required=True, readonly=False)

    @api.onchange('partnership_label')
    def _onchange_partnership_label(self):
        crm_menu = self.env.ref('partnership.crm_menu_partners', raise_if_not_found=False)
        if crm_menu:
            crm_menu.name = self.partnership_label
