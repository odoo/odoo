/** @odoo-module **/

import { registry } from "@web/core/registry";
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
EmailField.props = standardFieldProps;
EmailField.template = "web.EmailField";

registry.category("fields").add("email", EmailField);
