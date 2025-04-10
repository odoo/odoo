import { registry } from "@web/core/registry";
import { usePopover } from "@web/core/popover/popover_hook";
import { _t } from "@web/core/l10n/translation";
import {
    KanbanMany2ManyTagsAvatarUserField,
    ListMany2ManyTagsAvatarUserField,
    Many2ManyTagsAvatarUserField,
    Many2ManyAvatarUserTagsList,
    kanbanMany2ManyTagsAvatarUserField,
    listMany2ManyTagsAvatarUserField,
    many2ManyTagsAvatarUserField,
} from "@mail/views/web/fields/many2many_avatar_user_field/many2many_avatar_user_field";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { AvatarCardResourcePopover } from "@resource_mail/components/avatar_card_resource/avatar_card_resource_popover";
import { Domain } from "@web/core/domain";
import { KanbanMany2ManyTagsAvatarFieldTagsList } from "@web/views/fields/many2many_tags_avatar/many2many_tags_avatar_field";


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

class Many2ManyAvatarResourceTagsList extends Many2ManyAvatarUserTagsList {
    static template = "resource_mail.Many2ManyAvatarResourceTagsList";
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
        TagsList: Many2ManyAvatarResourceTagsList,
    };
    static optionTemplate = "resource_mail.Many2ManyAvatarResourceField.option";

    displayAvatarCard(record) {
        return !this.env.isSmall && this.relation === "resource.resource" && record.data.resource_type === "user";
    }

    getTagProps(record) {
        return {
            ...super.getTagProps(...arguments),
            icon: record.data.resource_type === "user" ? null : "fa-wrench",
            colorIndex: record.data.color,
            img: record.data.resource_type === "user"
                ? `/web/image/${this.relation}/${record.resId}/avatar_128`
                : null,
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

export class KanbanMany2ManyAvatarResourceTagsList extends Many2ManyAvatarResourceTagsList {
    static props = KanbanMany2ManyTagsAvatarFieldTagsList.props;
}
export class KanbanMany2ManyAvatarResourceField extends WithResourceFieldMixin(KanbanMany2ManyTagsAvatarUserField) {
    static components = {
        ...super.components,
        TagsList: KanbanMany2ManyAvatarResourceTagsList,
    };

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
