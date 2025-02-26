import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import {
    Many2ManyTagsField,
    many2ManyTagsField,
} from "@web/views/fields/many2many_tags/many2many_tags_field";
import { registry } from "@web/core/registry";

export class Many2XBarcodeTagsAutocomplete extends Many2XAutocomplete {
    onQuickCreateError(error, request) {
        if (error.data?.debug && error.data.debug.includes("psycopg2.errors.UniqueViolation")) {
            throw error;
        }
        super.onQuickCreateError(error, request);
    }
}

export class Many2ManyBarcodeTagsField extends Many2ManyTagsField {
    static components = {
        ...Many2ManyTagsField.components,
        Many2XAutocomplete: Many2XBarcodeTagsAutocomplete,
    };
}

export const many2ManyBarcodeTagsField = {
    ...many2ManyTagsField,
    component: Many2ManyBarcodeTagsField,
    additionalClasses: ['o_field_many2many_tags'],
}

registry.category("fields").add("many2many_barcode_tags", many2ManyBarcodeTagsField);
