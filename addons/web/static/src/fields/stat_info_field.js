/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;
const formatters = registry.category("formatters");

export class StatInfoField extends Component {
    get formattedValue() {
        const formatter = formatters.get(this.props.type);
        return formatter(this.props.value || 0, { digits: this.props.digits });
    }
}

StatInfoField.template = "web.StatInfoField";
StatInfoField.props = {
    ...standardFieldProps,
    label: { type: String, optional: true },
    noLabel: { type: Boolean, optional: true },
    digits: { type: Array, optional: true },
};
StatInfoField.supportedTypes = ["float", "integer"];
StatInfoField.isEmpty = () => false;
StatInfoField.extractProps = (fieldName, record, attrs) => {
    return {
        label: attrs.options.label_field
            ? record.data[attrs.options.label_field]
            : record.activeFields[fieldName].string,
        noLabel: Boolean(attrs.nolabel && !/^(0|false)$/i.test(attrs.nolabel)),
        digits:
            (attrs.digits ? JSON.parse(attrs.digits) : attrs.options.digits) ||
            record.fields[fieldName].digits,
    };
};

registry.category("fields").add("statinfo", StatInfoField);
