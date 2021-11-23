/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class PercentageField extends Component {
    get formattedValue() {
        let value = "";
        if (typeof this.props.value === "number") {
            value = `${
                this.percentageValue % 1 === 0
                    ? this.percentageValue
                    : this.percentageValue.toFixed(1)
            }%`;
        }
        return value;
    }
    get percentageValue() {
        return 100 * this.props.value;
    }
    /**
     * @param {Event} ev
     */
    onChange(ev) {
        let value = ev.target.value;
        if (this.props.record.fields[this.props.name].trim) {
            value = value.trim();
        }
        value = value / 100;
        this.props.update(value || false);
    }
}

PercentageField.props = {
    ...standardFieldProps,
};
PercentageField.template = "web.PercentageField";

registry.category("fields").add("percentage", PercentageField);
