# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _visible_menu_ids(self, debug=False):
        visible_ids = super()._visible_menu_ids(debug)
        if self.env.user.has_group('hr_attendance.group_hr_attendance_officer'):
            menu_ids_to_hide = ['hr_attendance.menu_hr_attendance_overview']
            hidden_menu_ids = {
                menu_id for ref in menu_ids_to_hide
                if (menu_id := self.env['ir.model.data']._xmlid_to_res_id(ref))
            }
            return visible_ids - hidden_menu_ids
        return visible_ids
