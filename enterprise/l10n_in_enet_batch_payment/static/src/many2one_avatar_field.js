import { registry } from "@web/core/registry";
import { many2OneAvatarField } from "@web/views/fields/many2one_avatar/many2one_avatar_field";

export const formMany2OneAvatarField = {
    ...many2OneAvatarField,
    extractProps(fieldInfo, dynamicInfo) {
        const props = many2OneAvatarField.extractProps(...arguments);
        props.canOpen = false;
        return props;
    },
};

registry.category("fields").add("form.many2one_avatar", formMany2OneAvatarField);
