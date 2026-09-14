from odoo import fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools.translate import _

_debug = DebugLog(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    order_cycle_count = fields.Integer(
        related="company_id.order_cycle_count",
        readonly=False,
    )
    order_cycle_unit = fields.Selection(
        related="company_id.order_cycle_unit",
        readonly=False,
    )

    def _clamp_validity_days(self, field_name, label):
        self.check_singleton()
        if self[field_name] >= 0:
            return None
        self[field_name] = self.env["res.company"].default_get([field_name])[field_name]
        _debug.logic("validity_days_clamped", field=field_name, value=self[field_name])
        return {
            "warning": {
                "title": _("Warning"),
                "message": _(
                    "%(label)s is required and must be greater or equal to 0.",
                    label=label,
                ),
            },
        }

    def _sync_order_lock(self, checkbox_field, lock_field):
        self.check_singleton()
        lock = "lock" if self[checkbox_field] else "edit"
        if self[lock_field] != lock:
            _debug.lifecycle("order_lock_synced", field=lock_field, value=lock)
            self[lock_field] = lock
