/** @odoo-module **/

import { registry } from "@web/core/registry";
import {
    Many2OneAvatarUserField,
    KanbanMany2OneAvatarUserField,
    many2OneAvatarUserField,
    kanbanMany2OneAvatarUserField,
} from "@mail/views/fields/many2one_avatar_user_field/many2one_avatar_user_field";

<<<<<<< HEAD
export class Many2OneAvatarEmployeeField extends Many2OneAvatarUserField { }
||||||| parent of f76b1ef7382 (temp)
export class Many2OneAvatarEmployeeField extends Many2OneAvatarUserField {}
=======
export class Many2OneAvatarEmployeeField extends Many2OneAvatarUserField {
    get relation() {
        return "hr.employee.public";
    }
}
>>>>>>> f76b1ef7382 (temp)

export const many2OneAvatarEmployeeField = {
    ...many2OneAvatarUserField,
    component: Many2OneAvatarEmployeeField,
    additionalClasses: [
        ...many2OneAvatarUserField.additionalClasses,
        "o_field_many2one_avatar_user",
    ],
    extractProps: (fieldInfo) => ({
        ...many2OneAvatarUserField.extractProps(fieldInfo),
        canQuickCreate: false,
        relation: fieldInfo.options?.relation,
    }),
};

registry.category("fields").add("many2one_avatar_employee", many2OneAvatarEmployeeField);

export class KanbanMany2OneAvatarEmployeeField extends KanbanMany2OneAvatarUserField { }

<<<<<<< HEAD
export const kanbanMany2OneAvatarEmployeeField = {
    ...kanbanMany2OneAvatarUserField,
    component: KanbanMany2OneAvatarEmployeeField,
    extractProps: (fieldInfo) => ({
        ...kanbanMany2OneAvatarUserField.extractProps(fieldInfo),
        relation: fieldInfo.options?.relation,
    })
||||||| parent of f76b1ef7382 (temp)
export class KanbanMany2OneAvatarEmployeeField extends KanbanMany2OneAvatarUserField {}
KanbanMany2OneAvatarEmployeeField.extractProps = ({ attrs, field }) => {
    return {
        ...KanbanMany2OneAvatarUserField.extractProps({ attrs, field }),
        relation: (attrs.options && attrs.options.relation) || field.relation,
    };
=======
export class KanbanMany2OneAvatarEmployeeField extends KanbanMany2OneAvatarUserField {
    get relation() {
        return "hr.employee.public";
    }
}
KanbanMany2OneAvatarEmployeeField.extractProps = ({ attrs, field }) => {
    return {
        ...KanbanMany2OneAvatarUserField.extractProps({ attrs, field }),
        relation: (attrs.options && attrs.options.relation) || field.relation,
    };
>>>>>>> f76b1ef7382 (temp)
};

registry
    .category("fields")
    .add("kanban.many2one_avatar_employee", kanbanMany2OneAvatarEmployeeField);
