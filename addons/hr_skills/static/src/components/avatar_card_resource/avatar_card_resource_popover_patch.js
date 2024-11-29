import { patch } from "@web/core/utils/patch";
import { AvatarCardResourcePopover } from "@resource_mail/components/avatar_card_resource/avatar_card_resource_popover";

export const patchAvatarCardResourcePopoverSkills = {
    get fieldSpecification() {
        const fieldSpec = super.fieldSpecification;
        fieldSpec.employee_id.fields = {
            ...fieldSpec.employee_id.fields,
            employee_skill_ids: {
                fields: {
                    display_name: {},
                },
            },
        };
        return fieldSpec;
    },
    get skills() {
        return this.employee?.employee_skill_ids;
    },
    get skillTags() {
        return this.skills.map(({ id, display_name, color }) => ({
            id,
            text: display_name,
            colorIndex: color,
        }));
    },
};

export const unpatchAvatarCardResourcePopover = patch(
    AvatarCardResourcePopover.prototype,
    patchAvatarCardResourcePopoverSkills
);
