from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    purchase_config_id = fields.Many2one(
        comodel_name="purchase.config",
        compute="_compute_purchase_config_id",
        search="_search_purchase_config_id",
    )

    def _search_purchase_config_id(self, operator, value):
        return self._search_config_link("purchase.config", operator, value)

    def _compute_purchase_config_id(self):
        configs = self.env["purchase.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.purchase_config_id = by_company.get(company.id, False)
