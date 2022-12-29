/* @odoo-module */

import { registry } from "@web/core/registry";
import {
    Many2OneAvatarField,
    many2OneAvatarField,
    KanbanMany2OneAvatarField,
    kanbanMany2OneAvatarField,
} from "@web/views/fields/many2one_avatar/many2one_avatar_field";
import { useOpenChat } from "@mail/new/web/open_chat_hook";
import { useAssignUserCommand } from "@mail/new/web/fields/assign_user_command_hook";
import { patch } from "@web/core/utils/patch";

const userChatter = {
    setup() {
        this._super(...arguments);
        this.openChat = useOpenChat(this.relation);
        if (this.props.withCommand) {
            useAssignUserCommand();
        }
    },

    onClickAvatar() {
        this.openChat(this.props.record.data[this.props.name][0]);
    },
};

export class Many2OneAvatarUserField extends Many2OneAvatarField {
    static template = "mail.Many2OneAvatarUserField";
    static props = {
        ...Many2OneAvatarField.props,
        withCommand: { type: Boolean, optional: true },
    };
}
patch(Many2OneAvatarUserField.prototype, "mail", userChatter);

export const many2OneAvatarUserField = {
    ...many2OneAvatarField,
    component: Many2OneAvatarUserField,
    additionalClasses: ["o_field_many2one_avatar"],
    extractProps: (fieldInfo) => ({
        ...many2OneAvatarField.extractProps(fieldInfo),
        withCommand: fieldInfo.viewType === "form",
    }),
};

registry.category("fields").add("many2one_avatar_user", many2OneAvatarUserField);

export class KanbanMany2OneAvatarUserField extends KanbanMany2OneAvatarField {
    static template = "mail.KanbanMany2OneAvatarUserField";
    static props = {
        ...KanbanMany2OneAvatarField.props,
        displayAvatarName: { type: Boolean, optional: true },
    };
    /**
     * All props are normally passed to the Many2OneField however since
     * we add a new one, we need to filter it out.
     */
    get m2oFieldProps() {
        const props = {
            ...this.props,
        };
        delete props.displayAvatarName;
        return props;
    }

    get popoverProps() {
        return {
            ...this.m2oFieldProps,
            readonly: false,
        };
    }
}
patch(KanbanMany2OneAvatarUserField.prototype, "mail", userChatter);

export const kanbanMany2OneAvatarUserField = {
    ...kanbanMany2OneAvatarField,
    component: KanbanMany2OneAvatarUserField,
    additionalClasses: [...kanbanMany2OneAvatarField.additionalClasses, "o_field_many2one_avatar"],
    extractProps: (fieldInfo) => ({
        ...kanbanMany2OneAvatarField.extractProps(fieldInfo),
        displayAvatarName: fieldInfo.options.display_avatar_name || false,
    }),
};

registry.category("fields").add("kanban.many2one_avatar_user", kanbanMany2OneAvatarUserField);
registry.category("fields").add("activity.many2one_avatar_user", kanbanMany2OneAvatarUserField);
