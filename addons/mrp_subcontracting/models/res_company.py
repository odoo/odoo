from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    mrp_subcontracting_config_id = fields.Many2one(
        comodel_name="mrp_subcontracting.config",
        compute="_compute_mrp_subcontracting_config_id",
        search="_search_mrp_subcontracting_config_id",
    )

    def _search_mrp_subcontracting_config_id(self, operator, value):
        return self._search_config_link("mrp_subcontracting.config", operator, value)

    def _compute_mrp_subcontracting_config_id(self):
        configs = self.env["mrp_subcontracting.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.mrp_subcontracting_config_id = by_company.get(company.id, False)

    @api.model
    def _create_missing_subcontracting_location(self):
        company_without_subcontracting_loc = (
            self.env["res.company"]
            .with_context(active_test=False)
            .search(
                [
                    (
                        "mrp_subcontracting_config_id.subcontracting_location_id",
                        "=",
                        False,
                    )
                ]
            )
        )
        company_without_subcontracting_loc._create_subcontracting_location()

    def _create_per_company_locations(self):
        super()._create_per_company_locations()
        self._create_subcontracting_location()

    def _create_subcontracting_location(self):
        for company in self:
            subcontracting_location = self.env["stock.location"].create(
                {
                    "name": self.env._("Subcontracting"),
                    "usage": "internal",
                    "company_id": company.id,
                }
            )
            self.env["ir.default"].set(
                "res.partner",
                "property_stock_subcontractor",
                subcontracting_location.id,
                company_id=company.id,
            )
            company.mrp_subcontracting_config_id.subcontracting_location_id = (
                subcontracting_location
            )
