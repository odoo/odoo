/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";
import { parsePercentage } from "./parsers";

const { Component } = owl;

export class PercentageField extends Component {
    /**
     * @param {Event} ev
     */
    onChange(ev) {
        try {
            this.props.update(parsePercentage(ev.target.value));
        } catch (e) {
            this.props.record.setInvalidField(this.props.name);
        }
    }
}

PercentageField.template = "web.PercentageField";
PercentageField.props = {
    ...standardFieldProps,
};
PercentageField.displayName = _lt("Percentage");
PercentageField.supportedTypes = ["integer", "float"];

registry.category("fields").add("percentage", PercentageField);
