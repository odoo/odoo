/** @odoo-module native */
import { PartnerLedgerFollowupLineCell } from "@account/components/partner_ledger_followup/line_cell/line_cell";
import { AccountReport } from "@report_formula/components/account_report/account_report";
import { AccountReportLine } from "@report_formula/components/account_report/line/line";

export class PartnerLedgerFollowupLine extends AccountReportLine {
    static template = "account.PartnerLedgerFollowupLine";
    static components = {
        ...AccountReportLine.components,
        PartnerLedgerFollowupLineCell,
    };
}
AccountReport.registerCustomComponent(PartnerLedgerFollowupLine);
