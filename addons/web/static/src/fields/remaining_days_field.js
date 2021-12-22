/** @odoo-module **/

import { DatePicker, DateTimePicker } from "@web/core/datepicker/datepicker";
import { formatDate } from "@web/core/l10n/dates";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class RemainingDaysField extends Component {
    get hasTime() {
        return this.props.type === "datetime";
    }

    get pickerComponent() {
        return this.hasTime ? DateTimePicker : DatePicker;
    }

    get diffDays() {
        if (!this.props.value) {
            return null;
        }
        const today = luxon.DateTime.local().startOf("day");
        return Math.floor(this.props.value.startOf("day").diff(today, "days").days);
    }

    get formattedValue() {
        return this.props.value ? formatDate(this.props.value, { timezone: true }) : "";
    }
}

Object.assign(RemainingDaysField, {
    template: "web.RemainingDaysField",
    props: {
        ...standardFieldProps,
    },

    displayName: _lt("Remaining Days"),
    supportedTypes: ["date", "datetime"],
});

registry.category("fields").add("remaining_days", RemainingDaysField);
