import { AvatarCard } from "@mail/core/web/avatar_card/avatar_card";

import { BadgeTag } from "@web/core/tags_list/badge_tag";
import { TagsList } from "@web/core/tags_list/tags_list";
import { patch } from "@web/core/utils/patch";

Object.assign(AvatarCard.components, { BadgeTag, TagsList });

/** @type {AvatarCard} */
export const avatarCardPatch = {
    /** @override */
    get hasFooter() {
        return this.skillTags.length > 0 || super.hasFooter;
    },
    get skillTags() {
        return (
            this.employee?.employee_skill_ids.map(({ id, display_name, color }) => ({
                id,
                text: display_name,
                color,
            })) ?? []
        );
    },
};
export const unpatchAvatarCard = patch(AvatarCard.prototype, avatarCardPatch);
