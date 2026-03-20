import { registry } from "@web/core/registry";
import { propertiesField, PropertiesField } from "./properties_field";

export class CalendarPropertiesField extends PropertiesField {
    static template = "web.CalendarPropertiesField";
    async checkDefinitionWriteAccess() {
        return false;
    }
}

export const calendarPropertiesField = {
    ...propertiesField,
    component: CalendarPropertiesField,
};

registry.category("fields").add("calendar.properties", calendarPropertiesField);
