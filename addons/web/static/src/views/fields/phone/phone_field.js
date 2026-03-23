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
    };
    static components = { Dropdown, DropdownItem };

    setup() {
        this.input = useChildRef();
        useInputField({ getValue: () => this.props.record.data[this.props.name] || "" });
    }

    get phoneHref() {
        return "tel:" + this.props.record.data[this.props.name].replace(/\s+/g, "");
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
    ],
    supportedTypes: ["char"],
    extractProps: ({ placeholder }) => ({
        placeholder,
    }),
};

registry.category("fields").add("phone", phoneField);
