/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { AvatarCardResourcePopover } from "@resource_mail/components/avatar_card_resource/avatar_card_resource_popover";
import { TagsList } from "@web/core/tags_list/tags_list";

export const patchAvatarCardResourcePopover = {
    get fieldSpecification() {
        const fieldSpec = super.fieldSpecification;
        fieldSpec.employee_id = {
            fields: {
                ...fieldSpec.user_id.fields.employee_id.fields,
                show_hr_icon_display: {},
                hr_icon_display: {},
            },
        };
        delete fieldSpec.user_id.fields.employee_id;
        return fieldSpec;
    },
    get displayAvatar() {
        return this.employee && this.props.recordModel && this.props.id;
    },
    get employee() {
        return super.employee?.[0];
    },
};

export const unpatchAvatarCardResourcePopover = patch(
    AvatarCardResourcePopover.prototype,
    patchAvatarCardResourcePopover
);

// Adding TagsList component allows display tag lists on the resource/employee avatar card
// This is used by multiple modules depending on hr (planning for roles and hr_skills for skills)
AvatarCardResourcePopover.components = {
    ...AvatarCardResourcePopover.components,
    TagsList,
};

AvatarCardResourcePopover.template = "hr.AvatarCardResourcePopover";
