/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

const { Component, useState } = owl;

export class PriorityField extends Component {
    setup() {
        this.state = useState({
            index: -1,
        });
    }

    get index() {
        return this.state.index > -1
            ? this.state.index
            : this.selection.findIndex((o) => o[0] === this.props.value);
    }
    get selection() {
        return this.props.record.fields[this.props.name].selection;
    }

    /**
     * @param {string} value
     */
    onStarClicked(value, ev) {
        ev.stopPropagation();
        ev.preventDefault();
        const actualValue = this.props.value === value ? this.selection[0][0] : value;
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
