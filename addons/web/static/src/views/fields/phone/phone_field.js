import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useInputField } from "../input_field_hook";
import { standardFieldProps } from "../standard_field_props";
import { browser } from "@web/core/browser/browser";
import { Component, props, signal, t } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export const phoneFieldProps = {
    ...standardFieldProps,
    placeholder: t.string().optional(),
    formattedField: t.string().optional(),
    dialField: t.string().optional(),
    displayButtons: t.boolean().optional(true),
};

export class PhoneField extends Component {
    static template = "web.PhoneField";
    props = props(phoneFieldProps);
    static components = { Dropdown, DropdownItem };

    inputRef = signal(null);

    setup() {
        useInputField({ ref: this.inputRef, getValue: () => this.value || "" });
    }

    get value() {
        const { name, record } = this.props;
        const formattedField = this.props.formattedField || `${name}_formatted`;
        return record.data[formattedField] || record.data[name];
    }

    get dialNumber() {
        const { name, record } = this.props;
        const dialField = this.props.dialField || `${name}_sanitized`;
        return record.data[dialField] || record.data[name];
    }

    get phoneHref() {
        return "tel:" + this.dialNumber.replace(/\s+/g, "");
    }

    get actionButtons() {
        return [
            {
                icon: "fa-phone",
                onSelected: () => this.onLinkClicked(),
                name: _t("Call"),
            },
        ];
    }

    onLinkClicked() {
        browser.open(this.phoneHref);
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
        {
            label: _t("Formatted Field"),
            name: "formatted_field",
            type: "field",
            availableTypes: ["char"],
        },
        {
            label: _t("Dial Field"),
            name: "dial_field",
            type: "field",
            availableTypes: ["char"],
        },
    ],
    supportedTypes: ["char"],
    extractProps: ({ options, placeholder, viewType }) => ({
        placeholder,
        formattedField: options.formatted_field,
        dialField: options.dial_field,
        displayButtons: viewType === "form",
    }),
};

registry.category("fields").add("phone", phoneField);
