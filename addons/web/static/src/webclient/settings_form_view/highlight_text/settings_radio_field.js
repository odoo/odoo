/** @odoo-module **/

import { registry } from "@web/core/registry";
import { RadioField } from "@web/views/fields/radio/radio_field";
import { FormLabelHighlightText } from "./form_label_highlight_text";

export class SettingsRadioField extends RadioField {}

SettingsRadioField.extractStringExpr = (fieldName, record) => {
    const radioItems = SettingsRadioField.getItems(fieldName, record);
    return radioItems.map((r) => r[1]);
};
SettingsRadioField.template = "web.SettingsRadioField";
SettingsRadioField.components = { ...RadioField.components, FormLabelHighlightText };

registry.category("fields").add("base_settings.radio", SettingsRadioField);
