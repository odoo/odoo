from typing import Self

from odoo import api, fields, models
from odoo.models import ValuesType


class ResCompany(models.Model):
    _inherit = "res.company"

    resource_calendar_ids = fields.One2many(
        comodel_name="resource.calendar",
        inverse_name="company_id",
        string="Working Hours",
    )
    resource_config_id = fields.Many2one(
        comodel_name="resource.config",
        compute="_compute_resource_config_id",
        search="_search_resource_config_id",
    )
    resource_calendar_id = fields.Many2one(
        related="resource_config_id.resource_calendar_id",
        readonly=False,
    )

    def _search_resource_config_id(self, operator, value):
        return self._search_config_link("resource.config", operator, value)

    def _compute_resource_config_id(self):
        configs = self.env["resource.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.resource_config_id = by_company.get(company.id, False)

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        companies = super().create(vals_list)
        companies_without_calendar = companies.filtered(
            lambda c: not c.resource_calendar_id
        )
        if companies_without_calendar:
            companies_without_calendar.sudo()._create_resource_calendar()
        return companies

    @api.model
    def _init_data_resource_calendar(self):
        self.search([("resource_calendar_id", "=", False)])._create_resource_calendar()

    def _create_resource_calendar(self) -> None:
        vals_list = [company._prepare_resource_calendar_values() for company in self]
        resource_calendars = self.env["resource.calendar"].create(vals_list)
        for company, calendar in zip(self, resource_calendars, strict=True):
            company.resource_calendar_id = calendar

    def _prepare_resource_calendar_values(self) -> ValuesType:
        self.check_singleton()
        return {
            "name": self.env._("Standard 40 hours/week"),
            "company_id": self.id,
        }
