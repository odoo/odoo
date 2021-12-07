/** @odoo-module **/

import { DatePicker } from "@web/core/datepicker/datepicker";
import { formatDate } from "@web/core/l10n/dates";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class DateField extends Component {
    get value() {
        return this.props.value && this.props.value.startOf("day");
    }
    get formattedValue() {
        return this.props.value ? formatDate(this.value) : "";
    }
    get datePickerOptions() {
        return Object.assign({}, this.props.options.datepicker);
    }

    /**
     * @param {CustomEvent} ev
     */
    onChange(ev) {
        this.props.update(ev.detail.date);
    }
}

Object.assign(DateField, {
    template: "web.DateField",
    props: {
        ...standardFieldProps,
    },
    components: {
        DatePicker,
    },

    displayName: _lt("Date"),
    supportedTypes: ["date", "datetime"],
});

registry.category("fields").add("date", DateField);
