import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useInputField } from "../input_field_hook";
import { standardFieldProps } from "../standard_field_props";
import { InputBox } from "@web/core/input_box/input_box";
import { useChildRef } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

export class EmailField extends Component {
    static template = "web.EmailField";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    };
    static components = { InputBox };

    setup() {
        this.input = useChildRef();
        useInputField({ ref: this.input, getValue: () => this.props.record.data[this.props.name] || "" });
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
    get overlayButtons() {
        return [
            {
                icon: "fa-envelope",
                href: 'mailto:' + this.props.record.data[this.props.name],
                name: _t("Send Email")
            }
        ]
    }
}

export const formEmailField = {
    ...emailField,
    component: FormEmailField,
};

registry.category("fields").add("form.email", formEmailField);
