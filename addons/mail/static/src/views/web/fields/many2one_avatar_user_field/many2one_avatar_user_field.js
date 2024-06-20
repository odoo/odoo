/* @odoo-module */

import { useAssignUserCommand } from "@mail/views/web/fields/assign_user_command_hook";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import {
    Many2OneAvatarField,
    many2OneAvatarField,
    KanbanMany2OneAvatarField,
    kanbanMany2OneAvatarField,
} from "@web/views/fields/many2one_avatar/many2one_avatar_field";
import { usePopover } from "@web/core/popover/popover_hook";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";

const WithUserChatter = (T) =>
    class extends T {
        setup() {
            super.setup(...arguments);
            if (this.props.withCommand) {
                useAssignUserCommand();
            }
            this.avatarCard = usePopover(AvatarCardPopover);
        }

        onClickAvatar(ev) {
            const id = this.props.record.data[this.props.name][0] ?? false;
            if (id !== false) {
                if (this.relation !== "res.users") {
                    return;
                }
                const target = ev.currentTarget;
                if (!this.avatarCard.isOpen) {
                    this.avatarCard.open(target, {
                        id: this.props.record.data[this.props.name][0],
                    });
                }
            }
        }
    };

export class Many2OneAvatarUserField extends WithUserChatter(Many2OneAvatarField) {
    static template = "mail.Many2OneAvatarUserField";
    static props = {
        ...Many2OneAvatarField.props,
        context: { type: String, optional: true },
        domain: { type: [Array, Function], optional: true },
        withCommand: { type: Boolean, optional: true },
    };
}

export const many2OneAvatarUserField = {
    ...many2OneAvatarField,
    component: Many2OneAvatarUserField,
    additionalClasses: ["o_field_many2one_avatar"],
    extractProps(fieldInfo, dynamicInfo) {
        const props = many2OneAvatarField.extractProps(...arguments);
        props.context = fieldInfo.context;
        props.domain = dynamicInfo.domain;
        props.withCommand = fieldInfo.viewType === "form" || fieldInfo.viewType === "list";
        return props;
    },
};

registry.category("fields").add("many2one_avatar_user", many2OneAvatarUserField);

export class KanbanMany2OneAvatarUserField extends WithUserChatter(KanbanMany2OneAvatarField) {
    static template = "mail.KanbanMany2OneAvatarUserField";
    static props = {
        ...KanbanMany2OneAvatarField.props,
        displayAvatarName: { type: Boolean, optional: true },
    };
    /**
     * All props are normally passed to the Many2OneField however since
     * we add a new one, we need to filter it out.
     */
    get popoverProps() {
        const props = super.popoverProps;
        delete props.displayAvatarName;
        return props;
    }
}

export const kanbanMany2OneAvatarUserField = {
    ...kanbanMany2OneAvatarField,
    component: KanbanMany2OneAvatarUserField,
    additionalClasses: [...kanbanMany2OneAvatarField.additionalClasses, "o_field_many2one_avatar"],
    supportedOptions: [
        ...(kanbanMany2OneAvatarField.supportedOptions || []),
        {
            label: _t("Display avatar name"),
            name: "display_avatar_name",
            type: "boolean",
        },
    ],
    extractProps({ options }) {
        const props = kanbanMany2OneAvatarField.extractProps(...arguments);
        props.displayAvatarName = options.display_avatar_name || false;
        return props;
    },
};

registry.category("fields").add("kanban.many2one_avatar_user", kanbanMany2OneAvatarUserField);
registry.category("fields").add("activity.many2one_avatar_user", kanbanMany2OneAvatarUserField);
