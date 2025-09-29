import { useAssignUserCommand } from "@mail/views/web/fields/assign_user_command_hook";

import { registry } from "@web/core/registry";
import { usePopover } from "@web/core/popover/popover_hook";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";
import {
    Many2ManyTagsAvatarField,
    many2ManyTagsAvatarField,
    ListMany2ManyTagsAvatarField,
    listMany2ManyTagsAvatarField,
    KanbanMany2ManyTagsAvatarField,
    kanbanMany2ManyTagsAvatarField,
} from "@web/views/fields/many2many_tags_avatar/many2many_tags_avatar_field";
import { Many2XAvatarUserAutocomplete } from "../avatar_autocomplete/avatar_many2x_autocomplete";

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
                onAvatarClick: (target) => {
                    if (!this.displayAvatarCard(record)) {
                        return;
                    }
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
    static template = "mail.Many2ManyTagsAvatarUserField";
    static components = {
        ...Many2ManyTagsAvatarField.components,
        Many2XAutocomplete: Many2XAvatarUserAutocomplete,
    };
}

export const many2ManyTagsAvatarUserField = {
    ...many2ManyTagsAvatarField,
    component: Many2ManyTagsAvatarUserField,
    additionalClasses: ["o_field_many2many_tags_avatar"],
};

registry.category("fields").add("many2many_avatar_user", many2ManyTagsAvatarUserField);

export class KanbanMany2ManyTagsAvatarUserField extends WithUserChatter(
    KanbanMany2ManyTagsAvatarField
) {
    static components = {
        ...KanbanMany2ManyTagsAvatarField.components,
    };
    get displayText() {
        return !this.props.readonly;
    }

    getTagProps(record) {
        const p = super.getTagProps(record);
        return {
            ...p,
            text: this.displayText ? p.text : "",
        };
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
        Many2XAutocomplete: Many2XAvatarUserAutocomplete,
    };

    get displayText() {
        return this.props.record.data[this.props.name].records.length === 1 || !this.props.readonly;
    }

    getTagProps(record) {
        const p = super.getTagProps(record);
        return {
            ...p,
            text: this.displayText ? p.text : "",
        };
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
