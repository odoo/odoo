
/** @odoo-module */

import { AccountReport } from "@account_reports/components/account_report/account_report";
import { AccountReportLineCell } from "@account_reports/components/account_report/line_cell/line_cell";
const { DateTime } = luxon;


export class PartnerLedgerLineCell extends AccountReportLineCell {
    static template = "account_reports.PartnerLedgerLineCell";
    get cellClasses() {
        let superCellClasses = super.cellClasses;
        const cell = this.props.cell;
        if (
            cell.figure_type === 'date'
            && cell.expression_label == 'date_maturity'
            && cell.no_format
            && DateTime.fromISO(cell.no_format).startOf('day') < DateTime.now().startOf('day')
        ) {
            superCellClasses += ' text-danger';
        }
        return superCellClasses;
    }
}

AccountReport.registerCustomComponent(PartnerLedgerLineCell);
