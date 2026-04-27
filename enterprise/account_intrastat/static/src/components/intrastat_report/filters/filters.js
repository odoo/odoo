import { _t } from "@web/core/l10n/translation";

import { patch } from "@web/core/utils/patch";
import { AccountReportFilters } from "@account_reports/components/account_report/filters/filters";

patch(AccountReportFilters.prototype, {

    get selectedIntrastatOptions() {
        const intrastatSelectedType = this.controller.options.intrastat_type
            .filter((intrastatType) => intrastatType.selected)
            .map((intrastatType) => intrastatType.name);

        const selectedIntrastatOptions = intrastatSelectedType.length
            ? intrastatSelectedType
            : [_t("Arrival"), _t("Dispatch")];

        selectedIntrastatOptions.push(
            this.controller.options.intrastat_extended ? _t("Extended mode") : _t("Standard mode"),
        );
        selectedIntrastatOptions.push(
            this.controller.options.intrastat_with_vat
                ? _t("Partners with VAT numbers")
                : _t("All partners"),
        );
        return selectedIntrastatOptions.join(", ");
    },
});
