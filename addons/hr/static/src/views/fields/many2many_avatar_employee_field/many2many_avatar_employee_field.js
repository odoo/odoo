/** @odoo-module **/

import { registry } from "@web/core/registry";
import {
    Many2ManyTagsAvatarUserField,
    KanbanMany2ManyTagsAvatarUserField,
    many2ManyTagsAvatarUserField,
    kanbanMany2ManyTagsAvatarUserField,
} from "@mail/new/web/fields/many2many_avatar_user_field/many2many_avatar_user_field";

export class Many2ManyTagsAvatarEmployeeField extends Many2ManyTagsAvatarUserField {}

export const many2ManyTagsAvatarEmployeeField = {
    ...many2ManyTagsAvatarUserField,
    component: Many2ManyTagsAvatarEmployeeField,
    additionalClasses: [
        ...many2ManyTagsAvatarUserField.additionalClasses,
        "o_field_many2many_avatar_user",
    ],
};

registry.category("fields").add("many2many_avatar_employee", many2ManyTagsAvatarEmployeeField);

export class KanbanMany2ManyTagsAvatarEmployeeField extends KanbanMany2ManyTagsAvatarUserField {}

export const kanbanMany2ManyTagsAvatarEmployeeField = {
    ...kanbanMany2ManyTagsAvatarUserField,
    component: KanbanMany2ManyTagsAvatarEmployeeField,
    additionalClasses: [
        ...kanbanMany2ManyTagsAvatarUserField.additionalClasses,
        "o_field_many2many_avatar_user",
    ],
};

registry
    .category("fields")
    .add("kanban.many2many_avatar_employee", kanbanMany2ManyTagsAvatarEmployeeField);
registry
    .category("fields")
    .add("list.many2many_avatar_employee", kanbanMany2ManyTagsAvatarEmployeeField);
