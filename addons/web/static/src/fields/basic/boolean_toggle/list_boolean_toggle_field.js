// @ts-check

/** @module @web/fields/basic/boolean_toggle/list_boolean_toggle_field - List-view variant of the Boolean toggle switch */

import { registry } from "@web/core/registry";

import { BooleanToggleField, booleanToggleField } from "./boolean_toggle_field";
export class ListBooleanToggleField extends BooleanToggleField {
    static template = "web.ListBooleanToggleField";

    /** Toggles the boolean value on click when editable. */
    async onClick() {
        if (!this.props.readonly && this.props.record.isInEdition) {
            const changes = {
                [this.props.name]: !this.props.record.data[this.props.name],
            };
            await this.props.record.update(changes, {
                save: this.props.autosave,
            });
        }
    }
}

export const listBooleanToggleField = {
    ...booleanToggleField,
    component: ListBooleanToggleField,
};

registry.category("fields").add("list.boolean_toggle", listBooleanToggleField);
