/** @odoo-module **/

import { registry } from "@web/core/registry";
import {
    Many2OneAvatarUserField,
    KanbanMany2OneAvatarUserField,
    many2OneAvatarUserField,
    kanbanMany2OneAvatarUserField,
} from "@mail/views/web/fields/many2one_avatar_user_field/many2one_avatar_user_field";
import { EmployeeFieldRelationMixin } from "@hr/views/fields/employee_field_relation_mixin";

export class Many2OneAvatarEmployeeField extends EmployeeFieldRelationMixin(
    Many2OneAvatarUserField
) {
    get many2OneProps() {
        return {
            ...super.many2OneProps,
            relation: this.relation,
        };
    }
}

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

export class KanbanMany2OneAvatarEmployeeField extends EmployeeFieldRelationMixin(
    KanbanMany2OneAvatarUserField
) {
    get many2OneProps() {
        return {
            ...super.many2OneProps,
            relation: this.relation,
        };
    }
}

export const kanbanMany2OneAvatarEmployeeField = {
    ...kanbanMany2OneAvatarUserField,
    component: KanbanMany2OneAvatarEmployeeField,
    extractProps: (fieldInfo, dynamicInfo) => ({
        ...kanbanMany2OneAvatarUserField.extractProps(fieldInfo, dynamicInfo),
        relation: fieldInfo.options?.relation,
    }),
};

registry
    .category("fields")
    .add("kanban.many2one_avatar_employee", kanbanMany2OneAvatarEmployeeField);
