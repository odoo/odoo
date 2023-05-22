/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";
import { useService } from "@web/core/utils/hooks";

export const patchAvatarCardPopover = {
    setup() {
        this._super();
        this.userInfoTemplate = "hr.avatarCardUserInfos",
        this.actionService = useService("action");
    },
    get fieldNames(){
        let fields = this._super();
        return fields.concat([
            "work_phone", 
            "job_title", 
            "department_id", 
            "employee_parent_id",
            "employee_id",
        ])
    },
    async onClickViewEmployee(){
        const employeeId = this.user.employee_id[0];
        const action = await this.orm.call('hr.employee', 'get_formview_action', [employeeId]);
        this.actionService.doAction(action); 
    }
};

patch(AvatarCardPopover.prototype, "hr", patchAvatarCardPopover);
