from odoo import _, api, fields, models
from odoo.db.schema import get_table_columns
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, Query

_debug = DebugLog(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    exclude_bank_lines = fields.Boolean(
        compute="_compute_exclude_bank_lines",
        store=True,
    )

    analytic_coverage = fields.Float(
        compute="_compute_analytic_coverage",
        groups="analytic.group_analytic_accounting",
    )

    @api.depends("journal_id")
    def _compute_exclude_bank_lines(self):
        for move_line in self:
            move_line.exclude_bank_lines = (
                move_line.account_id != move_line.journal_id.default_account_id
            )

    @api.constrains("tax_ids", "tax_tag_ids")
    @_debug.perf.timed
    def _check_taxes_on_closing_entries(self):
        for aml in self:
            if aml.move_id.closing_return_id and (aml.tax_ids or aml.tax_tag_ids):
                raise UserError(_("You cannot add taxes on a tax closing move line."))

    @api.depends("product_id", "product_uom_id", "move_id.closing_return_id")
    def _compute_tax_ids(self):
        lines_to_compute = self.filtered(
            lambda line: not line.move_id.closing_return_id
        )
        (self - lines_to_compute).tax_ids = False
        super(AccountMoveLine, lines_to_compute)._compute_tax_ids()

    def _get_attachment_domains(self):
        attachment_domains = super()._get_attachment_domains()
        if self.move_id.closing_return_id:
            attachment_domains.append(
                [
                    ("res_model", "=", "account.return"),
                    ("res_id", "in", self.move_id.closing_return_id.ids),
                ]
            )
        return attachment_domains

    @api.model
    def _get_attachment_by_record(self, id_model2attachments, move_line):
        attachment_id = super()._get_attachment_by_record(
            id_model2attachments, move_line
        )
        if not attachment_id and move_line.move_id.closing_return_id:
            attachment_id = id_model2attachments.get(
                ("account.return", move_line.move_id.closing_return_id.id)
            )
        return attachment_id

    @api.model
    @_debug.perf.timed
    def _prepare_aml_shadowing_for_report(
        self, change_equivalence_dict, prefix_fields=False, prefix_fields_to_insert=True
    ):
        line_fields = self.env["account.move.line"]._fields
        stored_fields = sorted(
            fld
            for fld in get_table_columns(self.env.cr, "account_move_line")
            if fld in line_fields
        )

        fields_to_insert = []
        for fname in stored_fields:
            name = (
                SQL('"account_move_line.%s"', SQL(fname))
                if prefix_fields_to_insert
                else SQL(fname)
            )

            if fname in change_equivalence_dict:
                fields_to_insert.append(
                    SQL(
                        "%(original)s AS %(asname)s",
                        original=change_equivalence_dict[fname],
                        asname=name,
                    )
                )
            else:
                line_field = line_fields[fname]
                if getattr(line_field, "translate", False):
                    typecast = SQL("jsonb")
                else:
                    typecast = SQL(line_field.column_type[0])  # noqa: E8501  a field class's declared column type, not input

                fields_to_insert.append(
                    SQL(
                        "CAST(NULL AS %(typecast)s) AS %(fname)s",
                        typecast=typecast,
                        fname=name,
                    )
                )

        if _debug.pipeline.enabled:
            _debug.pipeline(
                "aml_shadowing_columns",
                stored=len(stored_fields),
                substituted=sum(
                    1 for fname in stored_fields if fname in change_equivalence_dict
                ),
                prefixed=prefix_fields_to_insert,
            )
        return (
            SQL(", ").join(
                SQL.identifier("account_move_line", fname)
                if prefix_fields
                else SQL.identifier(fname)
                for fname in stored_fields
            ),
            SQL(", ").join(fields_to_insert),
        )

    def _affect_tax_report(self):
        return super()._affect_tax_report() or self.move_id.closing_return_id

    def _field_to_sql(
        self, alias: str, fname: str, query: (Query | None) = None
    ) -> SQL:
        if fname == "analytic_coverage":
            plan_id = self.env.context.get("selected_analytic_plan")
            _debug.logic("analytic_coverage_sql", plan_id=plan_id, alias=alias)
            if not plan_id:
                return SQL("0.0")

            move_line_distribution = self.env["account.move.line"]._field_to_sql(
                "aml", "analytic_distribution"
            )

            return SQL(
                """
                   (SELECT COALESCE(SUM(CAST(distribution.value AS FLOAT)) / 100, 0)
                      FROM jsonb_each_text(%(distribution)s) AS distribution(key, value)
                     WHERE EXISTS (
                              SELECT 1
                                FROM regexp_split_to_table(distribution.key, ',') AS accounts
                                JOIN account_analytic_account ON account_analytic_account.id = CAST(accounts AS INTEGER)
                               WHERE account_analytic_account.plan_id = %(plan_id)s
                   ))
                """,
                distribution=move_line_distribution,
                plan_id=plan_id,
            )

        return super()._field_to_sql(alias, fname, query)

    @api.depends("analytic_distribution", "distribution_analytic_account_ids")
    @_debug.perf.timed
    def _compute_analytic_coverage(self):
        plan_id = self.env.context.get("selected_analytic_plan")
        _debug.logic("analytic_coverage_plan", lines=self, plan_id=plan_id)

        if not plan_id:
            self.analytic_coverage = 0.0
        else:
            plan_accounts = self.distribution_analytic_account_ids.filtered(
                lambda a: a.plan_id.id == plan_id
            )
            for line in self:
                coverage = 0
                if line.analytic_distribution:
                    for accounts, value in line.analytic_distribution.items():
                        if set(plan_accounts.ids) & {
                            int(acc) for acc in accounts.split(",")
                        }:
                            coverage += value
                line.analytic_coverage = coverage / 100
