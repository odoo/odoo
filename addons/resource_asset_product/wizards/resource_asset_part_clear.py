from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResourceAssetPartClear(models.TransientModel):
    _name = "resource.asset.part.clear"
    _description = "Clear Flagged Parts"

    # FIELDS
    part_ids = fields.Many2many(
        comodel_name="resource.asset.part",
        string="Parts",
        required=True,
    )
    note = fields.Text(
        required=True,
        help="Why the flags are accepted. It stays on the part's history.",
    )

    # ACTION METHODS
    def action_clear(self):
        self.check_singleton()
        _debug.lifecycle("part_clear_wizard_confirmed", parts=self.part_ids)
        self.part_ids._clear_flags(self.note)
        return {"type": "ir.actions.act_window_close"}
