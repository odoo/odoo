from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"
    _check_company_auto = True

    sale_config_id = fields.Many2one(
        comodel_name="sale.config",
        compute="_compute_sale_config_id",
        search="_search_sale_config_id",
    )

    def _search_sale_config_id(self, operator, value):
        return self._search_config_link("sale.config", operator, value)

    def _compute_sale_config_id(self):
        configs = self.env["sale.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.sale_config_id = by_company.get(company.id, False)
