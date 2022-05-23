/** @odoo-module **/

import { DatePicker } from "@web/core/datepicker/datepicker";
import { areDateEquals, formatDate } from "@web/core/l10n/dates";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class DateField extends Component {
    get date() {
        return this.props.value && this.props.value.startOf("day");
    }

    get formattedValue() {
        return formatDate(this.props.value, {
            // get local date if field type is datetime
            timezone: this.props.isDateTime,
        });
    }

    onDateTimeChanged(date) {
        if (!areDateEquals(this.date, date)) {
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
    isDateTime: { type: Boolean, optional: true },
    pickerOptions: { type: Object, optional: true },
};
DateField.defaultProps = {
    isDateTime: false,
    pickerOptions: {},
};

DateField.displayName = _lt("Date");
DateField.supportedTypes = ["date", "datetime"];

DateField.extractProps = (fieldName, record, attrs) => {
    return {
        isDateTime: record.fields[fieldName].type === "datetime",
        pickerOptions: attrs.options.datepicker,
    };
};

registry.category("fields").add("date", DateField);
