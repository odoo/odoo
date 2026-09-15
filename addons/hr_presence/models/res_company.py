from odoo import models
from odoo.tools import ormcache


class ResCompany(models.Model):
    _inherit = "res.company"

    def _hr_presence_valid_ips(self):
        self.check_singleton()
        raw = self.hr_presence_control_ip_list or ""
        return {part.strip() for part in raw.split(",") if part.strip()}

    def _get_cache_invalidation_fields(self):
        # _is_presence_ip_tracking_enabled is an ormcache, so nothing would notice a
        # company switching IP control on until the next registry cache clear.
        return super()._get_cache_invalidation_fields() | {"hr_presence_control_ip"}

    @ormcache()
    def _is_presence_ip_tracking_enabled(self):
        """Whether recording connection IPs can matter to anyone on this database.

        Read on every websocket presence update, so it must not reach the
        database when the feature is off -- which it is for most installations.
        """
        return bool(
            self.env["res.company"]
            .sudo()
            .search_count([("hr_presence_control_ip", "=", True)], limit=1)
        )
