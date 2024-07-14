/** @odoo-module */

import { AccountReport } from "@account_reports/components/account_report/account_report";
import { AccountReportLineCell } from "@account_reports/components/account_report/line_cell/line_cell";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class ConsolidationReportLineCell extends AccountReportLineCell {
    static template = "account_consolidation.ConsolidationReportLineCell";
    static components = {
        ...super.components,
        Dropdown,
        DropdownItem,
    }

    //------------------------------------------------------------------------------------------------------------------
    // Audit
    //------------------------------------------------------------------------------------------------------------------
    async audit() {
        const auditAction = await this.orm.call(
            "consolidation.trial.balance.report.handler",
            "action_open_audit",
            [
                this.controller.options.report_id,
                this.controller.options,
                {
                    line_id: this.props.line.id,
                    journal_id: this.props.cell.journal_id,
                },
            ],
            {
                context: this.controller.context,
            }
        );

        return this.action.doAction(auditAction);
    }
}

AccountReport.registerCustomComponent(ConsolidationReportLineCell);
