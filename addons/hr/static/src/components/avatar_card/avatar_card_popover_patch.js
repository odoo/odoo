/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";
import { useService } from "@web/core/utils/hooks";

export const patchAvatarCardPopover = {
    setup() {
        super.setup();
        this.userInfoTemplate = "hr.avatarCardUserInfos";
        this.actionService = useService("action");
    },
    get fieldNames() {
        const fields = super.fieldNames;
        return fields.concat(["work_phone", "work_email", "job_title", "employee_id"]);
    },
    get fieldSpecification() {
        const fieldSpec = super.fieldSpecification;
        fieldSpec["department_id"] = {
            fields: {
                display_name: {},
            },
        };
        return fieldSpec;
    },
    get email() {
        return this.record.data.work_email || this.record.data.email;
    },
    get phone() {
        return this.record.data.work_phone || this.record.data.phone;
    },
    get employeeId() {
        return this.record.data.employee_id;
    },
    async onClickViewEmployee() {
        if (!this.employeeId) {
            return;
        }
        const action = await this.orm.call("hr.employee", "get_formview_action", [this.employeeId]);
        this.actionService.doAction(action);
    },
};

export const unpatchAvatarCardPopover = patch(AvatarCardPopover.prototype, patchAvatarCardPopover);
