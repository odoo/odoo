/** @odoo-module */

import { registry } from '@web/core/registry';
import { ListBooleanToggleField, listBooleanToggleField } from "@web/views/fields/boolean_toggle/list_boolean_toggle_field";

export class ListBooleanToggleLoadField extends ListBooleanToggleField {
    async onChange(value) {
        await super.onChange(value);
        await this.props.record.save();
        return this.env.model.load();
    }
}

export const listBooleanToggleLoadField = {
    ...listBooleanToggleField,
    component: ListBooleanToggleLoadField,
};

registry.category("fields").add("boolean_toggle_load", listBooleanToggleLoadField);
