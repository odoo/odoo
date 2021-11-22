/** @odoo-module **/

import { DateTimePicker } from "@web/core/datepicker/datepicker";
import { formatDateTime, parseDateTime, serializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class DateTimeField extends Component {
    get parsedValue() {
        return this.props.value ? parseDateTime(this.props.value, { timezone: false }) : undefined;
    }

    get formattedValue() {
        return this.props.value ? formatDateTime(this.parsedValue, { timezone: true }) : "";
    }

    /**
     * @param {CustomEvent} ev
     */
    onChange(ev) {
        this.props.update(serializeDateTime(ev.detail.date));
    }
}

Object.assign(DateTimeField, {
    template: "web.DateTimeField",
    props: {
        ...standardFieldProps,
    },
    components: {
        DateTimePicker,
    },
});

registry.category("fields").add("datetime", DateTimeField);
