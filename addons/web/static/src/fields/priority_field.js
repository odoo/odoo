/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;
const { useState } = owl.hooks;

export class PriorityField extends Component {
    setup() {
        this.state = useState({
            index: -1,
        });
    }

    get index() {
        return this.state.index > -1
            ? this.state.index
            : Object.keys(this.selection).indexOf(this.props.value);
    }
    get selection() {
        return Object.fromEntries(this.props.record.fields[this.props.name].selection);
    }

    /**
     * @param {string} value
     */
    onStarClicked(value) {
        const actualValue = this.props.value === value ? Object.keys(this.selection)[0] : value;
        this.props.update(actualValue);
    }
}

Object.assign(PriorityField, {
    template: "web.PriorityField",
    props: {
        ...standardFieldProps,
    },

    displayName: _lt("Priority"),
    supportedTypes: ["selection"],
});

registry.category("fields").add("priority", PriorityField);
