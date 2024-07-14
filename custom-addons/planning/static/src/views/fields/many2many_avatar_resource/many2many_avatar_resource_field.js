/** @odoo-module **/

import { registry } from "@web/core/registry";
import {
    Many2ManyTagsAvatarField,
    many2ManyTagsAvatarField,
} from "@web/views/fields/many2many_tags_avatar/many2many_tags_avatar_field";
import { AvatarMany2XAutocomplete } from "@web/views/fields/relational_utils";
import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";

class AvatarResourceMany2XAutocomplete extends AvatarMany2XAutocomplete {
    get optionsSource() {
        return {
            ...super.optionsSource,
            optionTemplate: "planning.AvatarResourceMany2XAutocomplete",
        };
    }

    /**
     * @override
     */
    search(request) {
        return this.orm.call(
            this.props.resModel,
            "search_read",
            [this.getDomain(request), ["id", "display_name", "resource_type"]],
            {
                context: this.props.context,
                limit: this.props.searchLimit + 1,
            }
        );
    }

    /**
     * @override
     */
    getDomain(request) {
        return Domain.and([[["name", "ilike", request]], this.props.getDomain()]).toList(
            this.props.context
        );
    }

    /**
     * @override
     */
    mapRecordToOption(result) {
        return {
            resModel: this.props.resModel,
            value: result.id,
            resourceType: result.resource_type,
            label: result.display_name,
        };
    }
}

export class Many2ManyAvatarResourceField extends Many2ManyTagsAvatarField {
    static components = {
        ...super.components,
        Many2XAutocomplete: AvatarResourceMany2XAutocomplete,
    };

    getTagProps(record) {
        return {
            ...super.getTagProps(record),
            icon: record.data.resource_type == "user" ? null : "fa-wrench",
            img:
                record.data.resource_type == "user"
                    ? `/web/image/${this.relation}/${record.resId}/avatar_128`
                    : null,
        };
    }
}

export const many2ManyAvatarResourceField = {
    ...many2ManyTagsAvatarField,
    component: Many2ManyAvatarResourceField,
    fieldDependencies: [{ name: "resource_ids", type: "many2many" }],
    additionalClasses: ["o_field_many2many_tags_avatar"],
    relatedFields: (fieldInfo) => {
        return [
            ...many2ManyTagsAvatarField.relatedFields(fieldInfo),
            {
                name: "resource_type",
                type: "selection",
                selection: [
                    ["user", _t("Human")],
                    ["material", _t("Material")],
                ],
            },
        ];
    },
};

registry.category("fields").add("many2many_avatar_resource", many2ManyAvatarResourceField);
