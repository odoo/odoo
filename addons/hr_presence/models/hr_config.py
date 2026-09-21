from odoo import api, models


class HrConfig(models.Model):
    _inherit = "hr.config"

    @api.model
    def _get_cache_invalidation_fields(self):
        # _is_presence_ip_tracking_enabled is an ormcache, so nothing would notice a
        # company switching IP control on until the next registry cache clear.
        return super()._get_cache_invalidation_fields() | {"hr_presence_control_ip"}
