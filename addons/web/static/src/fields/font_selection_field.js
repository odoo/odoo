/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class FontSelectionField extends Component {
    get string() {
        return this.props.value !== false
            ? this.props.options.find((o) => o[0] === this.props.value)[1]
            : "";
    }

    stringify(value) {
        return JSON.stringify(value);
    }

    /**
     * @param {Event} ev
     */
    onChange(ev) {
        const value = JSON.parse(ev.target.value);
        this.props.update(value);
    }
}

FontSelectionField.template = "web.FontSelectionField";
FontSelectionField.props = {
    ...standardFieldProps,
    options: Object,
    placeholder: { type: String, optional: true },
};
FontSelectionField.extractProps = (fieldName, record) => {
    return {
        options: record.fields[fieldName].selection,
    };
};
FontSelectionField.displayName = _lt("Font Selection");
FontSelectionField.supportedTypes = ["selection"];

registry.category("fields").add("font", FontSelectionField);
