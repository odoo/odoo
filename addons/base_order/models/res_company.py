from odoo import fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools.date_utils import get_timedelta

_debug = DebugLog(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    base_order_config_id = fields.Many2one(
        comodel_name="base_order.config",
        compute="_compute_base_order_config_id",
        search="_search_base_order_config_id",
    )

    def _search_base_order_config_id(self, operator, value):
        return self._search_config_link("base_order.config", operator, value)

    def _compute_base_order_config_id(self):
        configs = self.env["base_order.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.base_order_config_id = by_company.get(company.id, False)

    def _get_order_cycle_cutoff_date(self):
        self.check_singleton()
        _debug.logic(
            "order_cycle_cutoff",
            company=self,
            count=self.base_order_config_id.order_cycle_count,
            unit=self.base_order_config_id.order_cycle_unit,
        )
        return fields.Date.today() - get_timedelta(
            self.base_order_config_id.order_cycle_count,
            self.base_order_config_id.order_cycle_unit,
        )
