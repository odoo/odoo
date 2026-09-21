/** @odoo-module native */
import { AccountReport } from "@report_formula/components/account_report/account_report";
import { AccountReportFilters } from "@report_formula/components/account_report/filters/filters";
import { _t } from "@web/core/translation";

export class JournalReportFilters extends AccountReportFilters {
    get filterExtraOptionsData() {
        return {
            ...super.filterExtraOptionsData,
            show_payment_lines: {
                name: _t("Include Payments"),
            },
        };
    }
}

AccountReport.registerCustomComponent(JournalReportFilters);
