/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";
import { formatSelection } from "../formatters";

import { Component } from "@odoo/owl";

export class FontSelectionField extends Component {
    static template = "web.FontSelectionField";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
        required: { type: Boolean, optional: true },
    };

    get options() {
        return this.props.record.fields[this.props.name].selection.filter(
            (option) => option[0] !== false && option[1] !== ""
        );
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
    displayName: _t("Font Selection"),
    supportedTypes: ["selection"],
    extractProps({ attrs }, dynamicInfo) {
        return {
            placeholder: attrs.placeholder,
            required: dynamicInfo.required,
        };
    },
};

registry.category("fields").add("font", fontSelectionField);
