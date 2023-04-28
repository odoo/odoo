/** @odoo-module **/

import { registry } from "@web/core/registry";
import { booleanToggleField, BooleanToggleField } from "./boolean_toggle_field";

export class ListBooleanToggleField extends BooleanToggleField {
    static template = "web.ListBooleanToggleField";

    async onClick() {
        if (!this.props.readonly && this.props.record.isInEdition) {
            await this.props.record.update({
                [this.props.name]: !this.props.record.data[this.props.name],
            });
            if (this.props.autosave) {
                return this.props.record.save();
            }
        }
    }
}

export const listBooleanToggleField = {
    ...booleanToggleField,
    component: ListBooleanToggleField,
};

registry.category("fields").add("list.boolean_toggle", listBooleanToggleField);
