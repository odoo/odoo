from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountTax(models.Model):
    _inherit = "account.tax"

    @_debug.perf.timed
    def _prepare_base_line_for_taxes_computation(self, record, **kwargs):
        results = super()._prepare_base_line_for_taxes_computation(record, **kwargs)
        results["deferred_start_date"] = self._get_base_line_field_value_from_record(
            record, "deferred_start_date", kwargs, False
        )
        results["deferred_end_date"] = self._get_base_line_field_value_from_record(
            record, "deferred_end_date", kwargs, False
        )
        return results

    @_debug.perf.timed
    def _prepare_tax_line_for_taxes_computation(self, record, **kwargs):
        results = super()._prepare_tax_line_for_taxes_computation(record, **kwargs)
        results["deferred_start_date"] = self._get_base_line_field_value_from_record(
            record, "deferred_start_date", kwargs, False
        )
        results["deferred_end_date"] = self._get_base_line_field_value_from_record(
            record, "deferred_end_date", kwargs, False
        )
        return results

    @_debug.perf.timed
    def _prepare_base_line_grouping_key(self, base_line):
        results = super()._prepare_base_line_grouping_key(base_line)
        results["deferred_start_date"] = base_line["deferred_start_date"]
        results["deferred_end_date"] = base_line["deferred_end_date"]
        return results

    @_debug.perf.timed
    def _prepare_base_line_tax_repartition_grouping_key(
        self, base_line, base_line_grouping_key, tax_data, tax_rep_data
    ):
        results = super()._prepare_base_line_tax_repartition_grouping_key(
            base_line, base_line_grouping_key, tax_data, tax_rep_data
        )
        record = base_line["record"]
        if (
            isinstance(record, models.Model)
            and record._name == "account.move.line"
            and record._has_deferred_compatible_account()
            and base_line["deferred_start_date"]
            and base_line["deferred_end_date"]
            and not tax_rep_data["tax_rep"].use_in_tax_closing
        ):
            results["deferred_start_date"] = base_line["deferred_start_date"]
            results["deferred_end_date"] = base_line["deferred_end_date"]
        else:
            results["deferred_start_date"] = False
            results["deferred_end_date"] = False
        return results

    @_debug.perf.timed
    def _prepare_tax_line_repartition_grouping_key(self, tax_line):
        results = super()._prepare_tax_line_repartition_grouping_key(tax_line)
        results["deferred_start_date"] = tax_line["deferred_start_date"]
        results["deferred_end_date"] = tax_line["deferred_end_date"]
        return results
