from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountTax(models.Model):
    _inherit = "account.tax"

    def _get_used_tax_ids(self, tax_ids):

        used_taxes = super()._get_used_tax_ids(tax_ids)
        remaining_ids = tax_ids - used_taxes

        if remaining_ids:
            self.env["hr.expense"].flush_model(["tax_ids"])
            self.env.cr.execute(
                """
                SELECT id
                FROM account_tax
                WHERE EXISTS(
                    SELECT 1
                    FROM expense_tax AS exp
                    WHERE tax_id = ANY(%s)
                    AND account_tax.id = exp.tax_id
                )
            """,
                [list(remaining_ids)],
            )

            used_taxes.update([tax[0] for tax in self.env.cr.fetchall()])
            _debug.perf.count(
                "expense_tax_usage_scanned",
                candidates=len(remaining_ids),
                used=len(used_taxes),
            )

        return used_taxes

    def _prepare_base_line_for_taxes_computation(self, record, **kwargs):
        results = super()._prepare_base_line_for_taxes_computation(record, **kwargs)
        results["expense_id"] = self._get_base_line_field_value_from_record(
            record, "expense_id", kwargs, self.env["hr.expense"]
        )
        return results

    def _prepare_tax_line_for_taxes_computation(self, record, **kwargs):
        results = super()._prepare_tax_line_for_taxes_computation(record, **kwargs)
        results["expense_id"] = self._get_base_line_field_value_from_record(
            record, "expense_id", kwargs, self.env["hr.expense"]
        )
        return results

    def _prepare_base_line_grouping_key(self, base_line):
        results = super()._prepare_base_line_grouping_key(base_line)
        results["expense_id"] = base_line["expense_id"].id
        return results

    def _prepare_tax_line_repartition_grouping_key(self, tax_line):
        results = super()._prepare_tax_line_repartition_grouping_key(tax_line)
        results["expense_id"] = tax_line["expense_id"].id
        return results
