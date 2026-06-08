import { booleanField, BooleanField } from "@web/views/fields/boolean/boolean_field";
import { registry } from "@web/core/registry";

export class BooleanCheckboxField extends BooleanField {
    get displayAsToggle() {
        return false;
    }
}

export const booleanCheckboxField = {
    ...booleanField,
    component: BooleanCheckboxField,
};
registry.category("fields").add("boolean_checkbox", booleanCheckboxField);
