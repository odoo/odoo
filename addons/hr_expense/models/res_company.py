from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    hr_expense_config_id = fields.Many2one(
        comodel_name="hr_expense.config",
        compute="_compute_hr_expense_config_id",
        search="_search_hr_expense_config_id",
    )

    def _search_hr_expense_config_id(self, operator, value):
        return self._search_config_link("hr_expense.config", operator, value)

    def _compute_hr_expense_config_id(self):
        configs = self.env["hr_expense.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.hr_expense_config_id = by_company.get(company.id, False)
