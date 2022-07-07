/** @odoo-module **/

import { DatePicker } from "@web/core/datepicker/datepicker";
import { areDateEquals, formatDate } from "@web/core/l10n/dates";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "../standard_field_props";

const { Component } = owl;

export class DateField extends Component {
    get isDateTime() {
        return this.props.record.fields[this.props.name].type === "datetime";
    }
    get date() {
        return this.props.value && this.props.value.startOf("day");
    }

    get formattedValue() {
        return formatDate(this.props.value, {
            // get local date if field type is datetime
            timezone: this.isDateTime,
        });
    }

    onDateTimeChanged(date) {
        if (!areDateEquals(this.date || "", date)) {
            this.props.update(date);
        }
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
