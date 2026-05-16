import { registry } from "@web/core/registry";
import {
    Many2ManyTagsField,
    many2ManyTagsField,
} from "@web/views/fields/many2many_tags/many2many_tags_field";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

export class Many2ManyTagsJournalsMany2xAutocomplete extends Many2XAutocomplete {
    static template = "account.Many2ManyTagsJournalsMany2xAutocomplete";
    static props = {
        ...Many2XAutocomplete.props,
        group_company_id: { type: Number, optional: true },
    };

    get searchSpecification() {
        return {
            ...super.searchSpecification,
            company_id: {
                fields: {
                    display_name: {},
                },
            },
        };
    }
}

export class Many2ManyTagsJournals extends Many2ManyTagsField {
    static template = "account.Many2ManyTagsJournals";
    static components = {
        ...Many2ManyTagsField.components,
        Many2XAutocomplete: Many2ManyTagsJournalsMany2xAutocomplete,
    };

    getTagProps(record) {
        const group_company_id = this.props.record.data["company_id"];

        const text = group_company_id
            ? record.data.display_name
            : `${record.data.company_id.display_name} - ${record.data.display_name}`;
        return {
            ...super.getTagProps(record),
            text,
        };
    }
}

export const fieldMany2ManyTagsJournals = {
    ...many2ManyTagsField,
    component: Many2ManyTagsJournals,
    relatedFields: (fieldInfo) => [
        ...many2ManyTagsField.relatedFields(fieldInfo),
        { name: "company_id", type: "many2one", relation: "res.company" },
    ],
};

registry.category("fields").add("many2many_tags_journals", fieldMany2ManyTagsJournals);
