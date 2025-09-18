// @ts-check

/** @module @web/fields/basic/email/email_field - Email input field with mailto link in readonly mode */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useInputField } from "@web/fields/input_field_hook";
import { standardFieldProps } from "@web/fields/standard_field_props";

export class EmailField extends Component {
    static template = "web.EmailField";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    };

    setup() {
        useInputField({
            getValue: () => this.props.record.data[this.props.name] || "",
        });
    }
}

export const emailField = {
    component: EmailField,
    displayName: _t("Email"),
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

registry.category("fields").add("email", emailField);

class FormEmailField extends EmailField {
    static template = "web.FormEmailField";
}

export const formEmailField = {
    ...emailField,
    component: FormEmailField,
};

registry.category("fields").add("form.email", formEmailField);
