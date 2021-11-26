/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class BooleanField extends Component {
    /**
     * @param {Event} ev
     */
    onChange(ev) {
        this.props.update(ev.target.checked);
    }
    /**
     * @param {MouseEvent} ev
     */
    onKeydown(ev) {
        switch (ev.key) {
            case "Enter":
                ev.preventDefault();
                this.props.update(!this.props.value);
                break;
        }
    }
}

Object.assign(BooleanField, {
    template: "web.BooleanField",
    props: {
        ...standardFieldProps,
    },

    displayName: _lt("Checkbox"),
    supportedTypes: ["boolean"],

    isEmpty() {
        return false;
    },
});

registry.category("fields").add("boolean", BooleanField);
