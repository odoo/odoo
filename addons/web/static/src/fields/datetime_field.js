/** @odoo-module **/

import { DateTimePicker } from "@web/core/datepicker/datepicker";
import { areDateEquals, formatDateTime } from "@web/core/l10n/dates";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class DateTimeField extends Component {
    get formattedValue() {
        return formatDateTime(this.props.value, { timezone: true });
    }

    onDateTimeChanged(date) {
        if (!areDateEquals(this.props.value, date)) {
            this.props.update(date);
        }
    }
}

DateTimeField.template = "web.DateTimeField";
DateTimeField.props = {
    ...standardFieldProps,
    pickerOptions: { type: Object, optional: true },
};
DateTimeField.defaultProps = {
    pickerOptions: {},
};
DateTimeField.components = {
    DateTimePicker,
};
DateTimeField.displayName = _lt("Date & Time");
DateTimeField.supportedTypes = ["datetime"];
DateTimeField.extractProps = (fieldName, record, attrs) => {
    return {
        pickerOptions: attrs.options.datepicker,
    };
};

registry.category("fields").add("datetime", DateTimeField);
