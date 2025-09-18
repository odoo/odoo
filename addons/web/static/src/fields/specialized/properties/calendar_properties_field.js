// @ts-check

/** @module @web/fields/specialized/properties/calendar_properties_field - Calendar-view read-only variant of the properties field */

import { registry } from "@web/core/registry";

import { PropertiesField, propertiesField } from "./properties_field";
export class CalendarPropertiesField extends PropertiesField {
    static template = "web.CalendarPropertiesField";
    /** @returns {Promise<false>} Always denies definition write access in calendar view */
    async checkDefinitionWriteAccess() {
        return false;
    }
}

export const calendarPropertiesField = {
    ...propertiesField,
    component: CalendarPropertiesField,
};

registry.category("fields").add("calendar.properties", calendarPropertiesField);
