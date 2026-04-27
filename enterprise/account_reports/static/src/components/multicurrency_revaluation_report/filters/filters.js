import { AccountReport } from "@account_reports/components/account_report/account_report";
import { AccountReportFilters } from "@account_reports/components/account_report/filters/filters";
import { parseFloat } from "@web/views/fields/parsers";
import { _t } from "@web/core/l10n/translation";

export class MulticurrencyRevaluationReportFilters extends AccountReportFilters {
    static template = "account_reports.MulticurrencyRevaluationReportFilters";

    //------------------------------------------------------------------------------------------------------------------
    // Custom filters
    //------------------------------------------------------------------------------------------------------------------
    async filterExchangeRate(ev, currencyId) {
        try {
            this.controller.options.currency_rates[currencyId].rate = Math.abs(parseFloat(ev.currentTarget.value));
        } catch {
            this.notification.add(_t("Please enter a valid number."), {
                type: "danger",
            });
        }
    }
}

AccountReport.registerCustomComponent(MulticurrencyRevaluationReportFilters);
