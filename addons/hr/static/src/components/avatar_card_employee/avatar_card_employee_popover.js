/** @odoo-module **/

import { onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useOpenChat } from "@mail/core/web/open_chat_hook";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";

export class AvatarCardEmployeePopover extends AvatarCardPopover {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.openChat = useOpenChat("res.users");//KEEP ???
        onWillStart(async () => {
            [this.employee] = await this.orm.read("hr.employee", [this.props.id], this.employeeFieldNames);
            [this.user] = this.employee.user_id ? await this.orm.read("res.users", [this.employee.user_id[0]], this.userFieldNames) : [false];
        });
    }

    get employeeFieldNames() {
        return ["name", "user_id", "job_title", "department_id", "work_email", "show_hr_icon_display", "hr_icon_display"];
    }

    get userFieldNames() {
        return super.fieldNames;
    }

    get email(){
        return this.employee.work_email || this.user?.email;
    }

    get phone(){
        return this.employee.work_phone || this.user?.phone;
    }

    async onClickViewEmployee(){
        const action = await this.orm.call('hr.employee', 'get_formview_action', [this.props.id]);
        this.actionService.doAction(action); 
    }
}

AvatarCardEmployeePopover.template = "hr.AvatarCardEmployeePopover";
