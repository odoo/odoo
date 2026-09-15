from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    partnership_label = fields.Char(
        related="company_id.partnership_label",
        readonly=False,
        required=True,
    )

    @api.onchange("partnership_label")
    def _onchange_partnership_label(self):
        crm_menu = self.env.ref(
            "partnership.crm_menu_partners", raise_if_not_found=False
        )
        if crm_menu:
            _debug.lifecycle("partnership_menu_renamed", label=self.partnership_label)
            crm_menu.name = self.partnership_label
