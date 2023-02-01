/** @odoo-module **/

import { DatePicker } from "@web/core/datepicker/datepicker";
import { areDateEquals, formatDate, formatDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

export class DateField extends Component {
    setup() {
        /**
         * The last value that has been commited to the model.
         * Not changed in case of invalid field value.
         */
        this.lastSetValue = null;
    }
    get isDateTime() {
        return this.props.record.fields[this.props.name].type === "datetime";
    }
    get date() {
        return this.props.value && this.props.value.startOf("day");
    }

    get formattedValue() {
        return this.isDateTime
            ? formatDateTime(this.props.value, { format: localization.dateFormat })
            : formatDate(this.props.value);
    }

    onDateTimeChanged(date) {
        if (!areDateEquals(this.date || "", date)) {
            this.props.update(date);
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

DateField.template = "web.DateField";
DateField.components = {
    DatePicker,
};
DateField.props = {
    ...standardFieldProps,
    pickerOptions: { type: Object, optional: true },
    placeholder: { type: String, optional: true },
};
DateField.defaultProps = {
    pickerOptions: {},
};

DateField.displayName = _lt("Date");
DateField.supportedTypes = ["date", "datetime"];

DateField.extractProps = ({ attrs }) => {
    return {
        pickerOptions: attrs.options.datepicker,
        placeholder: attrs.placeholder,
    };
};

registry.category("fields").add("date", DateField);
