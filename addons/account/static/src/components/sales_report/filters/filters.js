/** @odoo-module native */
import { AccountReport } from "@report_formula/components/account_report/account_report";
import { AccountReportFilters } from "@report_formula/components/account_report/filters/filters";
import { _t } from "@web/core/translation";

export class SalesReportFilters extends AccountReportFilters {
    static template = "account.SalesReportFilters";

    //------------------------------------------------------------------------------------------------------------------
    // Getters
    //------------------------------------------------------------------------------------------------------------------
    get selectedEcTaxName() {
        const selected =
            this.controller.cachedFilterOptions.ec_tax_filter_selection.filter(
                (ecTax) => ecTax.selected,
            );

        switch (selected.length) {
            case this.controller.cachedFilterOptions.ec_tax_filter_selection.length:
                return _t("All");
            case 0:
                return _t("None");
            default:
                return selected.map((s) => s.name.substring(0, 1)).join(", ");
        }
    }
}

AccountReport.registerCustomComponent(SalesReportFilters);
