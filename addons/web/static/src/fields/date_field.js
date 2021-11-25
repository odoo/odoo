/** @odoo-module **/

import { DatePicker } from "@web/core/datepicker/datepicker";
import { formatDate, serializeDate } from "@web/core/l10n/dates";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class DateField extends Component {
    get formattedValue() {
        return this.props.value ? formatDate(this.props.value) : "";
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

    displayName: _lt("Date"),
    supportedTypes: ["date", "datetime"],
});

registry.category("fields").add("date", DateField);
