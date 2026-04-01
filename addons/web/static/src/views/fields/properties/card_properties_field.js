import { registry } from "@web/core/registry";
import { propertiesField, PropertiesField } from "./properties_field";

export class CardPropertiesField extends PropertiesField {
    static template = "web.CardPropertiesField";

    async checkDefinitionWriteAccess() {
        return false;
    }
}

export const cardPropertiesField = {
    ...propertiesField,
    component: CardPropertiesField,
};

registry.category("fields").add("kanban.properties", cardPropertiesField);
registry.category("fields").add("hierarchy.properties", cardPropertiesField);
