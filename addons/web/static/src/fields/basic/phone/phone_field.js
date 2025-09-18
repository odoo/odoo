// @ts-check

/** @module @web/fields/basic/phone/phone_field - Phone number input field with tel: link in readonly mode */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useInputField } from "@web/fields/input_field_hook";
import { standardFieldProps } from "@web/fields/standard_field_props";

export class PhoneField extends Component {
    static template = "web.PhoneField";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    };

    setup() {
        useInputField({
            getValue: () => this.props.record.data[this.props.name] || "",
        });
    }
    /** @returns {string} tel: URI with whitespace stripped */
    get phoneHref() {
        return `tel:${(this.props.record.data[this.props.name] || "").replace(/\s+/g, "")}`;
    }
}

export const phoneField = {
    component: PhoneField,
    displayName: _t("Phone"),
    supportedOptions: [
        {
            label: _t("Dynamic Placeholder"),
            name: "placeholder_field",
            type: "field",
            availableTypes: ["char"],
        },
    ],
    supportedTypes: ["char"],
    extractProps: ({ placeholder }) => ({
        placeholder,
    }),
};

registry.category("fields").add("phone", phoneField);

class FormPhoneField extends PhoneField {
    static template = "web.FormPhoneField";
}

export const formPhoneField = {
    ...phoneField,
    component: FormPhoneField,
};

registry.category("fields").add("form.phone", formPhoneField);
