# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _

from odoo.exceptions import UserError
from odoo.tools import Query, SQL

class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = "account.move.line"

    exclude_bank_lines = fields.Boolean(compute='_compute_exclude_bank_lines', store=True)

    analytic_coverage = fields.Float(
        string="Analytic Coverage",
        compute='_compute_analytic_coverage',
        groups='analytic.group_analytic_accounting',
    )

    @api.depends('journal_id')
    def _compute_exclude_bank_lines(self):
        for move_line in self:
            move_line.exclude_bank_lines = move_line.account_id != move_line.journal_id.default_account_id

    @api.constrains('tax_ids', 'tax_tag_ids')
    def _check_taxes_on_closing_entries(self):
        for aml in self:
            if aml.move_id.tax_closing_report_id and (aml.tax_ids or aml.tax_tag_ids):
                raise UserError(_("You cannot add taxes on a tax closing move line."))

    @api.depends('product_id', 'product_uom_id', 'move_id.tax_closing_report_id')
    def _compute_tax_ids(self):
        """ Some special cases may see accounts used in tax closing having default taxes.
        They would trigger the constrains above, which we don't want. Instead, we don't trigger
        the tax computation in this case.
        """
        # EXTEND account
        lines_to_compute = self.filtered(lambda line: not line.move_id.tax_closing_report_id)
        (self - lines_to_compute).tax_ids = False
        super(AccountMoveLine, lines_to_compute)._compute_tax_ids()

    @api.model
    def _prepare_aml_shadowing_for_report(self, change_equivalence_dict):
        """ Prepares the fields lists for creating a temporary table shadowing the account_move_line one.
        This is used to switch the computation mode of the reports, with analytics or financial budgets, for example.

        :param change_equivalence_dict: A dict, in the form {aml_field: sql_equivalence}, where:
                                        - aml_field: is a string containing the name of field of account.move.line
                                        - sql_equivalence: is the value to use to shadow aml_field. It can be an SQL object; if
                                          it's not, it'll be escaped in the query.

        :return: A tuple of 2 SQL objects, so that:
                 - The first one is the fields list to pass into the INSERT TO part of the query filling up the temporary table
                 - The second one contains the field values to insert into the SELECT clause of the same query, in the same order
                   as in the first element of the returned tuple.
        """
        line_fields = self.env['account.move.line'].fields_get()
        self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='account_move_line'")
        stored_fields = {f[0] for f in self.env.cr.fetchall() if f[0] in line_fields}

        fields_to_insert = []
        for fname in stored_fields:
            if fname in change_equivalence_dict:
                fields_to_insert.append(SQL(
                    "%(original)s AS %(asname)s",
                    original=change_equivalence_dict[fname],
                    asname=SQL('"account_move_line.%s"', SQL(fname)),
                ))
            else:
                line_field = line_fields[fname]
                if line_field.get("translate"):
                    typecast = SQL('jsonb')
                else:
                    typecast = SQL(self.env['account.move.line']._fields[fname].column_type[0])

                fields_to_insert.append(SQL(
                    "CAST(NULL AS %(typecast)s) AS %(fname)s",
                    typecast=typecast,
                    fname=SQL('"account_move_line.%s"', SQL(fname)),
                ))

        return SQL(', ').join(SQL.identifier(fname) for fname in stored_fields), SQL(', ').join(fields_to_insert)

    def _field_to_sql(self, alias: str, fname: str, query: (Query | None) = None, flush: bool = True) -> SQL:
        if fname == 'analytic_coverage':
            plan_id = self.env.context.get('selected_analytic_plan')
            if not plan_id:
                return SQL("0.0")

            move_line_distribution = self.env['account.move.line']._field_to_sql('aml', 'analytic_distribution')

            return SQL("""
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

        return super()._field_to_sql(alias, fname, query, flush)

    def _compute_analytic_coverage(self):
        plan_id = self.env.context.get('selected_analytic_plan')

        if not plan_id:
            self.analytic_coverage = 0.0
        else:
            plan_accounts = self.distribution_analytic_account_ids.filtered(lambda a: a.plan_id.id == plan_id)
            for line in self:
                coverage = 0
                if line.analytic_distribution:
                    for accounts, value in line.analytic_distribution.items():
                        if set(plan_accounts.ids) & {int(acc) for acc in accounts.split(',')}:
                            coverage += value
                line.analytic_coverage = coverage / 100
