from odoo import api, models, _
from odoo.exceptions import UserError


class PosPreset(models.Model):
    _inherit = "pos.preset"

    @api.ondelete(at_uninstall=False)
    def _unlink_except_master_presets(self):
        master_presets = self.env["pos.config"].get_record_by_ref([
            'pos_restaurant.pos_takein_preset',
            'pos_restaurant.pos_takeout_preset',
            'pos_restaurant.pos_delivery_preset',
        ])
        if any(preset.id in master_presets for preset in self):
            raise UserError(_('You cannot delete the master preset(s).'))
