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
        return this.props.labelField
            ? this.props.record.data[this.props.labelField]
            : this.props.record.activeFields[this.props.name].string;
    }
}

StatInfoField.template = "web.StatInfoField";
StatInfoField.props = {
    ...standardFieldProps,
    labelField: { type: String, optional: true },
    noLabel: { type: Boolean, optional: true },
};
StatInfoField.supportedTypes = ["float", "integer"];
StatInfoField.isEmpty = () => false;
StatInfoField.extractProps = (fieldName, record, attrs) => {
    return {
        labelField: attrs.options.label_field,
        noLabel: Boolean(attrs.nolabel && !/^(0|false)$/i.test(attrs.nolabel)),
    };
};

registry.category("fields").add("statinfo", StatInfoField);
