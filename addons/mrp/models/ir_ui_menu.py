# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _visible_menu_ids(self, debug=False):
        visible_ids = super()._visible_menu_ids(debug)
        if self.env.user.role == 'light_user':
            mrp_root = self.env['ir.model.data']._xmlid_to_res_id('mrp.menu_mrp_root', raise_if_not_found=False)
            if mrp_root:
                return visible_ids - {mrp_root}
        return visible_ids
