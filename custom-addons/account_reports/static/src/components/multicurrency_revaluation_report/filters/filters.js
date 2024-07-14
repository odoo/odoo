/** @odoo-module */

import { AccountReport } from "@account_reports/components/account_report/account_report";
import { AccountReportFilters } from "@account_reports/components/account_report/filters/filters";

export class MulticurrencyRevaluationReportFilters extends AccountReportFilters {
    static template = "account_reports.MulticurrencyRevaluationReportFilters";

    //------------------------------------------------------------------------------------------------------------------
    // Custom filters
    //------------------------------------------------------------------------------------------------------------------
    async filterExchangeRate() {
        Object.values(this.controller.options.currency_rates).forEach((currencyRate) => {
            const input = document.querySelector(`input[name="${ currencyRate.currency_id }"]`);

            currencyRate.rate = input.value;
        });

        this.controller.reload('currency_rates', this.controller.options);
    }
}

AccountReport.registerCustomComponent(MulticurrencyRevaluationReportFilters);
