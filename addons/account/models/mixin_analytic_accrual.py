from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MixinAnalytic(models.AbstractModel):
    _inherit = "mixin.analytic"

    @api.model
    @_debug.perf.timed
    def _read_group_for_accrual(
        self,
        domain,
        groupby=(),
        aggregates=(),
        having=(),
        offset=0,
        limit=None,
        order=None,
    ) -> list[tuple]:
        aggregates_to_skip, fields_to_patch = (
            self._get_aggregates_to_skip_and_fields_to_patch()
        )
        patched_fields = {
            f"{field}:sum": field
            for field in fields_to_patch
            if f"{field}:sum" in aggregates
        }
        _debug.logic(
            "accrual_aggregates_patched",
            patched=len(patched_fields),
            skipped_aggregates=len(aggregates_to_skip),
            groupby=groupby,
        )
        if not patched_fields:
            return super()._read_group(
                domain, groupby, aggregates, having, offset, limit, order
            )

        kept_aggregates = tuple(a for a in aggregates if a not in aggregates_to_skip)
        rows = super()._read_group(
            domain,
            groupby,
            (*kept_aggregates, "id:recordset"),
            having,
            offset,
            limit,
            order,
        )

        accrual_records = self.search(Domain.AND([domain, self._get_domain_accrual()]))
        _debug.pipeline(
            "accrual_rows_fetched",
            rows=len(rows),
            accrual_records=accrual_records,
        )

        patched_rows = []
        for row in rows:
            group_values = row[: len(groupby)]
            kept_values = iter(row[len(groupby) : -1])
            records = row[-1] & accrual_records
            patched_rows.append(
                (
                    *group_values,
                    *(
                        sum(records.mapped(patched_fields[spec]))
                        if spec in patched_fields
                        else next(kept_values)
                        for spec in aggregates
                    ),
                )
            )
        return patched_rows

    @api.model
    def _get_domain_accrual(self):
        return [("product_id", "!=", False)]

    @api.model
    def _get_accrual_date_window(self, field_path):
        accrual_date = self.env.context.get("accrual_entry_date")
        ref_date = (
            fields.Date.to_date(accrual_date) if accrual_date else fields.Date.today()
        )
        return [
            (field_path, ">=", ref_date - relativedelta(years=1)),
            (field_path, "<", ref_date + relativedelta(days=1)),
        ]

    @api.model
    def _get_aggregates_to_skip_and_fields_to_patch(self):
        return (
            ["qty_invoiced_at_date:sum", "amount_to_invoice_at_date:sum"],
            ["qty_invoiced_at_date", "amount_to_invoice_at_date"],
        )
