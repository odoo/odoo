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
        let parsedValue;
        try {
            parsedValue = this.props.parse(ev.target.value);
        } catch (e) {
            // FIXME WOWL check error
            this.props.setAsInvalid(this.props.name);
            return;
        }
        this.props.update(parsedValue);
    }
}

PercentageField.template = "web.PercentageField";
PercentageField.defaultProps = {
    setAsInvalid: () => {},
};
PercentageField.props = {
    ...standardFieldProps,
    setAsInvalid: { type: Function, optional: true },
};
PercentageField.extractProps = (fieldName, record) => {
    return {
        setAsInvalid: record.setInvalidField.bind(record),
    };
};
PercentageField.displayName = _lt("Percentage");
PercentageField.supportedTypes = ["integer", "float"];

registry.category("fields").add("percentage", PercentageField);
