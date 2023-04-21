/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2ManyTagsAvatarUserField, KanbanMany2ManyTagsAvatarUserField } from "@mail/views/fields/many2many_avatar_user_field/many2many_avatar_user_field";

export class Many2ManyTagsAvatarEmployeeField extends Many2ManyTagsAvatarUserField {
    get relation() {
        return "hr.employee.public";
    }
}
Many2ManyTagsAvatarEmployeeField.additionalClasses = [...Many2ManyTagsAvatarUserField.additionalClasses, "o_field_many2many_avatar_user"];

registry.category("fields").add("many2many_avatar_employee", Many2ManyTagsAvatarEmployeeField);

export class KanbanMany2ManyTagsAvatarEmployeeField extends KanbanMany2ManyTagsAvatarUserField {
    get relation() {
        return "hr.employee.public";
    }
}
KanbanMany2ManyTagsAvatarEmployeeField.additionalClasses = [...KanbanMany2ManyTagsAvatarUserField.additionalClasses, "o_field_many2many_avatar_user"];

registry.category("fields").add("kanban.many2many_avatar_employee", KanbanMany2ManyTagsAvatarEmployeeField);
registry.category("fields").add("list.many2many_avatar_employee", KanbanMany2ManyTagsAvatarEmployeeField);
