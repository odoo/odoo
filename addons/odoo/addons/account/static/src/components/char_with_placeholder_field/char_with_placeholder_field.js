/** @odoo-module **/

import { registry } from "@web/core/registry";
import { CharField, charField } from "@web/views/fields/char/char_field";

// Ensure that in Hoot tests, this module is loaded after `@mail/js/onchange_on_keydown`
// (needed because that module patches `charField`).
import "@mail/js/onchange_on_keydown";

export class CharWithPlaceholderField extends CharField {
    static template = "account.CharWithPlaceholderField";

    /** Override **/
    get formattedValue() {
        return super.formattedValue || this.placeholder;
    }
}

export const charWithPlaceholderField = {
    ...charField,
    component: CharWithPlaceholderField,
};

registry.category("fields").add("char_with_placeholder_field", charWithPlaceholderField);
