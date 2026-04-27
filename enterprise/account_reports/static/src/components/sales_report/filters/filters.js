import { _t } from "@web/core/l10n/translation";

import { AccountReport } from "@account_reports/components/account_report/account_report";
import { AccountReportFilters } from "@account_reports/components/account_report/filters/filters";

export class SalesReportFilters extends AccountReportFilters {
    static template = "account_reports.SalesReportFilters";

    //------------------------------------------------------------------------------------------------------------------
    // Getters
    //------------------------------------------------------------------------------------------------------------------
    get selectedEcTaxName() {
        const selected = this.controller.options.ec_tax_filter_selection.filter(
            (ecTax) => ecTax.selected,
        );

        switch (selected.length) {
            case this.controller.options.ec_tax_filter_selection.length:
                return _t("All");
            case 0:
                return _t("None");
            default:
                return selected.map((s) => s.name.substring(0, 1)).join(", ");
        }
    }
}

AccountReport.registerCustomComponent(SalesReportFilters);
