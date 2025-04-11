/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { onWillStart } from "@odoo/owl";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";
import { useService } from "@web/core/utils/hooks";

export const patchAvatarCardPopover = {
    setup() {
        super.setup();
        this.userInfoTemplate = "hr.avatarCardUserInfos";
        this.actionService = useService("action");
        onWillStart(async () => {
            await this.initialize();
            this.employees = await this.orm.read("hr.employee", this.user.employee_ids, [
                "department_id",
                "job_title",
            ]);
        });
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
    get jobTitle() {
        if (this.user.job_title || !this.employees) {
            return this.user.job_title;
        }
        for (const employee of this.employees) {
            if (employee.job_title) {
                return employee.job_title;
            }
        }
        return false;
    },
    get department() {
        if (this.user.department_id || !this.employees) {
            return this.user.department_id;
        }
        for (const employee of this.employees) {
            if (employee.department_id) {
                return employee.department_id;
            }
        }
        return false;
    },
    async onClickViewEmployee(){
        const employeeId = this.user.employee_ids[0];
        const action = await this.orm.call('hr.employee', 'get_formview_action', [employeeId]);
        this.actionService.doAction(action); 
    }
};

export const unpatchAvatarCardPopover = patch(AvatarCardPopover.prototype, patchAvatarCardPopover);
