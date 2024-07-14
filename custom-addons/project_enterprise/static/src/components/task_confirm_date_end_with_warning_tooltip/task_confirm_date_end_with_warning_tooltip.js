/** @odoo-module */

import { registry } from "@web/core/registry";
import { DateTimeField, dateTimeField } from "@web/views/fields/datetime/datetime_field";
import { Component } from "@odoo/owl";

export class WarningTooltip extends Component {
    static template = "industry_fsm.warning_tooltip";

    get tooltipInfo() {
        return JSON.stringify({ text: this.props.value });
    }
}

export class DateTimeWithWarning extends DateTimeField {
    static components = { ...DateTimeField.components, WarningTooltip };

    static template = "industry_fsm.DateTimeWithWarning";

    get warning() {
        return this.props.record.data.warning || "";
    }
}

export const dateTimeWithWarning = {
    ...dateTimeField,
    component: DateTimeWithWarning,
};

registry.category("fields").add("task_confirm_date_end_with_warning", dateTimeWithWarning);
