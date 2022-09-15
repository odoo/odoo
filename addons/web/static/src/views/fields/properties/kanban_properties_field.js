/** @odoo-module **/

import { registry } from "@web/core/registry";
import { PropertiesField } from "./properties_field";

export class KanbanPropertiesField extends PropertiesField {

}

KanbanPropertiesField.template = "web.KanbanPropertiesField";

registry.category("fields").add("kanban.properties", KanbanPropertiesField);
