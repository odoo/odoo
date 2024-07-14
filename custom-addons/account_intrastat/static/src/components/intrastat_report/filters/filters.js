/** @odoo-module */

import { AccountReport } from "@account_reports/components/account_report/account_report";
import { AccountReportFilters } from "@account_reports/components/account_report/filters/filters";

export class IntrastatReportFilters extends AccountReportFilters {
    static template = "account_intrastat.IntrastatReportFilters";

    //------------------------------------------------------------------------------------------------------------------
    // Getters
    //------------------------------------------------------------------------------------------------------------------
    get intrastatTypeName() {
        let name = null;

        for (const intrastatType of this.controller.options.intrastat_type)
            if (intrastatType.selected)
                name = (name) ? `${ name }, ${ intrastatType.name }` : intrastatType.name;

        return (name) ? name : "All";
    }
}

AccountReport.registerCustomComponent(IntrastatReportFilters);
