/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

class StatInfoField extends Component {
    get formatter() {
        return registry.category("formatters").get(this.props.type);
    }

    get value() {
        return this.formatter(this.props.value || 0, {
            field: this.props.record.fields[this.props.name],
        });
    }

    get text() {
        return this.props.options.label_field
            ? this.props.record.data[this.props.options.label_field]
            : this.props.record.activeFields[this.props.name].string;
    }
}
StatInfoField.props = {
    ...standardFieldProps,
};
StatInfoField.template = "web.StatInfoField";

Object.assign(StatInfoField, {
    isEmpty() {
        return false;
    },
});

registry.category("fields").add("statinfo", StatInfoField);
