/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";

export const patchAvatarCardPopover = {
    setup() {
        super.setup();
        this.userInfoTemplate = "hr.avatarCardUserInfos";
    },
    get fieldNames() {
        const fields = super.fieldNames;
        const additionalFields = [
            "work_phone",
            "work_email",
            "work_location_name",
            "work_location_type",
            "job_title",
            "department_id",
            this.props.recordModel ? "employee_id" : "employee_ids",
        ];
        fields["users"] = [...fields["users"], ...additionalFields];
        return fields;
    },
    get email() {
        return this.avatarEntity.work_email || this.avatarEntity.email;
    },
    get phone() {
        return this.avatarEntity.work_phone || this.avatarEntity.phone;
    },
    async getProfileAction() {
        const { employee_ids } = this.avatarEntity;
        if (employee_ids?.length > 0) {
            return this.orm.call("hr.employee", "get_formview_action", [employee_ids[0]], {
                chat_icon: true,
            });
        }
        return super.getProfileAction(...arguments);
    },
};

export const unpatchAvatarCardPopover = patch(AvatarCardPopover.prototype, patchAvatarCardPopover);
