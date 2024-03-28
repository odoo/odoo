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
        fields["partnerwithuser"] = [...fields["partnerwithuser"], ...additionalFields];
        return fields;
    },
    get email() {
        return this.user.work_email || this.user.email;
    },
    get phone() {
        return this.user.work_phone || this.user.phone;
    },
    async getProfileAction() {
        const { employee_ids } = this.user;
        const hasEmployees = employee_ids?.length > 0;
        const model = hasEmployees ? "hr.employee" : "res.partner";
        const kwargs = hasEmployees ? { chat_icon: true } : {};
        return hasEmployees
            ? this.orm.call(model, "get_formview_action", [employee_ids[0]], kwargs)
            : super.getProfileAction(...arguments);
    },
};

export const unpatchAvatarCardPopover = patch(AvatarCardPopover.prototype, patchAvatarCardPopover);
