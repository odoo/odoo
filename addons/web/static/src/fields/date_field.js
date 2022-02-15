/** @odoo-module **/

import { DatePicker } from "@web/core/datepicker/datepicker";
import { formatDate } from "@web/core/l10n/dates";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class DateField extends Component {
    get date() {
        return this.props.value && this.props.value.startOf("day");
    }
    get isDateTime() {
        return this.props.record.fields[this.props.name].type === "datetime";
    }
    get formattedValue() {
        return this.props.value
            ? formatDate(this.props.value, {
                  // get local date if field type is datetime
                  timezone: this.isDateTime,
              })
            : "";
    }
}

DateField.template = "web.DateField";
DateField.props = {
    ...standardFieldProps,
    pickerOptions: { type: Object, optional: true },
};
DateField.defaultProps = {
    pickerOptions: {},
};
DateField.components = {
    DatePicker,
};
(DateField.displayName = _lt("Date")),
    (DateField.supportedTypes = ["date", "datetime"]),
    (DateField.convertAttrsToProps = (attrs) => {
        return {
            pickerOptions: attrs.options.datepicker,
        };
    });

registry.category("fields").add("date", DateField);
