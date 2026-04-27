/** @odoo-module */

import { localization } from "@web/core/l10n/localization";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { formatFloat } from "@web/core/utils/numbers";
import { parseFloat } from "@web/views/fields/parsers";

import { Component, useRef } from "@odoo/owl";

export class AccountReportEditPopover extends Component {
    static template = "account_reports.AccountReportEditPopover";
    static props = {
        line_id: String,
        cell: Object,
        controller: Object,
        onClose: Function,
        close: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.editPopupData = JSON.parse(this.props.cell.edit_popup_data);

        if (this.props.cell.figure_type === 'boolean') {
            this.booleanTrue = useRef("booleanTrue");
            this.booleanFalse = useRef("booleanFalse");
        } else {
            this.input = useRef("input");
            useAutofocus({ refName: "input" });
        }
    }

    get editableNumericValue() {
        const { no_format } = this.props.cell.no_format;
        if (no_format == null || no_format === "") {
            return no_format;
        }

        const numericValue = Number(no_format);
        if (Number.isNaN(numericValue)) {
            return no_format;
        }

        return formatFloat(numericValue, {
            digits: [0, this.editPopupData.rounding],
            thousandsSep: "",
            grouping: [],
            trailingZeros: false,
        });
    }

    // -----------------------------------------------------------------------------------------------------------------
    // Edit
    // -----------------------------------------------------------------------------------------------------------------
    async edit() {
        let editValue;

        if (this.props.cell.figure_type === 'boolean')
            editValue = Number(this.booleanTrue.el.checked && !this.booleanFalse.el.checked);
        else if (this.props.cell.figure_type === 'string')
            editValue = this.input.el.value;
        else {
            const inputValue = this.input.el.value;
            const otherDecimalSeparator = localization.decimalPoint === "." ? "," : ".";
            const localeThousandsSeparator = localization.thousandsSep || "";

            if (
                inputValue.split(localization.decimalPoint || ".").length >= 3 // At least three parts means two decimal separators which would be wrong.
                || (inputValue.includes(otherDecimalSeparator) && otherDecimalSeparator !== localeThousandsSeparator)
            ) {
                editValue = inputValue;
            } else {
                try {
                    editValue = parseFloat(inputValue).toString();
                } catch {
                    editValue = inputValue;
                }
            }
        }

        const res = await this.orm.call(
            "account.report",
            "action_modify_manual_value",
            [
                this.props.controller.options.report_id,
                this.props.line_id,
                this.props.controller.options,
                this.editPopupData.column_group_key,
                editValue,
                this.editPopupData.target_expression_id,
                this.editPopupData.rounding,
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
