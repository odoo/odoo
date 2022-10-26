/** @odoo-module **/

import { registry } from "@web/core/registry";
import { PropertiesField } from "./properties_field";

export class KanbanPropertiesField extends PropertiesField {
    async _checkDefinitionAccess() {
        // can not edit properties definition in the kanban view
        this.state.canChangeDefinition = false;
    }
}

KanbanPropertiesField.template = "web.KanbanPropertiesField";

registry.category("fields").add("kanban.properties", KanbanPropertiesField);
