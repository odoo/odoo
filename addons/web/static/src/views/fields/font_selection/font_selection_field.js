/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";
import { formatSelection } from "../formatters";

import { Component } from "@odoo/owl";

export class FontSelectionField extends Component {
    static template = "web.FontSelectionField";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    };

    get options() {
        return this.props.record.fields[this.props.name].selection.filter(
            (option) => option[0] !== false && option[1] !== ""
        );
    }
    get isRequired() {
        return this.props.record.isRequired(this.props.name);
    }
    get string() {
        return formatSelection(this.props.record.data[this.props.name], {
            selection: this.options,
        });
    }

    stringify(value) {
        return JSON.stringify(value);
    }

    /**
     * @param {Event} ev
     */
    onChange(ev) {
        const value = JSON.parse(ev.target.value);
        this.props.record.update({ [this.props.name]: value });
    }
}

export const fontSelectionField = {
    component: FontSelectionField,
    displayName: _lt("Font Selection"),
    supportedTypes: ["selection"],
    extractProps: ({ attrs }) => ({
        placeholder: attrs.placeholder,
    }),
    legacySpecialData: "_fetchSpecialRelation",
};

registry.category("fields").add("font", fontSelectionField);
