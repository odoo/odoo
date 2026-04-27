import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { AccountReportFilters } from "@account_reports/components/account_report/filters/filters";

patch(AccountReportFilters.prototype, {
    get selectedExtraOptions() {
        let selectedExtraOptionsName = super.selectedExtraOptions;

        if (this.controller.options.include_no_tin) {
            const includeNoTINName = _t("With Partners without TIN");

            selectedExtraOptionsName = selectedExtraOptionsName
                ? `${selectedExtraOptionsName}, ${includeNoTINName}`
                : includeNoTINName;
        }

        if (this.controller.options.include_imports) {
            const includeImportsName = _t("With Importations");
            selectedExtraOptionsName = selectedExtraOptionsName
                ? `${selectedExtraOptionsName}, ${includeImportsName}`
                : includeImportsName;
        }

        return selectedExtraOptionsName;
    },

    get hasExtraOptionsFilter() {
        return (
            super.hasExtraOptionsFilter ||
            "include_no_tin" in this.controller.options ||
            "include_imports" in this.controller.options
        );
    },
});
