/** @odoo-module **/

import { registry } from "@web/core/registry";
import { usePopover } from "@web/core/popover/popover_hook";
import {
    Many2OneAvatarUserField,
    many2OneAvatarUserField,
} from "@mail/views/web/fields/many2one_avatar_user_field/many2one_avatar_user_field";
import { AvatarCardResourcePopover } from "@resource_mail/components/avatar_card_resource/avatar_card_resource_popover";
import { AvatarResourceMany2XAutocomplete } from "@resource_mail/views/fields/many2many_avatar_resource/many2many_avatar_resource_field";


const ExtendMany2OneAvatarToResource = (T) => class extends T {
    // We choose to extend Many2One_avatar_user instead of patching it as field dependencies need to be added on the widget to manage resources
    setup() {
        super.setup();
        this.avatarCard = usePopover(AvatarCardResourcePopover);
    }

    get displayAvatarCard() {
        return !this.env.isSmall && this.relation === "resource.resource" && this.props.record.data.resource_type === "user";
    }
};


export class Many2OneAvatarResourceField extends ExtendMany2OneAvatarToResource(Many2OneAvatarUserField) {
    static template = "resource_mail.Many2OneAvatarResourceField";
    static components = {
        ...super.components,
        Many2XAutocomplete: AvatarResourceMany2XAutocomplete,
    };
}

export const many2OneAvatarResourceField = {
    ...many2OneAvatarUserField,
    component: Many2OneAvatarResourceField,
    fieldDependencies: [
        {
            name: "resource_type", //to add in model that will use this widget for m2o field related to resource.resource record (as related field is only supported for x2m)
            type: "selection",
        },
    ],
};

registry.category("fields").add("many2one_avatar_resource", many2OneAvatarResourceField);

export class KanbanMany2OneAvatarResourceField extends ExtendMany2OneAvatarToResource(Many2OneAvatarResourceField) {
    static template = "resource_mail.KanbanMany2OneAvatarResourceField";
}

export const kanbanMany2OneAvatarResourceField = {
    ...many2OneAvatarResourceField,
    component: KanbanMany2OneAvatarResourceField,
};

registry.category("fields").add("kanban.many2one_avatar_resource", kanbanMany2OneAvatarResourceField);
