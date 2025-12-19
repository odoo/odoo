import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useInputField } from "../input_field_hook";
import { standardFieldProps } from "../standard_field_props";
import { InputBox } from "@web/core/input_box/input_box";
import { useChildRef } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { Component } from "@odoo/owl";

export class PhoneField extends Component {
    static template = "web.PhoneField";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    };
    static components = { InputBox };

    setup() {
        this.input = useChildRef();
        useInputField({ ref: this.input, getValue: () => this.props.record.data[this.props.name] || "" });
    }
    get inlineButtons() {
        return [];
    }
    get phoneHref() {
        return "tel:" + this.props.record.data[this.props.name].replace(/\s+/g, "");
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

export class FormPhoneField extends PhoneField {
    get overlayButtons() {
        return [
            {
                icon: "fa-phone",
                onSelected: () => this.onLinkClicked(),
                name: _t("Call")
            }
        ]
    }
    get inlineButtons() {
        return this.overlayButtons.filter(btn => btn.showInReadonly);
    }
}

export const formPhoneField = {
    ...phoneField,
    component: FormPhoneField,
};

registry.category("fields").add("form.phone", formPhoneField);
