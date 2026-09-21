/** @odoo-module native */
import { AccountReportLineCell } from "@report_formula/components/account_report/line_cell/line_cell";

export class PartnerLedgerFollowupLineCell extends AccountReportLineCell {
    static template = "account.PartnerLedgerFollowupLineCell";

    async toggleNoFollowup(ev) {
        const res = await this.orm.call(
            "account.partner.ledger.report.handler",
            "action_toggle_no_followup",
            [this.props.line.id, this.controller.lines.map((line) => line.id)],
        );
        this.controller.updateLines(
            res.updated_line_ids,
            "no_followup",
            res.updated_value,
        );
    }
}
