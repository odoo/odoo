from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    order_cycle_count = fields.Integer(
        related="company_id.base_order_config_id.order_cycle_count",
        readonly=False,
    )
    order_cycle_unit = fields.Selection(
        related="company_id.base_order_config_id.order_cycle_unit",
        readonly=False,
    )

    def _company_default_of(self, field_name):
        company = self.env["res.company"]
        link = company._config_link_of_field(field_name)
        owner = self.env[company._fields[link].comodel_name] if link else company
        return owner.default_get([field_name])[field_name]

    def _clamp_validity_days(self, field_name, label):
        self.check_singleton()
        if self[field_name] >= 0:
            return None
        self[field_name] = self._company_default_of(field_name)
        _debug.logic("validity_days_clamped", field=field_name, value=self[field_name])
        return {
            "warning": {
                "title": self.env._("Warning"),
                "message": self.env._(
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
