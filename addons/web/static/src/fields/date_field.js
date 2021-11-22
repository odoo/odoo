/** @odoo-module **/

import { DatePicker } from "@web/core/datepicker/datepicker";
import { formatDate, parseDate, serializeDate } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class DateField extends Component {
    get parsedValue() {
        return this.props.value ? parseDate(this.props.value) : undefined;
    }

    get formattedValue() {
        return this.props.value ? formatDate(this.parsedValue) : "";
    }

    /**
     * @param {CustomEvent} ev
     */
    onChange(ev) {
        this.props.update(serializeDate(ev.detail.date));
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
});

registry.category("fields").add("date", DateField);
