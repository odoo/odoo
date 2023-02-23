/** @odoo-module **/

import { registry } from "@web/core/registry";
import { radioField, RadioField } from "@web/views/fields/radio/radio_field";
import { HighlightText } from "./highlight_text";

export class SettingsRadioField extends RadioField {
    static template = "web.SettingsRadioField";
    static components = { ...super.components, HighlightText };
}

export const settingsRadioField = {
    ...radioField,
    component: SettingsRadioField,
    extractStringExpr(fieldName, record) {
        const radioItems = SettingsRadioField.getItems(fieldName, record);
        return radioItems.map((r) => r[1]);
    },
};

registry.category("fields").add("base_settings.radio", settingsRadioField);
