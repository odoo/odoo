// @ts-check

/** @module @web/views/settings/highlight_text/settings_radio_field - RadioField variant with search-term highlighting on option labels */

import { registry } from "@web/core/registry";
import { RadioField, radioField } from "@web/fields/selection/radio/radio_field";

import { HighlightText } from "./highlight_text";
/** RadioField variant with search-term highlighting on option labels. */
export class SettingsRadioField extends RadioField {
    static template = "web.SettingsRadioField";
    static components = {
        .../** @type {any} */ (RadioField).components,
        HighlightText,
    };
}

export const settingsRadioField = {
    ...radioField,
    component: SettingsRadioField,
};

registry.category("fields").add("base_settings.radio", settingsRadioField);
