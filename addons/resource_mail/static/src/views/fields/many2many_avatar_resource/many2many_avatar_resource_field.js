import { registry } from "@web/core/registry";
import { usePopover } from "@web/core/popover/popover_hook";
import { _t } from "@web/core/l10n/translation";
import {
    KanbanMany2ManyTagsAvatarUserField,
    ListMany2ManyTagsAvatarUserField,
    Many2ManyTagsAvatarUserField,
    kanbanMany2ManyTagsAvatarUserField,
    listMany2ManyTagsAvatarUserField,
    many2ManyTagsAvatarUserField,
} from "@mail/views/web/fields/many2many_avatar_user_field/many2many_avatar_user_field";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { AvatarCardResourcePopover } from "@resource_mail/components/avatar_card_resource/avatar_card_resource_popover";
import { Domain } from "@web/core/domain";
import { AvatarTag } from "@web/core/tags_list/avatar_tag";
import { Component } from "@odoo/owl";

export class AvatarResourceMany2XAutocomplete extends Many2XAutocomplete {
    /**
     * @override
     */
    search(request) {
        return this.orm.call(
            this.props.resModel,
            "search_read",
            [this.getDomain(request), ["id", "display_name", "resource_type", "color"]],
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
}

class ResourceTag extends Component {
    static template = "resource_mail.ResourceTag";
    static components = { AvatarTag };
    static props = {
        color: { type: Number, optional: true },
        imageUrl: { type: String, optional: true },
        onAvatarClick: { type: Function, optional: true },
        onDelete: { type: Function, optional: true },
        text: { type: String, optional: true },
        tooltip: { type: String, optional: true },
        type: { type: [String, { value: false }] }, // in sample data, the type is false
    };
}

const WithResourceFieldMixin = (T) => class ResourceFieldMixin extends T {
    setup() {
        super.setup(...arguments);
        if (this.relation == "resource.resource") {
            this.avatarCard = usePopover(AvatarCardResourcePopover);
        }
    }

    static components = {
        ...super.components,
        Many2XAutocomplete: AvatarResourceMany2XAutocomplete,
        Tag: ResourceTag,
    };
    static optionTemplate = "resource_mail.Many2ManyAvatarResourceField.option";

    displayAvatarCard(record) {
        return !this.env.isSmall && this.relation === "resource.resource" && record.data.resource_type === "user";
    }

    getTagProps(record) {
        return {
            ...super.getTagProps(...arguments),
            color: record.data.color,
            type: record.data.resource_type,
            imageUrl: record.data.resource_type === "user"
                ? `/web/image/${this.relation}/${record.resId}/avatar_128`
                : undefined,
        };
    }
};

const resourceFieldMixin = {
    relatedFields: (fieldInfo) => {
        return [
            ...many2ManyTagsAvatarUserField.relatedFields(fieldInfo),
            {
                name: "resource_type",
                type: "selection",
                selection: [
                    ["user", _t("Human")],
                    ["material", _t("Material")],
                ],
            },
            {
                name: "color",
                type: "integer",
            },
        ];
    },
};

export class Many2ManyAvatarResourceField extends WithResourceFieldMixin(Many2ManyTagsAvatarUserField) {}
export const many2ManyAvatarResourceField = {
    ...many2ManyTagsAvatarUserField,
    ...resourceFieldMixin,
    component: Many2ManyAvatarResourceField,
};
registry.category("fields").add("many2many_avatar_resource", many2ManyAvatarResourceField);

export class ListMany2ManyAvatarResourceField extends WithResourceFieldMixin(ListMany2ManyTagsAvatarUserField) {}
export const listMany2ManyAvatarResourceField = {
    ...listMany2ManyTagsAvatarUserField,
    ...resourceFieldMixin,
    component: ListMany2ManyAvatarResourceField,
};
registry.category("fields").add("list.many2many_avatar_resource", listMany2ManyAvatarResourceField);

export class KanbanMany2ManyAvatarResourceField extends WithResourceFieldMixin(KanbanMany2ManyTagsAvatarUserField) {
    get tags() {
        return super.tags.reverse();
    }
}
export const kanbanMany2ManyAvatarResourceField = {
    ...kanbanMany2ManyTagsAvatarUserField,
    ...resourceFieldMixin,
    component: KanbanMany2ManyAvatarResourceField,
};
registry.category("fields").add("kanban.many2many_avatar_resource", kanbanMany2ManyAvatarResourceField);
