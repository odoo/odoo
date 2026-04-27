import { useRef, useState } from "@odoo/owl";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";

import { AccountReportLineCell } from "@account_reports/components/account_report/line_cell/line_cell";

export class AccountReportLineCellEditable extends AccountReportLineCell {
    static template = "account_reports.AccountReportLineCellEditable";

    setup() {
        super.setup();
        this.input = useRef("input");
        this.focused = useState({ value: false });

        useHotkey(
            "Enter",
            (ev) => {
                ev.target.blur();
            },
            { bypassEditableProtection: true }
        );
    }

    get cellClasses() {
        let classes = super.cellClasses;
        if (this.hasEditPopupData) {
            classes += " editable-cell";
        }
        return classes;
    }

    get hasEditPopupData() {
        return Boolean(this.props.cell?.edit_popup_data);
    }

    async onChange() {
        if (!this.input.el.value.trim()) {
            return;
        }
        const editValue = this.input.el.value;
        const cellEditData = this.hasEditPopupData
            ? JSON.parse(this.props.cell.edit_popup_data)
            : {};

        const res = await this.orm.call(
            "account.report",
            "action_modify_manual_value",
            [
                this.controller.options.report_id,
                this.props.line.id,
                this.controller.options,
                cellEditData.column_group_key,
                editValue,
                cellEditData.target_expression_id,
                cellEditData.rounding,
                this.controller.columnGroupsTotals,
            ],
            {
                context: this.controller.context,
            }
        );
        this.controller.lines = res.lines;
        this.controller.columnGroupsTotals = res.column_groups_totals;
        this.focused.value = false;
    }

    get inputValue() {
        return this.focused.value ? this.props.cell.no_format : this.props.cell.name;
    }

    onFocus() {
        this.focused.value = true;
    }

    onBlur() {
        if (JSON.stringify(this.props.cell.no_format) === this.input.el.value) {
            this.focused.value = false;
        }
    }
}
