/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { archParseBoolean } from "@web/views/utils";
import { standardFieldProps } from "../standard_field_props";

const { Component } = owl;
const formatters = registry.category("formatters");

export class StatInfoField extends Component {
    get formattedValue() {
        const formatter = formatters.get(this.props.type);
        return formatter(this.props.value || 0, { digits: this.props.digits });
    }
    get label() {
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
    digits: { type: Array, optional: true },
};

StatInfoField.displayName = _lt("Stat Info");
StatInfoField.supportedTypes = ["float", "integer", "monetary"];

StatInfoField.isEmpty = () => false;
StatInfoField.extractProps = ({ attrs, field }) => {
    return {
        labelField: attrs.options.label_field,
        noLabel: archParseBoolean(attrs.nolabel),
        digits: (attrs.digits ? JSON.parse(attrs.digits) : attrs.options.digits) || field.digits,
    };
};

registry.category("fields").add("statinfo", StatInfoField);
