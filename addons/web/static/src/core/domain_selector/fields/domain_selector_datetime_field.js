/** @odoo-module **/

import { DatePicker, DateTimePicker } from "@web/core/datepicker/datepicker";
import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";

const { Component } = owl;

const dsf = registry.category("domain_selector/fields");
const dso = registry.category("domain_selector/operator");

export class DomainSelectorDateTimeField extends Component {
    get component() {
        const { DatePicker, DateTimePicker } = this.constructor.components;
        return this.props.field.type === "date" ? DatePicker : DateTimePicker;
    }
    get parser() {
        return registry.category("parsers").get(this.props.field.type);
    }
    get parsedValue() {
        return this.props.value ? this.parser(this.props.value) : luxon.DateTime.local();
    }

    onChange(value) {
        const serialize = this.props.field.type === "date" ? serializeDate : serializeDateTime;
        this.props.update({ value: serialize(value) });
    }
}
Object.assign(DomainSelectorDateTimeField, {
    template: "web.DomainSelectorDateTimeField",
    components: {
        DatePicker,
        DateTimePicker,
    },

    onDidTypeChange(field) {
        const serialize = field.type === "date" ? serializeDate : serializeDateTime;
        return { value: serialize(luxon.DateTime.local()) };
    },
    getOperators() {
        return ["=", "!=", ">", "<", ">=", "<=", "set", "not set"].map((key) => dso.get(key));
    },
});

dsf.add("date", DomainSelectorDateTimeField);
dsf.add("datetime", DomainSelectorDateTimeField);
