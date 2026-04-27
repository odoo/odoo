/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import {
    Many2ManyAvatarResourceField,
    many2ManyAvatarResourceField,
} from "@resource_mail/views/fields/many2many_avatar_resource/many2many_avatar_resource_field";
import { many2ManyTagsAvatarUserField } from "@mail/views/web/fields/many2many_avatar_user_field/many2many_avatar_user_field";
import { _t } from "@web/core/l10n/translation";


export const patchM2mResourceFieldPrototype = {
    displayAvatarCard(record) {
        return !this.env.isSmall && this.relation === "resource.resource" &&
            (record.data.resource_type === "user" || record.data.role_ids.records.length > 1);
    },
};

export const patchM2mResourceField = {
    relatedFields: (fieldInfo) => {
        return [
            ...many2ManyTagsAvatarUserField.relatedFields(fieldInfo),
            {
                name: "resource_type",
                type: "selection",
                selection: [
                    ["user", _t("Human")],
                    ["material", _t("Material")],
                ],
            },
            {
                name: "role_ids",
                type: "many2many",
            },
        ];
    },
};

patch(Many2ManyAvatarResourceField.prototype, patchM2mResourceFieldPrototype);
patch(many2ManyAvatarResourceField, patchM2mResourceField);
