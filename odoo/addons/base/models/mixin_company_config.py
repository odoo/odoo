from typing import Self

from odoo import api, fields, models
from odoo.api import ValuesType
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MixinCompanyConfig(models.AbstractModel):
    _name = "mixin.company.config"
    _description = "Configuration an application keeps per company"
    _check_company_auto = True

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        index=True,
        required=True,
        ondelete="cascade",
    )

    _company_uniq = models.Constraint(
        "unique (company_id)",
        "A company has one configuration record per application.",
    )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        # one record per company: data that names a company already
        # configured (the company's create made the record) writes it
        company_ids = [vals.get("company_id") for vals in vals_list]
        existing = {
            config.company_id.id: config
            for config in self.sudo().search(
                [("company_id", "in", [cid for cid in company_ids if cid])]
            )
        }
        if not existing:
            return super().create(vals_list)
        records = self.browse()
        to_create = []
        for vals in vals_list:
            config = existing.get(vals.get("company_id"))
            if config is None:
                to_create.append(vals)
                continue
            _debug.lifecycle(
                "written_instead_of_created",
                model=self._name,
                company=config.company_id.id,
            )
            config.with_env(self.env).write(
                {key: value for key, value in vals.items() if key != "company_id"}
            )
            records |= config.with_env(self.env)
        if to_create:
            records |= super().create(to_create)
        return records

    @api.model
    def _for(self, company: models.Model) -> Self:
        company.check_singleton()
        config = self.sudo().search([("company_id", "=", company.id)], limit=1)
        if config:
            return config.with_env(self.env)
        _debug.lifecycle("created_for_company", model=self._name, company=company.id)
        return self.sudo().create({"company_id": company.id}).with_env(self.env)

    @api.model
    def _for_each(self, companies: models.Model) -> Self:
        existing = self.sudo().search([("company_id", "in", companies.ids)])
        missing = companies - existing.company_id
        if missing:
            _debug.lifecycle(
                "created_for_companies", model=self._name, companies=missing.ids
            )
            existing |= self.sudo().create(
                [{"company_id": company.id} for company in missing]
            )
        return existing.with_env(self.env)
