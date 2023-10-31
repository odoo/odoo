/** @odoo-module */

import { registry } from '@web/core/registry';
import {
    booleanToggleField,
    BooleanToggleField,
} from "@web/views/fields/boolean_toggle/boolean_toggle_field";

export class BooleanToggleLoadField extends BooleanToggleField {
    async onChange(value) {
        await super.onChange(value);
        return this.env.model.load();
    }
}

export const booleanToggleLoadField = {
    ...booleanToggleField,
    component: BooleanToggleLoadField,
};

registry.category("fields").add("boolean_toggle_load", booleanToggleLoadField);
