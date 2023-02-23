/** @odoo-module **/

import { DateTimePicker } from "@web/core/datepicker/datepicker";
import { areDateEquals, formatDateTime } from "@web/core/l10n/dates";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

export class DateTimeField extends Component {
    static template = "web.DateTimeField";
    static components = {
        DateTimePicker,
    };
    static props = {
        ...standardFieldProps,
        pickerOptions: { type: Object, optional: true },
        placeholder: { type: String, optional: true },
    };
    static defaultProps = {
        pickerOptions: {},
    };

    setup() {
        /**
         * The last value that has been commited to the model.
         * Not changed in case of invalid field value.
         */
        this.lastSetValue = null;
    }

    get formattedValue() {
        return formatDateTime(this.props.value);
    }

    onDateTimeChanged(date) {
        if (!areDateEquals(this.props.value || "", date)) {
            this.props.record.update({ [this.props.name]: date });
        }
    }
    onDatePickerInput(ev) {
        this.props.setDirty(ev.target.value !== this.lastSetValue);
    }
    onUpdateInput(date) {
        this.props.setDirty(false);
        this.lastSetValue = date;
    }
}

export const dateTimeField = {
    component: DateTimeField,
    displayName: _lt("Date & Time"),
    supportedTypes: ["datetime"],
    extractProps: ({ attrs }) => ({
        pickerOptions: attrs.options.datepicker,
        placeholder: attrs.placeholder,
    }),
};

registry.category("fields").add("datetime", dateTimeField);
