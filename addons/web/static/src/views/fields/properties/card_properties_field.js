import { registry } from "@web/core/registry";
import { propertiesField, PropertiesField } from "./properties_field";

export class CardPropertiesField extends PropertiesField {
    static template = "web.CardPropertiesField";

    async _checkDefinitionAccess() {
        // can not edit properties definition in cards
        this.state.canChangeDefinition = false;
    }
}

export const cardPropertiesField = {
    ...propertiesField,
    component: CardPropertiesField,
};

registry.category("fields").add("calendar.properties", cardPropertiesField);
registry.category("fields").add("kanban.properties", cardPropertiesField);
registry.category("fields").add("hierarchy.properties", cardPropertiesField);
