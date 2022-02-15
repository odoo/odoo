/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class EmailField extends Component {
    get formattedValue() {
        let value = typeof this.props.value === "string" ? this.props.value : "";
        return value;
    }
    /**
     * @param {Event} ev
     */
    onChange(ev) {
        let value = ev.target.value;
        if (this.props.record.fields[this.props.name].trim) {
            value = value.trim();
        }
        this.props.update(value || false);
    }
}

EmailField.template = "web.EmailField";
EmailField.props = {
    ...standardFieldProps,
};
EmailField.displayName = _lt("Email");
EmailField.supportedTypes = ["char"];

registry.category("fields").add("email", EmailField);
