import { registry } from '@web/core/registry';
import { ListBooleanToggleField, listBooleanToggleField } from "@web/views/fields/boolean_toggle/list_boolean_toggle_field";

export class ListBooleanToggleLoadField extends ListBooleanToggleField {
    async onChange(newValue) {
        this.state.value = newValue;
        // technical_is_new_default ensure to the backend which level trigger the onchange
        const changes = { [this.props.name]: newValue, technical_is_new_default: newValue };
        await this.props.record.update(changes, { save: this.props.autosave });
    }
}

export const listBooleanToggleLoadField = {
    ...listBooleanToggleField,
    component: ListBooleanToggleLoadField,
};

registry.category("fields").add("boolean_toggle_load", listBooleanToggleLoadField);
