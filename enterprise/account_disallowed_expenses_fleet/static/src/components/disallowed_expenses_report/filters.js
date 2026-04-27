import { patch } from "@web/core/utils/patch";
import { AccountReportFilters } from "@account_reports/components/account_report/filters/filters";

patch(AccountReportFilters.prototype, {
    get hasExtraOptionsFilter() {
        return super.hasExtraOptionsFilter || "vehicle_split" in this.controller.options;
    },
});
