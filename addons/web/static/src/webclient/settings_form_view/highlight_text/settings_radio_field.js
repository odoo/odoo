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
};

registry.category("fields").add("base_settings.radio", settingsRadioField);
