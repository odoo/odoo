/** @odoo-module **/

import { registry } from "@web/core/registry";
import { booleanToggleField, BooleanToggleField } from "./boolean_toggle_field";

export class ListBooleanToggleField extends BooleanToggleField {
    static template = "web.ListBooleanToggleField";

    onClick() {
        if (!this.props.readonly) {
            this.props.record.update({
                [this.props.name]: !this.props.record.data[this.props.name],
            });
        }
    }
}

export const listBooleanToggleField = {
    ...booleanToggleField,
    component: ListBooleanToggleField,
};

registry.category("fields").add("list.boolean_toggle", listBooleanToggleField);
