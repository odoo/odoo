import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import {
    Many2ManyTagsAvatarUserField,
    CardMany2ManyTagsAvatarUserField,
    ListMany2ManyTagsAvatarUserField,
    many2ManyTagsAvatarUserField,
    cardMany2ManyTagsAvatarUserField,
    listMany2ManyTagsAvatarUserField,
} from "@mail/views/web/fields/many2many_avatar_user_field/many2many_avatar_user_field";
import {
    many2ManyTagsAvatarFieldProps,
    cardMany2ManyTagsAvatarFieldProps,
    listMany2ManyTagsAvatarFieldProps,
} from "@web/views/fields/many2many_tags_avatar/many2many_tags_avatar_field";
import { EmployeeFieldRelationMixin } from "@hr/views/fields/employee_field_relation_mixin";

export class Many2ManyTagsAvatarEmployeeField extends EmployeeFieldRelationMixin(
    Many2ManyTagsAvatarUserField,
    many2ManyTagsAvatarFieldProps
) {
    displayAvatarCard(record) {
        return (
            (!this.env.isSmall && ["hr.employee", "hr.employee.public"].includes(this.relation)) ||
            super.displayAvatarCard(record)
        );
    }
}

export const many2ManyTagsAvatarEmployeeField = {
    ...many2ManyTagsAvatarUserField,
    component: Many2ManyTagsAvatarEmployeeField,
    additionalClasses: [
        ...many2ManyTagsAvatarUserField.additionalClasses,
        "o_field_many2many_avatar_user",
    ],
    extractProps: (fieldInfo, dynamicInfo) => ({
        ...many2ManyTagsAvatarUserField.extractProps(fieldInfo, dynamicInfo),
        canQuickCreate: false,
        relation: fieldInfo.options?.relation,
    }),
};

registry.category("fields").add("many2many_avatar_employee", many2ManyTagsAvatarEmployeeField);

export class CardMany2ManyTagsAvatarEmployeeField extends EmployeeFieldRelationMixin(
    CardMany2ManyTagsAvatarUserField,
    cardMany2ManyTagsAvatarFieldProps
) {
    displayAvatarCard(record) {
        return (
            (!this.env.isSmall && ["hr.employee", "hr.employee.public"].includes(this.relation)) ||
            super.displayAvatarCard(record)
        );
    }

    get placeholder() {
        return _t("Search employee...");
    }
}

export const cardMany2ManyTagsAvatarEmployeeField = {
    ...cardMany2ManyTagsAvatarUserField,
    component: CardMany2ManyTagsAvatarEmployeeField,
    additionalClasses: [
        ...cardMany2ManyTagsAvatarUserField.additionalClasses,
        "o_field_many2many_avatar_user",
    ],
    extractProps: (fieldInfo, dynamicInfo) => ({
        ...cardMany2ManyTagsAvatarUserField.extractProps(fieldInfo, dynamicInfo),
        relation: fieldInfo.options?.relation,
    }),
};

registry
    .category("fields")
    .add("card.many2many_avatar_employee", cardMany2ManyTagsAvatarEmployeeField)
    .add("activity.many2many_avatar_employee", cardMany2ManyTagsAvatarEmployeeField);

export class ListMany2ManyTagsAvatarEmployeeField extends EmployeeFieldRelationMixin(
    ListMany2ManyTagsAvatarUserField,
    listMany2ManyTagsAvatarFieldProps
) {
    displayAvatarCard(record) {
        return (
            (!this.env.isSmall && ["hr.employee", "hr.employee.public"].includes(this.relation)) ||
            super.displayAvatarCard(record)
        );
    }
}

export const listMany2ManyTagsAvatarEmployeeField = {
    ...listMany2ManyTagsAvatarUserField,
    component: ListMany2ManyTagsAvatarEmployeeField,
    additionalClasses: [
        ...listMany2ManyTagsAvatarUserField.additionalClasses,
        "o_field_many2many_avatar_user",
    ],
};
registry
    .category("fields")
    .add("list.many2many_avatar_employee", listMany2ManyTagsAvatarEmployeeField);
