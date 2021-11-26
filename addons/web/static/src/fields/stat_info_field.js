/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class StatInfoField extends Component {
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

Object.assign(StatInfoField, {
    template: "web.StatInfoField",
    props: {
        ...standardFieldProps,
    },

    supportedTypes: ["float", "integer"],

    isEmpty() {
        return false;
    },
});

registry.category("fields").add("statinfo", StatInfoField);
