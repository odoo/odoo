/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useInputField } from "../input_field_hook";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

export class PhoneField extends Component {
    static template = "web.PhoneField";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    };

    setup() {
        useInputField({ getValue: () => this.props.record.data[this.props.name] || "" });
    }
    get phoneHref() {
        return "tel:" + this.props.record.data[this.props.name].replace(/\s+/g, "");
    }
}

export const phoneField = {
    component: PhoneField,
    displayName: _t("Phone"),
    supportedTypes: ["char"],
    extractProps: ({ attrs }) => ({
        placeholder: attrs.placeholder,
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
