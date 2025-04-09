import { registry } from "@web/core/registry";
import { propertiesField, PropertiesField } from "./properties_field";

export class CalendarCardPropertiesField extends PropertiesField {
    static template = "web.CalendarCardPropertiesField";
    async checkDefinitionWriteAccess() {
        return false;
    }
}

export const calendarCardPropertiesField = {
    ...propertiesField,
    component: CalendarCardPropertiesField,
    additionalClasses: ["d-flex", "flex-column", "gap-3"],
};

registry.category("fields").add("calendar.properties", calendarCardPropertiesField);
