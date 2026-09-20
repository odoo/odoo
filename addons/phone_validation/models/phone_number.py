import re

from odoo import _, api, fields, models
from odoo.db.schema import create_index
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import SQL, normalize_identifier

from odoo.addons.phone_validation.tools import phone_validation

PHONE_NOISE_SQL_PATTERN = r"[\s\\./\(\)\-]"
PHONE_NOISE_PATTERN = re.compile(PHONE_NOISE_SQL_PATTERN)


class PhoneNumber(models.Model):
    _inherit = "phone.number"
    _phone_search_min_length = 3

    valid = fields.Boolean(
        compute="_compute_valid",
        store=True,
    )
    blacklisted = fields.Boolean(
        compute="_compute_blacklisted",
        search="_search_blacklisted",
        compute_sudo=True,
        groups="base.group_user",
    )

    def init(self):
        super().init()
        for fname in ("number", "sanitized"):
            expression = (
                f"regexp_replace(({fname}::text), "
                f"'{PHONE_NOISE_SQL_PATTERN}'::text, ''::text, 'g'::text)"
            )
            create_index(
                self.env.cr,
                indexname=normalize_identifier(f"{self._table}_{fname}_partial_tgm"),
                tablename=self._table,
                expressions=[expression],
                where=f"{fname} IS NOT NULL",
            )
            if self.env.registry.has_trigram:
                create_index(
                    self.env.cr,
                    indexname=normalize_identifier(
                        f"{self._table}_{fname}_partial_gin_idx"
                    ),
                    tablename=self._table,
                    method="gin",
                    expressions=[expression + " gin_trgm_ops"],
                    where=f"{fname} IS NOT NULL",
                )

    def _get_phone_country(self):
        return super()._get_phone_country() or self.env.company.country_id

    @api.model
    def _e164(self, number, country=None):
        if not number:
            return False
        country = country or self.env.company.country_id
        if not country and not number.lstrip().startswith(("+", "00")):
            return False
        try:
            return phone_validation.phone_format(
                number,
                country.code if country else None,
                country.phone_code if country else None,
                force_format="E164",
                raise_exception=True,
            )
        except UserError:
            return False

    @api.model
    def _normalize_number(self, number, country=None):
        return self._e164(number, country) or super()._normalize_number(number, country)

    @api.depends("number", "country_id", "partner_ids.country_id")
    def _compute_valid(self):
        for phone in self:
            phone.valid = bool(self._e164(phone.number, phone._get_phone_country()))

    @api.depends("sanitized")
    def _compute_blacklisted(self):
        numbers = [number for number in self.mapped("sanitized") if number]
        blacklist = (
            set(
                self.env["phone.blacklist"]
                .sudo()
                .search([("number", "in", numbers)])
                .mapped("number")
            )
            if numbers
            else set()
        )
        for phone in self:
            phone.blacklisted = phone.sanitized in blacklist

    @api.model
    def _search_blacklisted(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        self.env.cr.execute(
            SQL(
                "SELECT pn.id FROM phone_number pn "
                "JOIN phone_blacklist bl ON bl.number = pn.sanitized AND bl.active"
            )
        )
        ids = [row[0] for row in self.env.cr.fetchall()]
        return [("id", operator, ids)]

    @api.onchange("number", "country_id")
    def _onchange_number(self):
        if self.number:
            country = self.country_id or self.env.company.country_id
            self.number = (
                self._phone_format_number(
                    self.number, country, force_format="INTERNATIONAL"
                )
                or self.number
            )

    @api.model
    def _search_number_terms(self, operator, value):
        value = value.strip() if isinstance(value, str) else value
        if not value:
            return []
        if self._phone_search_min_length and len(value) < self._phone_search_min_length:
            raise UserError(
                _("Please enter at least 3 characters when searching a Phone number.")
            )
        if value.startswith(("+", "00")):
            term = PHONE_NOISE_PATTERN.sub(
                "", value[1 if value.startswith("+") else 2 :]
            )
            if operator not in ("=", "!="):
                term = f"{term}%"
            return ["00" + term, "+" + term]
        term = PHONE_NOISE_PATTERN.sub("", value)
        if operator not in ("=", "!="):
            term = f"%{term}%"
        return [term]

    @api.model
    def _search_number_ids(self, operator, value):
        """The phone numbers matching ``value`` -- one term, or a collection of
        them under ``in`` -- in a single statement."""
        if operator == "in":
            operator, values = "=", value
        else:
            values = [value]
        terms = [
            term
            for value in values
            for term in self._search_number_terms(operator, value)
        ]
        if not terms:
            return []
        sql_operator = {"=like": "LIKE", "=ilike": "ILIKE"}.get(operator, operator)
        clauses = [
            SQL(
                "REGEXP_REPLACE(pn.%s, %s, '', 'g') %s %s",
                SQL.identifier(fname),
                PHONE_NOISE_SQL_PATTERN,
                SQL(sql_operator),
                term,
            )
            for fname in ("number", "sanitized")
            for term in terms
        ]
        self.env.cr.execute(
            SQL(
                "SELECT pn.id FROM phone_number pn WHERE %s",
                SQL(" OR ").join(clauses),
            )
        )
        return [row[0] for row in self.env.cr.fetchall()]

    @api.model
    def _search_phone_domain(self, fnames, operator, value):
        if isinstance(value, str):
            value = value.strip()
        if not fnames:
            raise UserError(_("Missing definition of phone fields."))
        if operator in ("in", "not in"):
            values = [v.strip() if isinstance(v, str) else v for v in value]
            if any(v is True or not v for v in values):
                aggregator = Domain.OR if operator == "in" else Domain.AND
                return aggregator(
                    self._search_phone_domain(
                        fnames, "=" if operator == "in" else "!=", v
                    )
                    for v in values
                )
            ids = self._search_number_ids("in", values)
            if operator == "not in":
                return Domain.AND(Domain(fname, "not in", ids) for fname in fnames)
            return Domain.OR(Domain(fname, "in", ids) for fname in fnames)
        if (value is True or not value) and operator in ("=", "!="):
            if value:
                operator = "=" if operator == "!=" else "!="
            op = Domain.AND if operator == "=" else Domain.OR
            return op(Domain(fname, operator, False) for fname in fnames)
        if not value:
            return Domain.TRUE
        positive = {"!=": "=", "not like": "like", "not ilike": "ilike"}
        if operator in positive:
            ids = self._search_number_ids(positive[operator], value)
            return Domain.AND(Domain(fname, "not in", ids) for fname in fnames)
        ids = self._search_number_ids(operator, value)
        return Domain.OR(Domain(fname, "in", ids) for fname in fnames)
