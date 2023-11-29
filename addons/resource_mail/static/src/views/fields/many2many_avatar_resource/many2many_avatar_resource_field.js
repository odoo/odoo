/** @odoo-module **/

import { registry } from "@web/core/registry";
import { usePopover } from "@web/core/popover/popover_hook";
import {
    Many2ManyTagsAvatarUserField,
    many2ManyTagsAvatarUserField,
    Many2ManyAvatarUserTagsList,
} from "@mail/views/web/fields/many2many_avatar_user_field/many2many_avatar_user_field";
import { AvatarMany2XAutocomplete } from "@web/views/fields/relational_utils";
import { AvatarCardResourcePopover } from "@resource_mail/components/avatar_card_resource/avatar_card_resource_popover";
import { Domain } from "@web/core/domain";


class AvatarResourceMany2XAutocomplete extends AvatarMany2XAutocomplete {
    get optionsSource() {
        return {
            ...super.optionsSource,
            optionTemplate: "resource_mail.AvatarResourceMany2XAutocomplete",
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

class Many2ManyAvatarResourceTagsList extends Many2ManyAvatarUserTagsList {
    static template = "resource_mail.Many2ManyAvatarResourceTagsList";
}

export class Many2ManyAvatarResourceField extends Many2ManyTagsAvatarUserField {
    setup() {
        super.setup(...arguments);
        if (this.relation == "resource.resource") {
            this.avatarCard = usePopover(AvatarCardResourcePopover);
        }
    }

    static components = {
        ...super.components,
        Many2XAutocomplete: AvatarResourceMany2XAutocomplete,
        TagsList: Many2ManyAvatarResourceTagsList,
    };

    displayAvatarCard(record) {
        return !this.env.isSmall && this.relation === "resource.resource" && record.data.resource_type === "user";
    }

    getTagProps(record) {
        return {
            ...super.getTagProps(...arguments),
            icon: record.data.resource_type === "user" ? null : "fa-wrench",
            img: record.data.resource_type === "user"
                ? `/web/image/${this.relation}/${record.resId}/avatar_128`
                : null,
        };
    }
}

export const many2ManyAvatarResourceField = {
    ...many2ManyTagsAvatarUserField,
    component: Many2ManyAvatarResourceField,
    additionalClasses: ["o_field_many2many_tags_avatar"],
    relatedFields: (fieldInfo) => {
        return [
            ...many2ManyTagsAvatarUserField.relatedFields(fieldInfo),
            {
                name: "resource_type",
                type: "selection",
            },
        ];
    },
};

registry.category("fields").add("many2many_avatar_resource", many2ManyAvatarResourceField);
