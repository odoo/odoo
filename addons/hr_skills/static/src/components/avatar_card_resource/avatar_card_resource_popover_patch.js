/** @odoo-module native */
import { AvatarCardResourcePopover } from "@resource_mail/components/avatar_card_resource/avatar_card_resource_popover";
import { serializeDate } from "@web/core/l10n/dates";
import { luxon } from "@web/core/l10n/luxon";
import { patch } from "@web/core/utils/patch";

export const patchAvatarCardResourcePopover = {
    loadAdditionalData() {
        const promises = super.loadAdditionalData();
        this.skills = false;
        if (this.record.current_employee_skill_ids?.length) {
            promises.push(
                this.orm
                    .read("hr.employee.skill", this.record.current_employee_skill_ids, [
                        "display_name",
                        "color",
                        "valid_from",
                        "valid_to",
                    ])
                    .then((skills) => {
                        const today = serializeDate(luxon.DateTime.now());
                        this.skills = skills.filter(
                            (skill) =>
                                skill.valid_from <= today &&
                                (!skill.valid_to || skill.valid_to >= today),
                        );
                    }),
            );
        }
        return promises;
    },
    get fieldNames() {
        return [...super.fieldNames, "current_employee_skill_ids"];
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

export const unpatchAvatarCardResourcePopover = patch(
    AvatarCardResourcePopover.prototype,
    patchAvatarCardResourcePopover,
);
