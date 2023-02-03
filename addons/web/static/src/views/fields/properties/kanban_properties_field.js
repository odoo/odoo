/** @odoo-module **/

import { registry } from "@web/core/registry";
import { propertiesField, PropertiesField } from "./properties_field";

export class KanbanPropertiesField extends PropertiesField {
    static template = "web.KanbanPropertiesField";

    async _checkDefinitionAccess() {
        // can not edit properties definition in the kanban view
        this.state.canChangeDefinition = false;
    }
}

export const kanbanPropertiesField = {
    ...propertiesField,
    component: KanbanPropertiesField,
};

registry.category("fields").add("kanban.properties", kanbanPropertiesField);
