import logging
import typing
from collections.abc import Collection
from typing import Literal, Self

from odoo import api, fields, models
from odoo.api import ValuesType
from odoo.libs.debug_log import DebugLog

if typing.TYPE_CHECKING:
    from .mail_alias import MailAlias
    from .mail_alias_domain import MailAliasDomain

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class MixinMailAliasMixinOptional(models.AbstractModel):
    _name = "mixin.mail.alias.optional"
    _description = "Email Aliases Mixin (light)"
    ALIAS_WRITEABLE_FIELDS = [
        "alias_domain_id",
        "alias_name",
        "alias_contact",
        "alias_defaults",
        "alias_bounced_content",
    ]

    alias_id: MailAlias = fields.Many2one(
        comodel_name="mail.alias",
        copy=False,
        required=False,
        ondelete="restrict",
    )
    alias_name = fields.Char(
        related="alias_id.alias_name",
        readonly=False,
    )
    alias_domain_id: MailAliasDomain = fields.Many2one(
        comodel_name="mail.alias.domain",
        related="alias_id.alias_domain_id",
        string="Alias Domain",
        readonly=False,
    )
    alias_domain = fields.Char(
        related="alias_id.alias_domain",
        string="Alias Domain Name",
    )
    alias_defaults = fields.Text(related="alias_id.alias_defaults")
    alias_email = fields.Char(
        related="alias_id.alias_full_name",
        string="Email Alias",
    )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        company_fname = self._mail_get_company_field()
        if company_fname:
            company_id_default = (
                self.default_get([company_fname]).get(company_fname)
                or self.env.company.id
            )
            company_prefetch_ids = {
                vals[company_fname] for vals in vals_list if vals.get(company_fname)
            }
            company_prefetch_ids.add(company_id_default)
        else:
            company_id_default = self.env.company.id
            company_prefetch_ids = {company_id_default}

        alias_vals_list, record_vals_list = [], []
        overrides_by_index = {}
        for index, vals in enumerate(vals_list):
            if self._is_new_alias_required(vals):
                company_id = vals.get(company_fname) or company_id_default
                company = (
                    self.env["res.company"]
                    .with_prefetch(company_prefetch_ids)
                    .browse(company_id)
                )
                alias_vals, record_vals = self._alias_split_values(vals)
                creation_vals = (
                    self.env[self._name]
                    .with_context(
                        default_alias_domain_id=alias_vals.get(
                            "alias_domain_id", company.alias_domain_id.id
                        ),
                    )
                    ._alias_get_creation_values()
                )
                overrides = {
                    fname: value
                    for fname, value in alias_vals.items()
                    if fname in creation_vals
                }
                alias_vals_list.append({**creation_vals, **alias_vals})
                record_vals_list.append(record_vals)
                overrides_by_index[index] = overrides

        alias_ids = []
        if alias_vals_list:
            alias_ids = iter(self.env["mail.alias"].sudo().create(alias_vals_list).ids)

        valid_vals_list = []
        record_vals_iter = iter(record_vals_list)
        for vals in vals_list:
            if self._is_new_alias_required(vals):
                record_vals = next(record_vals_iter)
                record_vals["alias_id"] = next(alias_ids)
                valid_vals_list.append(record_vals)
            else:
                valid_vals_list.append(vals)

        records = super().create(valid_vals_list)
        _debug.lifecycle(
            "create",
            model=self._name,
            count=len(records),
            aliases_created=len(alias_vals_list),
            overrides=len(overrides_by_index),
        )

        for index, record in enumerate(records):
            if not record.alias_id:
                continue
            alias_values = record._alias_get_creation_values()
            overrides = overrides_by_index.get(index, {})
            alias_values.update(
                {
                    fname: value
                    for fname, value in overrides.items()
                    if fname in alias_values
                }
            )
            record.alias_id.sudo().write(alias_values)

        return records

    def write(self, vals: ValuesType) -> Literal[True]:
        if vals.get("alias_name"):
            alias_create_values = [
                dict(record._alias_get_creation_values(), alias_name=vals["alias_name"])
                for record in self.filtered(lambda rec: not rec.alias_id)
            ]
            if alias_create_values:
                _debug.lifecycle(
                    "aliases_created_on_write",
                    model=self._name,
                    records=len(alias_create_values),
                )
                aliases = self.env["mail.alias"].sudo().create(alias_create_values)
                for record, alias in zip(
                    self.filtered(lambda rec: not rec.alias_id), aliases, strict=False
                ):
                    record.alias_id = alias.id

        alias_vals, record_vals = self._alias_split_values(
            vals, filters=self.ALIAS_WRITEABLE_FIELDS
        )
        if record_vals:
            super().write(record_vals)

        company_fname = self._mail_get_company_field()
        if company_fname in vals:
            alias_domain_values = self.filtered("alias_id")._alias_get_alias_domain_id()
            for record, alias_domain_id in alias_domain_values.items():
                record.sudo().alias_domain_id = alias_domain_id.id

        if alias_vals:
            if not record_vals:
                self.check_access("write")
            _debug.lifecycle(
                "alias_written",
                model=self._name,
                records=self.ids,
                fields=list(alias_vals),
            )
            self.mapped("alias_id").sudo().write(alias_vals)

        return True

    def unlink(self) -> Literal[True]:
        aliases = self.mapped("alias_id")
        _debug.lifecycle(
            "unlink", model=self._name, records=self.ids, aliases=len(aliases)
        )
        res = super().unlink()
        aliases.sudo().unlink()
        return res

    def copy_data(self, default: ValuesType | None = None) -> list[ValuesType]:
        vals_list = super().copy_data(default=default)
        not_writable_fields = set(self.env["mail.alias"]._fields.keys()) - set(
            self.ALIAS_WRITEABLE_FIELDS
        )
        for vals in vals_list:
            for not_writable_field in not_writable_fields:
                if not_writable_field in vals:
                    del vals[not_writable_field]
        return vals_list

    @api.model
    def _is_new_alias_required(self, record_vals: dict) -> bool:
        return not record_vals.get("alias_id") and record_vals.get("alias_name")

    def _alias_get_alias_domain_id(self) -> dict:
        alias_domain_values = {}
        record_companies = self._mail_get_companies()
        for record in self:
            record_company = record_companies[record.id]
            alias_domain_values[record] = (
                record_company.alias_domain_id
                or record.alias_domain_id
                or self.env.company.alias_domain_id
            )
        return alias_domain_values

    def _prepare_alias_defaults(self) -> dict:
        if not self:
            return {}
        self.check_singleton()
        return self.alias_id._prepare_alias_defaults() if self.alias_id else {}

    def _alias_get_creation_values(self) -> dict:
        values = {
            "alias_parent_thread_id": self.id or False,
            "alias_parent_model_id": self.env["ir.model"]._get_id(self._name),
        }
        if "default_alias_domain_id" in self.env.context:
            values["alias_domain_id"] = self.env.context["default_alias_domain_id"]
        return values

    def _alias_split_values(
        self, values: dict, filters: Collection[str] | Literal[False] = False
    ) -> tuple:
        if not filters:
            filters = self.env["mail.alias"]._fields.keys()
        alias_values, record_values = {}, {}
        for fname in values:
            if fname in filters:
                alias_values[fname] = values.get(fname)
            else:
                record_values[fname] = values.get(fname)
        return alias_values, record_values
