import { many2OneAvatarUserField, Many2OneAvatarUserField } from "../../web/fields/many2one_avatar_user_field/many2one_avatar_user_field";
import { registry } from "@web/core/registry";


export class Many2OneAvatarUserNoNameField extends Many2OneAvatarUserField {
    static template = "mail.Many2OneAvatarUserNoNameField"
}


const fieldDescr = {
    ...many2OneAvatarUserField,
    component: Many2OneAvatarUserNoNameField,
};

registry.category("fields").add("many2one_avatar_user_noname", fieldDescr);
