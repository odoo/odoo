/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";
import { useService } from "@web/core/utils/hooks";

export const patchAvatarCardPopover = {
    setup() {
        super.setup();
        this.userInfoTemplate = "hr.avatarCardUserInfos",
        this.actionService = useService("action");
    },
    get fieldNames(){
        let fields = super.fieldNames;
        return fields.concat([
            "work_phone",
            "work_email", 
            "job_title", 
            "department_id", 
            "employee_parent_id",
            "employee_ids",
        ])
    },
    get email(){
        return this.user.work_email || this.user.email;
    },
    get phone(){
        return this.user.work_phone || this.user.phone;
    },
    async onClickViewEmployee(){
        const employeeId = this.user.employee_ids[0];
        const action = await this.orm.call('hr.employee', 'get_formview_action', [employeeId]);
        this.actionService.doAction(action); 
    }
};

export const unpatchAvatarCardPopover = patch(AvatarCardPopover.prototype, patchAvatarCardPopover);
