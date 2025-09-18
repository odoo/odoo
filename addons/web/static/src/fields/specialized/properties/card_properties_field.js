// @ts-check

/** @module @web/fields/specialized/properties/card_properties_field - Kanban/hierarchy card read-only variant of the properties field */

import { registry } from "@web/core/registry";

import { PropertiesField, propertiesField } from "./properties_field";
export class CardPropertiesField extends PropertiesField {
    static template = "web.CardPropertiesField";

    /** @returns {Promise<false>} Always denies definition write access in card views */
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
