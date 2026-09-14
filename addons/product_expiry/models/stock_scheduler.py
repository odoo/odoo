from odoo import api, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockScheduler(models.AbstractModel):
    _inherit = "stock.scheduler"

    @api.model
    def _get_tasks(self):
        return [*super()._get_tasks(), "_alert_expired_lots"]

    @api.model
    def _alert_expired_lots(self, use_new_cursor=False, company_id=False):
        _debug.lifecycle("cron_enter", cron="alert_expired_lots", company=company_id)
        self.env["stock.lot"]._alert_lots_past_alert_date(company_id=company_id)
