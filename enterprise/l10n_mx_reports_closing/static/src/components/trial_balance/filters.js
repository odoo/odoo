import { AccountReport } from "@account_reports/components/account_report/account_report";
import { AccountReportFilters } from "@account_reports/components/account_report/filters/filters";

const { DateTime } = luxon;

export class L10nMXTrialBalanceReportFilters extends AccountReportFilters {
    static template = "l10n_mx_reports_closing.TrialBalanceFilters";

    initDateFilters() {
        const filters = super.initDateFilters();
        filters["year13"] = 0;
        return filters;
    }

    displayPeriod(periodType) {
        if (periodType === 'year13') {
            return this._displayMonth13(DateTime.now());
        }

        return super.displayPeriod(periodType);
    }

    _displayMonth13(dateTo) {
        return dateTo.plus({ years: this.dateFilter.year13 }).toFormat("yyyy");
    }

    isPeriodSelected(periodType) {
        // This is a hack to use the "Year" behaviour for the "Month 13" date filter without displaying both of them selected at the same time
        const isYear13Selected = this.controller.options.date.filter.includes("year13");
        this.controller.options.l10n_mx_month_13 = isYear13Selected;
        return periodType === "year" && isYear13Selected ? false : super.isPeriodSelected(periodType);
    }
}

AccountReport.registerCustomComponent(L10nMXTrialBalanceReportFilters);
