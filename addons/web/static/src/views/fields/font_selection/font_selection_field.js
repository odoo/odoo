/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";
import { formatSelection } from "../formatters";

const { Component } = owl;

export class FontSelectionField extends Component {
    get string() {
        return formatSelection(this.props.value, { selection: this.props.options });
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
    required: { type: Boolean, optional: true },
};
FontSelectionField.defaultProps = {
    required: false,
};

FontSelectionField.displayName = _lt("Font Selection");
FontSelectionField.supportedTypes = ["selection"];

FontSelectionField.extractProps = (fieldName, record, attrs) => {
    return {
        options: Array.from(record.fields[fieldName].selection),
        required: record.isRequired(fieldName),
        placeholder: attrs.placeholder,
    };
};

registry.category("fields").add("font", FontSelectionField);
