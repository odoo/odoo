import { registry } from "@web/core/registry";
import { ListMany2ManyTagsAvatarUserField, listMany2ManyTagsAvatarUserField } from "@mail/views/web/fields/many2many_avatar_user_field/many2many_avatar_user_field";

export class CustomMany2ManyUserField extends ListMany2ManyTagsAvatarUserField {
    getTagProps(record) {
        return {
            ...super.getTagProps(record),
            onDelete: this.props.readonly ? () => this.deleteTag(record.id) : undefined,
        };
    }
    get showM2OSelectionField() {
        return this.props.readonly;
    }
}

export const customMany2ManyUserField = {
    ...listMany2ManyTagsAvatarUserField, 
    component: CustomMany2ManyUserField,
};

registry.category("fields").add("custom_user_avatar_field", customMany2ManyUserField);
