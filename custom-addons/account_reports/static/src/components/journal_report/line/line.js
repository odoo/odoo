/** @odoo-module */

import { AccountReport } from "@account_reports/components/account_report/account_report";
import { AccountReportLine } from "@account_reports/components/account_report/line/line";

export class JournalReportLine extends AccountReportLine {
    static template = "account_reports.JournalReportLine";

    // -----------------------------------------------------------------------------------------------------------------
    // Classes
    // -----------------------------------------------------------------------------------------------------------------
    get lineClasses() {
        let classes = super.lineClasses;

        if (this.props.line.id.includes("|headers~~"))
            classes += ' accent_header';

        if (this.props.line.move_id)
            classes += ' accent_line';

        return classes;
    }

    // -----------------------------------------------------------------------------------------------------------------
    // Actions
    // -----------------------------------------------------------------------------------------------------------------
    async openTaxJournalItems(ev, name, taxType) {
        return this.controller.reportAction(ev, "journal_report_action_open_tax_journal_items", {
            name: name,
            tax_type: taxType,
            journal_id: this.props.line.journal_id,
            journal_type: this.props.line.journal_type,
            date_form: this.props.line.date_from,
            date_to: this.props.line.date_to,
        })
    }
}

AccountReport.registerCustomComponent(JournalReportLine);
