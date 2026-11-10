import { registry } from "@web/core/registry";
import { propertiesField, PropertiesField, propertiesFieldProps } from "./properties_field";
import { t, useProps } from "@odoo/owl";

export class CardPropertiesField extends PropertiesField {
    static template = "web.CardPropertiesField";

    props = useProps({
        ...propertiesFieldProps,
        icon: t.string().optional(),
        iconClass: t.string().optional(),
    });

    async checkDefinitionWriteAccess() {
        return false;
    }
}

export const cardPropertiesField = {
    ...propertiesField,
    component: CardPropertiesField,
    extractProps({ attrs }, dynamicInfo) {
        return {
            ...propertiesField.extractProps({ attrs }, dynamicInfo),
            icon: attrs.icon,
            iconClass: attrs.iconClass,
        };
    },
};

registry.category("fields").add("card.properties", cardPropertiesField);
registry.category("fields").add("hierarchy.properties", cardPropertiesField);
