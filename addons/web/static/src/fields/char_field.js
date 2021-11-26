/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class CharField extends Component {
    get formattedValue() {
        let value = typeof this.props.value === "string" ? this.props.value : "";
        if (this.isPassword) {
            value = "*".repeat(value.length);
        }
        return value;
    }
    get shouldTrim() {
        return this.props.record.fields[this.props.name].trim;
    }
    get maxLength() {
        return this.props.record.fields[this.props.name].size;
    }
    get isPassword() {
        return "password" in this.props.attrs;
    }

    /**
     * @param {Event} ev
     */
    onChange(ev) {
        let value = ev.target.value;
        if (this.shouldTrim) {
            value = value.trim();
        }
        this.props.update(value || false);
    }
}

Object.assign(CharField, {
    template: "web.CharField",
    props: {
        ...standardFieldProps,
        autocomplete: { type: String, optional: true },
        password: { type: String, optional: true },
        placeholder: { type: String, optional: true },
    },

    displayName: _lt("Text"),
    supportedTypes: ["char"],
});

CharField.template = "web.CharField";

registry.category("fields").add("char", CharField);
