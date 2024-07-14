/** @odoo-module */

import { AccountReport } from "@account_reports/components/account_report/account_report";
import { AccountReportFilters } from "@account_reports/components/account_report/filters/filters";

export class ConsolidationReportFilters extends AccountReportFilters {
    static template = "account_consolidation.ConsolidationReportFilters";

    //------------------------------------------------------------------------------------------------------------------
    // Getters
    //------------------------------------------------------------------------------------------------------------------
    get selectedComparisonName() {
        let comparisonName = null;

        for (const period of this.controller.options.periods)
            if (period.selected)
                if (comparisonName)
                    comparisonName += `, ${ period.name }`;
                else
                    comparisonName = period.name;

        return comparisonName;
    }

    get selectedJournalName() {
        let journalName = null;

        for (const journal of this.controller.options.consolidation_journals)
            if (journal.selected)
                if (journalName)
                    journalName += `, ${ journal.name }`;
                else
                    journalName = journal.name;

        return journalName || "All";
    }

    get hasSelectedPeriod() {
        if (!this.controller.options.periods)
            return false;

        for (const period of this.controller.options.periods)
            if (period.selected)
                return true;

        return false;
    }
}

AccountReport.registerCustomComponent(ConsolidationReportFilters);
