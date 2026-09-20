from typing import Self

from odoo import api, fields, models
from odoo.api import ValuesType
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MixinCompanyConfig(models.AbstractModel):
    _name = "mixin.company.config"
    _description = "Configuration an application keeps per company"
    _check_company_auto = True
    _company_config = True

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

    def _register_hook(self) -> None:
        # every company has its row once the registry is loaded: a search
        # through the company's link finds what it never had to create
        super()._register_hook()
        if self._abstract:
            return
        companies = self.env["res.company"].sudo().with_context(active_test=False)
        rows = self._for_each(companies.search([]))
        _debug.lifecycle("registry_rows_ensured", model=self._name, rows=len(rows))

    @api.model
    def _get_field_names_delegated_to_root(self) -> list[str]:
        return []

    @api.constrains(
        lambda self: self._get_field_names_delegated_to_root() + ["company_id"]
    )
    def _check_delegated_fields_match_root(self) -> None:
        for config in self:
            parent = config.company_id.parent_id
            if not parent:
                continue
            parent_config = self._for(parent)
            for fname in self._get_field_names_delegated_to_root():
                if config[fname] != parent_config[fname]:
                    description = (
                        self.env["ir.model.fields"]
                        ._get(self._name, fname)
                        .field_description
                    )
                    raise ValidationError(
                        self.env._(
                            "The %s of a subsidiary must be the same as its root company.",
                            description,
                        )
                    )

    def _inherit_delegated_fields(self, vals_list: list[ValuesType]) -> None:
        delegated = self._get_field_names_delegated_to_root()
        if not delegated:
            return
        Company = self.env["res.company"]
        for vals in vals_list:
            parent = Company.browse(vals.get("company_id")).parent_id
            if not parent:
                continue
            parent_config = self._for(parent)
            for fname in delegated:
                vals.setdefault(
                    fname,
                    self._fields[fname].convert_to_write(
                        parent_config[fname], parent_config
                    ),
                )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        # one record per company: data that names a company already
        # configured (the company's create made the record) writes it
        self._inherit_delegated_fields(vals_list)
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
        # a company not yet saved has no configuration to find or create
        companies = companies.filtered(lambda company: isinstance(company.id, int))
        # One query finds and fills the configurations: they are read in the
        # caller's scope when it may read them, so the values it asks for next
        # come from the cache; a reader without rights finds them as superuser.
        reader = self if self.has_access("read") else self.sudo()
        existing = reader.search_fetch([("company_id", "in", companies.ids)])
        missing = companies - existing.company_id
        if missing:
            _debug.lifecycle(
                "created_for_companies", model=self._name, companies=missing.ids
            )
            existing |= self.sudo().create(
                [{"company_id": company.id} for company in missing]
            )
        return existing.with_env(self.env)
