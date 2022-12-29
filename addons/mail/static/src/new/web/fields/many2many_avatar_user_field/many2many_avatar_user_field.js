/* @odoo-module */

import { registry } from "@web/core/registry";
import { TagsList } from "@web/views/fields/many2many_tags/tags_list";
import {
    Many2ManyTagsAvatarField,
    ListKanbanMany2ManyTagsAvatarField,
    many2ManyTagsAvatarField,
    listKanbanMany2ManyTagsAvatarField,
} from "@web/views/fields/many2many_tags_avatar/many2many_tags_avatar_field";
import { useOpenChat } from "@mail/new/web/open_chat_hook";
import { useAssignUserCommand } from "@mail/new/web/fields/assign_user_command_hook";

export class Many2ManyAvatarUserTagsList extends TagsList {}
Many2ManyAvatarUserTagsList.template = "mail.Many2ManyAvatarUserTagsList";

export class Many2ManyTagsAvatarUserField extends Many2ManyTagsAvatarField {
    setup() {
        super.setup();
        this.openChat = useOpenChat(this.relation);
        if (this.props.withCommand) {
            useAssignUserCommand();
        }
    }

    get tags() {
        return super.tags.map((tag) => ({
            ...tag,
            onImageClicked: () => {
                this.openChat(tag.resId);
            },
        }));
    }
}
Many2ManyTagsAvatarUserField.components = {
    ...Many2ManyTagsAvatarField.components,
    TagsList: Many2ManyAvatarUserTagsList,
};

export const many2ManyTagsAvatarUserField = {
    ...many2ManyTagsAvatarField,
    component: Many2ManyTagsAvatarUserField,
    additionalClasses: ["o_field_many2many_tags_avatar"],
};

registry.category("fields").add("many2many_avatar_user", many2ManyTagsAvatarUserField);

export class KanbanMany2ManyTagsAvatarUserField extends ListKanbanMany2ManyTagsAvatarField {
    static props = {
        ...ListKanbanMany2ManyTagsAvatarField.props,
        displayText: { type: Boolean, optional: true },
    };

    setup() {
        super.setup();
        this.openChat = useOpenChat(this.relation);
        if (this.props.withCommand) {
            useAssignUserCommand();
        }
    }

    get displayText() {
        return (
            (this.props.displayText && this.props.record.data[this.props.name].records.length === 1) ||
            !this.props.readonly
        );
    }

    get tags() {
        const recordFromId = (id) =>
            this.props.record.data[this.props.name].records.find((rec) => rec.id === id);
        return super.tags.map((tag) => ({
            ...tag,
            onImageClicked: () => {
                this.openChat(recordFromId(tag.id).resId);
            },
        }));
    }
}
KanbanMany2ManyTagsAvatarUserField.template = "mail.KanbanMany2ManyTagsAvatarUserField";
KanbanMany2ManyTagsAvatarUserField.components = {
    ...ListKanbanMany2ManyTagsAvatarField.components,
    TagsList: Many2ManyAvatarUserTagsList,
};

export const kanbanMany2ManyTagsAvatarUserField = {
    ...listKanbanMany2ManyTagsAvatarField,
    component: KanbanMany2ManyTagsAvatarUserField,
    additionalClasses: ["o_field_many2many_tags_avatar"],
    extractProps: (fieldInfo) => ({
        ...listKanbanMany2ManyTagsAvatarField.extractProps(fieldInfo),
        displayText: fieldInfo.viewType === "list",
    }),
};

registry.category("fields").add("kanban.many2many_avatar_user", kanbanMany2ManyTagsAvatarUserField);
registry.category("fields").add("list.many2many_avatar_user", kanbanMany2ManyTagsAvatarUserField);
registry
    .category("fields")
    .add("activity.many2many_avatar_user", kanbanMany2ManyTagsAvatarUserField);
