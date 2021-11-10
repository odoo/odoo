/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class CharField extends Component {
    get formattedValue() {
        let value = typeof this.props.value === "string" ? this.props.value : "";
        if (this.props.password) {
            value = "*".repeat(value.length);
        }
        return value;
    }

    /**
     * @param {Event} ev
     */
    onChange(ev) {
        let value = ev.target.value;
        if (this.props.meta.trim) {
            value = value.trim();
        }
        this.props.update(value || false);
    }
}
CharField.props = {
    ...standardFieldProps,
    autocomplete: { type: String, optional: true },
    password: { type: String, optional: true },
    placeholder: { type: String, optional: true },
};
CharField.template = "web.CharField";

registry.category("fields").add("char", CharField);
