# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _visible_menu_ids(self, debug=False):
        visible_ids = super()._visible_menu_ids(debug)
        if self.env.user.role == 'light_user':
            maintenance_root = self.env['ir.model.data']._xmlid_to_res_id('maintenance.menu_maintenance_title', raise_if_not_found=False)
            return visible_ids - {maintenance_root}
        return visible_ids
