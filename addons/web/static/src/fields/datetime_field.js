/** @odoo-module **/

import { DateTimePicker } from "@web/core/datepicker/datepicker";
import { formatDateTime } from "@web/core/l10n/dates";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class DateTimeField extends Component {
    get formattedValue() {
        return this.props.value ? formatDateTime(this.props.value, { timezone: true }) : "";
    }
}

Object.assign(DateTimeField, {
    template: "web.DateTimeField",
    props: {
        ...standardFieldProps,
        pickerOptions: { type: Object, optional: true },
    },
    defaultProps: {
        pickerOptions: {},
    },
    components: {
        DateTimePicker,
    },

    displayName: _lt("Date & Time"),
    supportedTypes: ["datetime"],

    convertAttrsToProps(attrs) {
        return {
            pickerOptions: attrs.options.datepicker,
        };
    },
});

registry.category("fields").add("datetime", DateTimeField);
