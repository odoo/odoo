from typing import Any

from odoo import api, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class KpiProvider(models.AbstractModel):
    _name = "kpi.provider"
    _description = "KPI Provider"

    @api.model
    def get_kpi_summary(self) -> list[dict[str, Any]]:
        _debug.logic("kpi_summary", provider=self._name, uid=self.env.uid, kpis=0)
        return []
