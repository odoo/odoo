/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2OneAvatarUserField, KanbanMany2OneAvatarUserField } from "@mail/views/fields/many2one_avatar_user_field/many2one_avatar_user_field";

export class Many2OneAvatarEmployeeField extends Many2OneAvatarUserField {}

Many2OneAvatarEmployeeField.extractProps = ({ field, attrs }) => {
    return {
        ...Many2OneAvatarUserField.extractProps({ field, attrs }),
        relation: (attrs.options && attrs.options.relation) || field.relation,
        canQuickCreate: false,
    }
};

Many2OneAvatarEmployeeField.additionalClasses = [...Many2OneAvatarUserField.additionalClasses, "o_field_many2one_avatar_user"];

registry.category("fields").add("many2one_avatar_employee", Many2OneAvatarEmployeeField);

export class KanbanMany2OneAvatarEmployeeField extends KanbanMany2OneAvatarUserField {}
KanbanMany2OneAvatarEmployeeField.extractProps = ({ attrs, field }) => {
    return {
        ...KanbanMany2OneAvatarUserField.extractProps({ attrs, field }),
        relation: (attrs.options && attrs.options.relation) || field.relation,
    };
};

registry.category("fields").add("kanban.many2one_avatar_employee", KanbanMany2OneAvatarEmployeeField);
