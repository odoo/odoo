import { useAssignUserCommand } from "@mail/views/web/fields/assign_user_command_hook";

import { registry } from "@web/core/registry";
import { TagsList } from "@web/core/tags_list/tags_list";
import { usePopover } from "@web/core/popover/popover_hook";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";
import {
    Many2ManyTagsAvatarField,
    many2ManyTagsAvatarField,
    ListMany2ManyTagsAvatarField,
    listMany2ManyTagsAvatarField,
    KanbanMany2ManyTagsAvatarField,
    kanbanMany2ManyTagsAvatarField,
    KanbanMany2ManyTagsAvatarFieldTagsList,
} from "@web/views/fields/many2many_tags_avatar/many2many_tags_avatar_field";

export class Many2ManyAvatarUserTagsList extends TagsList {
    static template = "mail.Many2ManyAvatarUserTagsList";
}

const WithUserChatter = (T) =>
    class UserChatterMixin extends T {
        setup() {
            super.setup(...arguments);
            if (this.props.withCommand) {
                useAssignUserCommand();
            }
            this.avatarCard = usePopover(AvatarCardPopover);
        }

        displayAvatarCard(record) {
            return ["res.users", "res.partner"].includes(this.relation);
        }

        getAvatarCardProps(record) {
            return {
                id: record.resId,
                model: this.relation,
            };
        }

        getTagProps(record) {
            return {
                ...super.getTagProps(...arguments),
                onImageClicked: (ev) => {
                    if (!this.displayAvatarCard(record)) {
                        return;
                    }
                    const target = ev.currentTarget;
                    if (
                        !this.avatarCard.isOpen ||
                        (this.lastOpenedId && record.resId !== this.lastOpenedId)
                    ) {
                        this.avatarCard.open(target, this.getAvatarCardProps(record));
                        this.lastOpenedId = record.resId;
                    }
                },
            };
        }
    };

export class Many2ManyTagsAvatarUserField extends WithUserChatter(Many2ManyTagsAvatarField) {
    static components = {
        ...Many2ManyTagsAvatarField.components,
        TagsList: Many2ManyAvatarUserTagsList,
    };
}

export const many2ManyTagsAvatarUserField = {
    ...many2ManyTagsAvatarField,
    component: Many2ManyTagsAvatarUserField,
    additionalClasses: ["o_field_many2many_tags_avatar"],
};

registry.category("fields").add("many2many_avatar_user", many2ManyTagsAvatarUserField);

export class KanbanMany2ManyAvatarUserTagsList extends KanbanMany2ManyTagsAvatarFieldTagsList {
    static template = "mail.KanbanMany2ManyAvatarUserTagsList";
}

export class KanbanMany2ManyTagsAvatarUserField extends WithUserChatter(
    KanbanMany2ManyTagsAvatarField
) {
    static template = "mail.KanbanMany2ManyTagsAvatarUserField";
    static components = {
        ...KanbanMany2ManyTagsAvatarField.components,
        TagsList: KanbanMany2ManyAvatarUserTagsList,
    };
    get displayText() {
        return !this.props.readonly;
    }
}
export const kanbanMany2ManyTagsAvatarUserField = {
    ...kanbanMany2ManyTagsAvatarField,
    component: KanbanMany2ManyTagsAvatarUserField,
    additionalClasses: ["o_field_many2many_tags_avatar", "o_field_many2many_tags_avatar_kanban"],
};
registry.category("fields").add("kanban.many2many_avatar_user", kanbanMany2ManyTagsAvatarUserField);

export class ListMany2ManyTagsAvatarUserField extends WithUserChatter(
    ListMany2ManyTagsAvatarField
) {
    static template = "mail.ListMany2ManyTagsAvatarUserField";
    static components = {
        ...ListMany2ManyTagsAvatarField.components,
        TagsList: Many2ManyAvatarUserTagsList,
    };

    get displayText() {
        return this.props.record.data[this.props.name].records.length === 1 || !this.props.readonly;
    }
}

export const listMany2ManyTagsAvatarUserField = {
    ...listMany2ManyTagsAvatarField,
    component: ListMany2ManyTagsAvatarUserField,
    listViewWidth: [120],
    additionalClasses: ["o_field_many2many_tags_avatar", "o_field_many2many_tags_avatar_list"],
};

registry.category("fields").add("list.many2many_avatar_user", listMany2ManyTagsAvatarUserField);
registry
    .category("fields")
    .add("activity.many2many_avatar_user", kanbanMany2ManyTagsAvatarUserField);
