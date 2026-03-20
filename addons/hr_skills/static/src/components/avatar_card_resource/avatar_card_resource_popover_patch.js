import { patch } from "@web/core/utils/patch";
import { BadgeTag } from "@web/core/tags_list/badge_tag";
import { AvatarCardResourcePopover } from "@resource_mail/components/avatar_card_resource/avatar_card_resource_popover";

export const patchAvatarCardResourcePopover = {
    get hasFooter() {
        return this.employee?.employee_skill_ids?.length > 0 || super.hasFooter;
    },
    get skillTags() {
        return this.employee.employee_skill_ids.map(({ id, display_name, color }) => ({
            id,
            text: display_name,
            color,
        }));
    },
};

export const unpatchAvatarCardResourcePopover = patch(
    AvatarCardResourcePopover.prototype,
    patchAvatarCardResourcePopover
);
patch(AvatarCardResourcePopover, {
    components: {
        ...AvatarCardResourcePopover.components,
        SkillTag: BadgeTag,
    },
});
