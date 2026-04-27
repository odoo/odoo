import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { AccountReportFilters } from "@account_reports/components/account_report/filters/filters";

patch(AccountReportFilters.prototype, {
    get selectedExtraOptions() {
        let selectedExtraOptionsName = super.selectedExtraOptions;
        if (this.controller.filters.show_cash_basis) {
            const cashBasisFilterName = this.controller.options.report_cash_basis
                ? _t("Cash Basis")
                : _t("Accrual Basis");

            selectedExtraOptionsName = selectedExtraOptionsName
                ? `${selectedExtraOptionsName}, ${cashBasisFilterName}`
                : cashBasisFilterName;
        }
        return selectedExtraOptionsName;
    },

    get hasExtraOptionsFilter() {
        return super.hasExtraOptionsFilter || this.controller.filters.show_cash_basis;
    },
});
