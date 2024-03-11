/** @odoo-module **/

import { registry } from "@web/core/registry";
import { BooleanToggleField } from "./boolean_toggle_field";

export class ListBooleanToggleField extends BooleanToggleField {
    onClick() {
        if (!this.props.readonly) {
            this.props.update(!this.props.value, { save: this.props.autosave });
        }
    }
}

ListBooleanToggleField.template = "web.ListBooleanToggleField";

registry.category("fields").add("list.boolean_toggle", ListBooleanToggleField);
