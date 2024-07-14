/** @odoo-module */

import { useAutofocus, useService } from "@web/core/utils/hooks";

import { Component, useRef } from "@odoo/owl";

export class AccountReportEditPopover extends Component {
    static template = "account_reports.AccountReportEditPopover";

    setup() {
        this.orm = useService("orm");

        if (this.props.cell.figure_type === 'boolean') {
            this.booleanTrue = useRef("booleanTrue");
            this.booleanFalse = useRef("booleanFalse");
        } else {
            this.input = useRef("input");
            useAutofocus({ refName: "input" });
        }
    }

    // -----------------------------------------------------------------------------------------------------------------
    // Edit
    // -----------------------------------------------------------------------------------------------------------------
    async edit() {
        let editValue;
        const editPopupData = JSON.parse(this.props.cell.edit_popup_data);

        if (this.props.cell.figure_type === 'boolean')
            editValue = Number(this.booleanTrue.el.checked && !this.booleanFalse.el.checked);
        else
            editValue = this.input.el.value;

        const res = await this.orm.call(
            "account.report",
            "action_modify_manual_value",
            [
                this.props.controller.options.report_id,
                this.props.controller.options,
                editPopupData.column_group_key,
                editValue,
                editPopupData.target_expression_id,
                editPopupData.rounding,
                this.props.controller.columnGroupsTotals,
            ],
            {
                context: this.props.controller.context,
            }
        );

        this.props.controller.lines = res.lines;
        this.props.controller.columnGroupsTotals = res.column_groups_totals;

        this.props.onClose();
    }
}
