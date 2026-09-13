from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, Query

_debug = DebugLog(__name__)


class AccountAccountTag(models.Model):
    _inherit = "account.account.tag"

    report_expression_id = fields.Many2one(
        comodel_name="account.report.expression",
        compute="_compute_report_expression",
    )
    balance_negate = fields.Boolean(compute="_compute_report_expression")

    @api.model_create_multi
    @_debug.perf.timed
    def create(self, vals_list):
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "create",
                model=self._name,
                count=len(vals_list),
                fields=sorted({key for vals in vals_list for key in vals}),
            )
        tags = super().create(vals_list)
        if tax_tags := tags.filtered(
            lambda tag: tag.applicability == "taxes",
        ):
            self._translate_tax_tags(tag_ids=tax_tags.ids)
        return tags

    @api.ondelete(at_uninstall=False)
    @_debug.perf.timed
    def _unlink_except_master_tags(self):
        _debug.lifecycle("_unlink_except_master_tags", records=self)
        master_xmlids = [
            "account_tag_operating",
            "account_tag_financing",
            "account_tag_investing",
        ]
        for master_xmlid in master_xmlids:
            master_tag = self.env.ref(
                f"account.{master_xmlid}",
                raise_if_not_found=False,
            )
            if master_tag and master_tag in self:
                raise UserError(
                    _(
                        "You cannot delete this account tag (%s), it is used "
                        "on the chart of account definition.",
                        master_tag.name,
                    )
                )

    @api.depends("applicability", "country_id")
    @api.depends_context("company")
    @_debug.perf.timed
    def _compute_display_name(self):
        if not self.env.company.multi_vat_foreign_country_ids:
            return super()._compute_display_name()

        for tag in self:
            name = tag.name
            if (
                tag.applicability == "taxes"
                and tag.country_id
                and tag.country_id != self.env.company.account_fiscal_country_id
            ):
                name = _(
                    "%(tag)s (%(country_code)s)",
                    tag=tag.name,
                    country_code=tag.country_id.code,
                )
            tag.display_name = name
        return None

    @api.depends("name")
    @_debug.perf.timed
    def _compute_report_expression(self):
        query = self._search([("id", "in", self.ids)])
        id2expression = {
            tag_id: vals
            for tag_id, *vals in self.env.execute_query(
                query.select(
                    SQL.identifier(query.table, "id"),
                    self._field_to_sql(
                        query.table,
                        "report_expression_id",
                        query,
                    ),
                    self._field_to_sql(
                        query.table,
                        "balance_negate",
                        query,
                    ),
                ),
            )
        }
        _debug.perf.count("tag_report_expressions_fetched", rows=len(id2expression))
        for tag in self:
            tag.report_expression_id, tag.balance_negate = id2expression.get(
                tag._origin.id, (False, False)
            )

    def _field_to_sql(
        self,
        alias: str,
        field_expr: str,
        query: (Query | None) = None,
    ) -> SQL:
        if field_expr in ("report_expression_id", "balance_negate"):
            rhs_alias = query.get_table_alias(alias, "expression")
            if rhs_alias not in query._tables:
                query.add_join(
                    kind="LEFT JOIN",
                    alias=rhs_alias,
                    table="account_report_expression",
                    condition=SQL(
                        "%s->>'en_US' = LTRIM(%s, '-')",
                        SQL.identifier(alias, "name"),
                        SQL.identifier(rhs_alias, "formula"),
                    ),
                )
            if field_expr == "report_expression_id":
                return SQL.identifier(rhs_alias, "id")
            if field_expr == "balance_negate":
                return SQL(
                    "STARTS_WITH(%s, '-')",
                    SQL.identifier(rhs_alias, "formula"),
                )
        return super()._field_to_sql(alias, field_expr, query)

    @api.model
    def _get_tax_tags(self, tag_name, country_id):
        domain = self._get_domain_tax_tags(tag_name, country_id)
        original_lang = self.env.context.get("lang", "en_US")
        rslt_tags = (
            self.env["account.account.tag"]
            .with_context(
                active_test=False,
                lang="en_US",
            )
            .search(domain)
        )
        return rslt_tags.with_context(lang=original_lang)

    @api.model
    def _get_domain_tax_tags(self, formula, country_id):
        return [
            ("name", "=", formula.lstrip("-")),
            ("country_id", "=", country_id),
            ("applicability", "=", "taxes"),
        ]

    def _get_related_tax_report_expressions(self):
        tags = self.with_context(lang="en_US")
        if not tags:
            return self.env["account.report.expression"]

        keys = {(tag.name, tag.country_id.id) for tag in tags}
        candidates = self.env["account.report.expression"].search(
            Domain("engine", "=", "tax_tags")
            & Domain.OR(
                (
                    Domain(
                        "report_line_id.report_id.country_id",
                        "=",
                        tag.country_id.id,
                    )
                    & Domain("formula", "like", tag.name)
                )
                for tag in tags
            ),
        )
        return candidates.filtered(
            lambda expression: (
                (
                    expression.formula.lstrip("-"),
                    expression.report_line_id.report_id.country_id.id,
                )
                in keys
            )
        )

    @_debug.perf.timed
    def _translate_tax_tags(self, langs=None, tag_ids=None):
        langs = langs or (
            code
            for code, _name in self.env["res.lang"].get_installed()
            if code != "en_US"
        )
        for lang in langs:
            lang_sql = SQL("%s::text", lang)
            self.env.cr.execute(
                SQL(
                    """
                UPDATE account_account_tag tag
                   SET name = tag.name || jsonb_build_object(
                        %(lang)s,
                        substring(tag.name->>'en_US' FOR 1)
                            || (report_line.name->>%(lang)s))
                  FROM account_report_line report_line
                  JOIN account_report report
                    ON report.id = report_line.report_id
                 WHERE tag.applicability = 'taxes'
                   AND tag.country_id = report.country_id
                   AND tag.name->>'en_US'
                       = substring(tag.name->>'en_US' FOR 1)
                         || (report_line.name->>'en_US')
                   AND tag.name->>%(lang)s
                       != substring(tag.name->>'en_US' FOR 1)
                          || (report_line.name->>%(lang)s)
                   %(and_tag_ids)s
                """,
                    lang=lang_sql,
                    and_tag_ids=(
                        SQL("AND tag.id = ANY(%s)", list(tag_ids))
                        if tag_ids
                        else SQL("")
                    ),
                )
            )
            _debug.perf.count(
                "tax_tag_names_translated",
                lang=lang,
                restricted=bool(tag_ids),
                rows=self.env.cr.rowcount,
            )
