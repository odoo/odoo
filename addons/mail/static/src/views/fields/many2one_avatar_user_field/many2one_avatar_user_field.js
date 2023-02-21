/** @odoo-module **/

import { registry } from "@web/core/registry";
import {
    Many2OneAvatarField,
    many2OneAvatarField,
} from "@web/views/fields/many2one_avatar/many2one_avatar_field";
import { useOpenChat } from "@mail/views/open_chat_hook";
import { useAssignUserCommand } from "@mail/views/fields/assign_user_command_hook";

export class Many2OneAvatarUserField extends Many2OneAvatarField {
    setup() {
        super.setup();
        const relation = this.props.record.fields[this.props.name].relation;
        this.openChat = useOpenChat(relation);
        useAssignUserCommand();
    }

    onClickAvatar() {
        this.openChat(this.props.value[0]);
    }
}
Many2OneAvatarUserField.template = "mail.Many2OneAvatarUserField";

export const many2OneAvatarUserField = {
    ...many2OneAvatarField,
    component: Many2OneAvatarUserField,
    additionalClasses: ["o_field_many2one_avatar"],
};

registry.category("fields").add("many2one_avatar_user", many2OneAvatarUserField);

export class KanbanMany2OneAvatarUserField extends Many2OneAvatarUserField {
    /**
     * All props are normally passed to the Many2OneField however since
     * we add a new one, we need to filter it out.
     */
    get m2oFieldProps() {
        return Object.fromEntries(
            Object.entries(this.props).filter(([key, _val]) => key in Many2OneAvatarField.props)
        );
    }
}
KanbanMany2OneAvatarUserField.template = "mail.KanbanMany2OneAvatarUserField";
KanbanMany2OneAvatarUserField.props = {
    ...Many2OneAvatarUserField.props,
    displayAvatarName: { type: Boolean, optional: true },
};

export const kanbanMany2OneAvatarUserField = {
    ...many2OneAvatarUserField,
    component: KanbanMany2OneAvatarUserField,
    extractProps: (params) => ({
        ...many2OneAvatarUserField.extractProps(params),
        displayAvatarName: params.attrs.options.display_avatar_name || false,
    }),
};

registry.category("fields").add("kanban.many2one_avatar_user", kanbanMany2OneAvatarUserField);
registry.category("fields").add("activity.many2one_avatar_user", kanbanMany2OneAvatarUserField);
