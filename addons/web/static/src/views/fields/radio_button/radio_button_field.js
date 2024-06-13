import { radioField, RadioField } from "@web/views/fields/radio/radio_field";
import { registry } from "@web/core/registry";

export class RadioButtonField extends RadioField {
    static template = "web.RadioButtonField";
    static components = { ...super.components };
}

export const radioButtonField = {
    ...radioField,
    component: RadioButtonField,
};

registry.category("fields").add("radio_button", radioButtonField);
