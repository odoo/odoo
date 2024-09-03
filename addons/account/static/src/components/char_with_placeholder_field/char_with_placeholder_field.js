/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { CharField, charField } from "@web/views/fields/char/char_field";

// Ensure that in Hoot tests, this module is loaded after `@mail/js/onchange_on_keydown`
// (needed because that module patches `charField`).
import "@mail/js/onchange_on_keydown";

export class CharWithPlaceholderField extends CharField {
    static template = "account.CharWithPlaceholderField";
    static props = {
        ...CharField.props,
        placeholderField: { type: String },
    };

    /** Override **/
    get formattedValue() {
        return super.formattedValue || this.placeholder;
    }

    get placeholder() {
        return this.props.record.data[this.props.placeholderField] || this.props.placeholder;
    }
}

export const charWithPlaceholderField = {
    ...charField,
    component: CharWithPlaceholderField,
    supportedOptions: [
        ...charField.supportedOptions,
        {
            label: _t("Placeholder field"),
            name: "placeholder_field",
            type: "field",
            availableTypes: ["char"],
        },
    ],
    extractProps: ({ attrs, options }) => ({
        ...charField.extractProps({ attrs, options }),
        placeholderField: options.placeholder_field,
    }),
};

registry.category("fields").add("char_with_placeholder_field", charWithPlaceholderField);
