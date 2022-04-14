/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2ManyTagsField } from "./many2many_tags_field";

class ListMany2ManyTagsField extends Many2ManyTagsField {
    get canOpenColorDropdown() {
        return false;
    }
}
registry.category("fields").add("list.many2many_tags", ListMany2ManyTagsField);
