import { patch } from "@web/core/utils/patch";
import { AvatarCardResourcePopover } from "@resource_mail/components/avatar_card_resource/avatar_card_resource_popover";


export const patchAvatarCardResourcePopover = {
    loadAdditionalData() {
        const promises = super.loadAdditionalData();
        this.skills = false;
        if (this.record.employee_skill_ids?.length) {
            promises.push(
                this.orm
                    .read("hr.employee.skill", this.record.employee_skill_ids, ["display_name", "color"])
                    .then((skills) => {
                        this.skills = skills;
                    })
            );
        }
        return promises;
    },
    get fieldNames() {
        return [
            ...super.fieldNames,
            "employee_skill_ids",
        ];
    },
    get hasFooter() {
        return this.skills?.length > 0 || super.hasFooter;
    },
    get skillTags() {
        return this.skills.map(({ id, display_name, color }) => ({
            id,
            text: display_name,
            colorIndex: color,
        }));
    },
};

export const unpatchAvatarCardResourcePopover = patch(AvatarCardResourcePopover.prototype, patchAvatarCardResourcePopover);
