import { registry } from "@web/core/registry";
import {
    Many2ManyTagsAvatarEmployeeField,
    many2ManyTagsAvatarEmployeeField,
} from "@hr/views/fields/many2many_avatar_employee_field/many2many_avatar_employee_field";
import { Component } from "@odoo/owl";
import { AvatarTag } from "@web/core/tags_list/avatar_tag";

class EmployeeErrorTag extends Component {
    static template = "hr_work_entry.EmployeeErrorTag";
    static components = { AvatarTag };
    static props = ["imageUrl", "inError", "onAvatarClick", "onDelete", "text", "tooltip"];
}

export class Many2ManyTagsAvatarEmployeeErrorField extends Many2ManyTagsAvatarEmployeeField {
    static props = {
        ...Many2ManyTagsAvatarEmployeeField.props,
        inErrorField: { type: String, optional: true },
    };
    static components = {
        ...Many2ManyTagsAvatarEmployeeField.components,
        Tag: EmployeeErrorTag,
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
    .add("work_entry_many2many_avatar_employee", many2ManyTagsAvatarEmployeeErrorField);
