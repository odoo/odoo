/** @odoo-module **/

import { registry } from "@web/core/registry";
import { BooleanToggleField } from "./boolean_toggle_field";

const { Component } = owl;

export class ListBooleanToggleField extends Component {
    onClick() {
        if (!this.props.readonly) {
            this.props.update(!this.props.value);
        }
    }
}

ListBooleanToggleField.template = "web.ListBooleanToggleField";
ListBooleanToggleField.components = { BooleanToggleField };

registry.category("fields").add("list.boolean_toggle", ListBooleanToggleField);
