import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useInputField } from "../input_field_hook";
import { standardFieldProps } from "../standard_field_props";
import { useChildRef } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class PhoneField extends Component {
    static template = "web.PhoneField";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
        formattedField: { type: String, optional: true },
        dialField: { type: String, optional: true },
    };
    static components = { Dropdown, DropdownItem };

    setup() {
        this.input = useChildRef();
        useInputField({ getValue: () => this.value || "" });
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
    extractProps: ({ options, placeholder }) => ({
        placeholder,
        formattedField: options.formatted_field,
        dialField: options.dial_field,
    }),
};

registry.category("fields").add("phone", phoneField);
