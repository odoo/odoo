/** @odoo-module native */
import { AccountReport } from "@report_formula/components/account_report/account_report";
import { AccountReportFilters } from "@report_formula/components/account_report/filters/filters";
import { parseFloat } from "@web/core/parsers";
import { _t } from "@web/core/translation";

export class MulticurrencyRevaluationReportFilters extends AccountReportFilters {
    static template = "account.MulticurrencyRevaluationReportFilters";

    //------------------------------------------------------------------------------------------------------------------
    // Custom filters
    //------------------------------------------------------------------------------------------------------------------
    async filterExchangeRate(ev, currencyId) {
        try {
            this.controller.cachedFilterOptions.currency_rates[currencyId].rate =
                Math.abs(parseFloat(ev.currentTarget.value));
        } catch {
            this.notification.add(_t("Please enter a valid number."), {
                type: "danger",
            });
        }
    }
}

AccountReport.registerCustomComponent(MulticurrencyRevaluationReportFilters);
