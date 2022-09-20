/** @odoo-module **/

import { registry } from "@web/core/registry";
import { TagsList } from "@web/views/fields/many2many_tags/tags_list";
import {
    Many2ManyTagsAvatarField,
    ListKanbanMany2ManyTagsAvatarField,
} from "@web/views/fields/many2many_tags_avatar/many2many_tags_avatar_field";
import { useOpenChat } from "@mail/views/open_chat_hook";
import { useAssignUserCommand } from "@mail/views/fields/assign_user_command_hook";

export class Many2ManyAvatarUserTagsList extends TagsList {}
Many2ManyAvatarUserTagsList.template = "mail.Many2ManyAvatarUserTagsList";

export class Many2ManyTagsAvatarUserField extends Many2ManyTagsAvatarField {
    setup() {
        super.setup();
        this.openChat = useOpenChat(this.props.relation);
        useAssignUserCommand();
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
Many2ManyTagsAvatarUserField.additionalClasses = ["o_field_many2many_tags_avatar"];

registry.category("fields").add("many2many_avatar_user", Many2ManyTagsAvatarUserField);

export class KanbanMany2ManyTagsAvatarUserField extends ListKanbanMany2ManyTagsAvatarField {
    setup() {
        super.setup();
        this.openChat = useOpenChat(this.props.relation);
        useAssignUserCommand();
    }

    get displayText() {
        const isList = this.props.record.activeFields[this.props.name].viewType === "list";
        return (isList && this.props.value.records.length === 1) || !this.props.readonly;
    }

    get tags() {
        const recordFromId = (id) => this.props.value.records.find((rec) => rec.id === id);
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
KanbanMany2ManyTagsAvatarUserField.additionalClasses = ["o_field_many2many_tags_avatar"];

registry.category("fields").add("kanban.many2many_avatar_user", KanbanMany2ManyTagsAvatarUserField);
registry.category("fields").add("list.many2many_avatar_user", KanbanMany2ManyTagsAvatarUserField);
