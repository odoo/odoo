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
    get datePickerOptions() {
        return Object.assign({}, this.props.options.datepicker);
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
