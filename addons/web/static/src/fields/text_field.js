/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class TextField extends Component {
    onChange(ev) {
        this.props.record.update(this.props.name, ev.target.value);
    }
}

Object.assign(TextField, {
    template: "web.TextField",
    props: {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    },

    displayName: _lt("Multiline Text"),
    supportedTypes: ["html", "text"],
});

registry.category("fields").add("text", TextField);
registry.category("fields").add("html", TextField);
