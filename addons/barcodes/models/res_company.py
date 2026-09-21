from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    barcodes_config_id = fields.Many2one(
        comodel_name="barcodes.config",
        compute="_compute_barcodes_config_id",
        search="_search_barcodes_config_id",
    )

    def _search_barcodes_config_id(self, operator, value):
        return self._search_config_link("barcodes.config", operator, value)

    def _compute_barcodes_config_id(self):
        configs = self.env["barcodes.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.barcodes_config_id = by_company.get(company.id, False)
