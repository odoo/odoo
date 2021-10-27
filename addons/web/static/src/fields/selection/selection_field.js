/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "../standard_field_props";

const { Component } = owl;

export class SelectionField extends Component {
    get selection() {
        return Object.fromEntries(this.props.record.fields[this.props.name].selection);
    }
    get string() {
        return this.props.value ? this.selection[this.props.value] : "";
    }
    get value() {
        const rawValue = this.props.value;
        return this.props.type === "many2one" && rawValue ? rawValue.data.id : rawValue;
    }

    /**
     * @param {Event} ev
     */
    onChange(ev) {
        this.props.update(ev.target.value);
    }
}
SelectionField.props = {
    ...standardFieldProps,
    placeholder: { type: String, optional: true },
};
SelectionField.template = "web.SelectionField";

registry.category("fields").add("selection", SelectionField);
