/** @odoo-module native */
import { AccountReport } from "@report_formula/components/account_report/account_report";
import { AccountReportLineCell } from "@report_formula/components/account_report/line_cell/line_cell";

import { DateTime } from "luxon";
export class PartnerLedgerLineCell extends AccountReportLineCell {
    get cellClasses() {
        let superCellClasses = super.cellClasses;
        const cell = this.props.cell;
        if (
            cell.figure_type === "date" &&
            cell.expression_label === "date_maturity" &&
            cell.no_format &&
            DateTime.fromISO(cell.no_format).startOf("day") <
                DateTime.now().startOf("day")
        ) {
            superCellClasses += " text-danger";
        }
        return superCellClasses;
    }
}

AccountReport.registerCustomComponent(PartnerLedgerLineCell);
