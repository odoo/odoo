/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2OneAvatarField } from "@web/views/fields/many2one_avatar/many2one_avatar_field";
import { useOpenChat } from "@mail/views/open_chat_hook";
import { useAssignUserCommand } from "@mail/views/fields/assign_user_command_hook";

export class Many2OneAvatarUserField extends Many2OneAvatarField {
    setup() {
        super.setup();
        this.openChat = useOpenChat(this.props.relation);
        useAssignUserCommand();
    }

    onClickAvatar() {
        this.openChat(this.props.value[0]);
    }
}
Many2OneAvatarUserField.template = "mail.Many2OneAvatarUserField";
Many2OneAvatarUserField.additionalClasses = ["o_field_many2one_avatar"];

registry.category("fields").add("many2one_avatar_user", Many2OneAvatarUserField);

export class KanbanMany2OneAvatarUserField extends Many2OneAvatarUserField {
    /**
     * All props are normally passed to the Many2OneField however since
     * we add a new one, we need to filter it out.
     */
    get m2oFieldProps() {
        return Object.fromEntries(Object.entries(this.props).filter(([key, _val]) => key in Many2OneAvatarField.props));
    }
}
KanbanMany2OneAvatarUserField.template = "mail.KanbanMany2OneAvatarUserField";
KanbanMany2OneAvatarUserField.props = {
    ...Many2OneAvatarUserField.props,
    displayAvatarName: { type: Boolean, optional: true },
};
KanbanMany2OneAvatarUserField.extractProps = ({ attrs, field }) => {
    return {
        ...Many2OneAvatarUserField.extractProps({ attrs, field }),
        displayAvatarName: attrs.options.display_avatar_name || false,
    };
};

registry.category("fields").add("kanban.many2one_avatar_user", KanbanMany2OneAvatarUserField);
registry.category("fields").add("activity.many2one_avatar_user", KanbanMany2OneAvatarUserField);
