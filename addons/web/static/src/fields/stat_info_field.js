/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class StatInfoField extends Component {
    get formatter() {
        return registry.category("formatters").get(this.props.type);
    }

    get value() {
        return this.props.format(this.props.value || 0);
    }
}

StatInfoField.template = "web.StatInfoField";
StatInfoField.props = {
    ...standardFieldProps,
    label: { type: String, optional: true },
    noLabel: { type: Boolean, optional: true },
};
StatInfoField.supportedTypes = ["float", "integer"];
StatInfoField.isEmpty = () => false;
StatInfoField.extractProps = (fieldName, record, attrs) => {
    return {
        label: attrs.options.label_field
            ? record.data[attrs.options.label_field]
            : record.activeFields[fieldName].string,
        noLabel: Boolean(attrs.nolabel && !/^(0|false)$/i.test(attrs.nolabel)),
    };
};

registry.category("fields").add("statinfo", StatInfoField);
