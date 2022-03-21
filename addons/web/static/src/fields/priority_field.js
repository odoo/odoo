/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

const { Component, useState } = owl;

// WOWL FIXME: in master, if a priority field is readonly, there is no feedback when hovering it,
// which is correct, but if we click on it, there's a crash. It would be nice if we don't have the
// crash in master-wowl, and if we add a test to assert this behavior

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

    getTooltip(value) {
        return this.props.tooltipLabel ? `${this.props.tooltipLabel}: ${value}` : value;
    }
    /**
     * @param {string} value
     */
    onStarClicked(value) {
        if (this.props.value === value) {
            this.state.index = -1;
            this.props.update(this.selection[0][0]);
        } else {
            this.props.update(value);
        }
    }
}

PriorityField.template = "web.PriorityField";
PriorityField.props = {
    ...standardFieldProps,
    tooltipLabel: { type: String, optional: true },
};
PriorityField.extractProps = (fieldName, record) => {
    return {
        tooltipLabel: record.fields[fieldName].string,
    };
};
PriorityField.displayName = _lt("Priority");
PriorityField.supportedTypes = ["selection"];

registry.category("fields").add("priority", PriorityField);
