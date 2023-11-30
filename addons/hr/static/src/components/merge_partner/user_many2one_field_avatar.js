// /* @odoo-module */

import { registry } from "@web/core/registry";
import { UserMany2OneField } from "./user_many2one_field";
import { Many2OneAvatarUserField } from "@mail/views/web/fields/many2one_avatar_user_field/many2one_avatar_user_field";

export class UserMany2OneAvatarField extends Many2OneAvatarUserField {
    static components = {
        ...Many2OneAvatarUserField.component,
        Many2OneField: UserMany2OneField
    }
}

registry.category("fields").add("merge_partner", {
    component: UserMany2OneAvatarField,
});
