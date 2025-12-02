import { registry } from "@web/core/registry";
import {
    charWithPlaceholderField,
    CharWithPlaceholderField
} from "../char_with_placeholder_field/char_with_placeholder_field";

export class CharWithPlaceholderFieldToCheck extends CharWithPlaceholderField {
    static template = "account.CharWithPlaceholderField";
}

export const charWithPlaceholderFieldToCheck = {
    ...charWithPlaceholderField,
    component: CharWithPlaceholderFieldToCheck,
};

registry.category("fields").add("char_with_placeholder_field_to_check", charWithPlaceholderFieldToCheck);
