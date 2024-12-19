import {
    many2ManyTagsFieldColorEditable,
    Many2ManyTagsFieldColorEditable,
} from "@web/views/fields/many2many_tags/many2many_tags_field";
import { registry } from "@web/core/registry";
import { TagsList } from "@web/core/tags_list/tags_list";
import { _t } from "@web/core/l10n/translation";

export class FieldMany2ManyTagsBanksTagsList extends TagsList {
    static template = "FieldMany2ManyTagsBanksTagsList";
}

export class FieldMany2ManyTagsBanks extends Many2ManyTagsFieldColorEditable {
    static components = {
        ...FieldMany2ManyTagsBanks.components,
        TagsList: FieldMany2ManyTagsBanksTagsList,
    };

    getTagProps(record) {
        return {
            ...super.getTagProps(record),
            allowOutPayment: record.data?.allow_out_payment,
        };
    }
}

export const fieldMany2ManyTagsBanks = {
    ...many2ManyTagsFieldColorEditable,
    component: FieldMany2ManyTagsBanks,
    supportedOptions: [
        ...(many2ManyTagsFieldColorEditable.supportedOptions || []),
        {
            label: _t("Allows out payments"),
            name: "allow_out_payment_field",
            type: "boolean",
        },
    ],
    additionalClasses: [
        ...(many2ManyTagsFieldColorEditable.additionalClasses || []),
        "o_field_many2many_tags",
    ],
    relatedFields: ({ options }) => {
        return [
            ...many2ManyTagsFieldColorEditable.relatedFields({ options }),
            { name: options.allow_out_payment_field, type: "boolean", readonly: false },
        ];
    },
};

registry.category("fields").add("many2many_tags_banks", fieldMany2ManyTagsBanks);
