import { patch } from "@web/core/utils/patch";
import { AvatarCardResourcePopover } from "@resource_mail/components/avatar_card_resource/avatar_card_resource_popover";
import { TagsList } from "@web/core/tags_list/tags_list";

const patchAvatarCardResourcePopover = {
    get employee() {
        return this.resource?.employee_id;
    },
    get showViewProfileBtn() {
        return this.employee;
    },
};

patch(AvatarCardResourcePopover.prototype, patchAvatarCardResourcePopover);
// Adding TagsList component allows display tag lists on the resource/employee avatar card
// This is used by multiple modules depending on hr (planning for roles and hr_skills for skills)
patch(AvatarCardResourcePopover, {
    components: {
        ...AvatarCardResourcePopover.components,
        TagsList,
    },
});
