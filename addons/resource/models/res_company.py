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
    resource_calendar_id = fields.Many2one(
        comodel_name="resource.calendar",
        string="Default Working Hours",
        ondelete="restrict",
    )

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
