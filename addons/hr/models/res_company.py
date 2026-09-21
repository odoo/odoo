from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    hr_config_id = fields.Many2one(
        comodel_name="hr.config",
        compute="_compute_hr_config_id",
        search="_search_hr_config_id",
    )

    # fields.Properties resolves its `definition` as one hop and one field, so
    # hr.employee cannot reach the configuration through the link: the company
    # declares the definition and the configuration stores it
    employee_properties_definition = fields.PropertiesDefinition(
        related="hr_config_id.employee_properties_definition",
        readonly=False,
    )

    def _search_hr_config_id(self, operator, value):
        return self._search_config_link("hr.config", operator, value)

    def _compute_hr_config_id(self):
        configs = self.env["hr.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.hr_config_id = by_company.get(company.id, False)
