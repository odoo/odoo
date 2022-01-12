/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class PercentageField extends Component {
    /**
     * @param {Event} ev
     */
    onChange(ev) {
        let isValid = true;
        let value = ev.target.value;
        try {
            value = this.props.parseValue(value);
        } catch (e) {
            isValid = false;
            this.props.record.setInvalidField(this.props.name);
        }
        if (isValid) {
            this.props.update(value);
        }
    }
}

Object.assign(PercentageField, {
    template: "web.PercentageField",
    props: {
        ...standardFieldProps,
    },

    displayName: _lt("Percentage"),
    supportedTypes: ["integer", "float"],
});

registry.category("fields").add("percentage", PercentageField);
