from odoo import models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _visible_menu_ids(self, debug=False):
        visible_ids = super()._visible_menu_ids(debug)
        if self.env.user.role == 'light_user':
            repair_root = self.env['ir.model.data']._xmlid_to_res_id('repair.menu_repair_order', raise_if_not_found=False)
            if repair_root:
                return visible_ids - {repair_root}
        return visible_ids
