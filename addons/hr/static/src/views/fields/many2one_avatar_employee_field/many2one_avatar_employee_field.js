/** @odoo-module **/

import { registry } from "@web/core/registry";
import {
    Many2OneAvatarUserField,
    KanbanMany2OneAvatarUserField,
    many2OneAvatarUserField,
    kanbanMany2OneAvatarUserField,
} from "@mail/web/fields/many2one_avatar_user_field/many2one_avatar_user_field";

export class Many2OneAvatarEmployeeField extends Many2OneAvatarUserField { }

export const many2OneAvatarEmployeeField = {
    ...many2OneAvatarUserField,
    component: Many2OneAvatarEmployeeField,
    additionalClasses: [
        ...many2OneAvatarUserField.additionalClasses,
        "o_field_many2one_avatar_user",
    ],
    extractProps: (fieldInfo, dynamicInfo) => ({
        ...many2OneAvatarUserField.extractProps(fieldInfo, dynamicInfo),
        canQuickCreate: false,
        relation: fieldInfo.options?.relation,
    }),
};

registry.category("fields").add("many2one_avatar_employee", many2OneAvatarEmployeeField);

export class KanbanMany2OneAvatarEmployeeField extends KanbanMany2OneAvatarUserField { }

export const kanbanMany2OneAvatarEmployeeField = {
    ...kanbanMany2OneAvatarUserField,
    component: KanbanMany2OneAvatarEmployeeField,
    extractProps: (fieldInfo, dynamicInfo) => ({
        ...kanbanMany2OneAvatarUserField.extractProps(fieldInfo, dynamicInfo),
        relation: fieldInfo.options?.relation,
    })
};

registry
    .category("fields")
    .add("kanban.many2one_avatar_employee", kanbanMany2OneAvatarEmployeeField);
