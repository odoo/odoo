/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import {
    Many2OneAvatarResourceField,
    many2OneAvatarResourceField,
    KanbanMany2OneAvatarResourceField,
    kanbanMany2OneAvatarResourceField
} from "@resource_mail/views/fields/many2one_avatar_resource/many2one_avatar_resource_field";


export const patchM2oResourceFieldPrototype = {
    get displayAvatarCard() {
        return !this.env.isSmall && this.relation === "resource.resource" &&
            (this.props.record.data.resource_type == "user" || this.props.record.data.resource_roles?.records.length > 1);
    },
};

export const patchM2oResourceField = {
    fieldDependencies: [
        ...many2OneAvatarResourceField.fieldDependencies,
        {
            name: "resource_roles",
            type: "many2many"
        },
        {
            name: "resource_color",
            type: "integer"
        },
    ],
};

patch(Many2OneAvatarResourceField.prototype, patchM2oResourceFieldPrototype);
export const unpatchM2oResourceFieldPlanning = patch(many2OneAvatarResourceField, patchM2oResourceField);

patch(KanbanMany2OneAvatarResourceField.prototype, patchM2oResourceFieldPrototype);
export const unpatchKanbanM2oResourceFieldPlanning = patch(kanbanMany2OneAvatarResourceField, patchM2oResourceField);
