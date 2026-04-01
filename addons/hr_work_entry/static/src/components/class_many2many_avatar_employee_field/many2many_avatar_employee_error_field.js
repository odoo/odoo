import { registry } from "@web/core/registry";
import {
    Many2ManyTagsAvatarEmployeeField,
    many2ManyTagsAvatarEmployeeField,
} from "@hr/views/fields/many2many_avatar_employee_field/many2many_avatar_employee_field";
import { Many2ManyAvatarUserTagsList } from "@mail/views/web/fields/many2many_avatar_user_field/many2many_avatar_user_field";

export class Many2ManyAvatarUserTagsListError extends Many2ManyAvatarUserTagsList {
    static template = "hr_work_entry.Many2ManyAvatarUserTagsListError";
}

export class Many2ManyTagsAvatarEmployeeErrorField extends Many2ManyTagsAvatarEmployeeField {
    static props = {
        ...Many2ManyTagsAvatarEmployeeField.props,
        inErrorField: { type: String, optional: true },
    };
    static components = {
        ...Many2ManyTagsAvatarEmployeeField.components,
        TagsList: Many2ManyAvatarUserTagsListError,
    };

    /**
     * @override
     */
    getTagProps(record) {
        return {
            ...super.getTagProps(record),
            inError: this.props.record.data[this.props.inErrorField].currentIds.includes(
                record.resId
            ),
        };
    }
}

export const many2ManyTagsAvatarEmployeeErrorField = {
    ...many2ManyTagsAvatarEmployeeField,
    component: Many2ManyTagsAvatarEmployeeErrorField,
    extractProps: (fieldInfo, dynamicInfo) => ({
        ...many2ManyTagsAvatarEmployeeField.extractProps(fieldInfo, dynamicInfo),
        inErrorField: fieldInfo.attrs.in_error,
    }),
};

registry
    .category("fields")
    .add("many2many_avatar_employee_class", many2ManyTagsAvatarEmployeeErrorField);
