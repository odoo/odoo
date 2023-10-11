/** @odoo-module **/

import { onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useOpenChat } from "@mail/core/web/open_chat_hook";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";

export class AvatarCardEmployeePopover extends AvatarCardPopover {
    setup() {
        this.userInfoTemplate = "hr.avatarCardEmployeeInfos",
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.openChat = useOpenChat(this.props.recordModel);
        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        [this.record] = await this.orm.read(this.props.recordModel, [this.props.id], this.fieldNames);
    }

    get fieldNames() {
        const excludedFields = ["employee_parent_id", "employee_id"]
        const fields = [
            ...super.fieldNames,
            "user_id",            
            "show_hr_icon_display",
            "hr_icon_display",
        ].filter((field) => !excludedFields.includes(field));
        return fields;
    }

    get email(){
        return this.record.work_email || this.record.email;
    }

    get phone(){
        return this.record.work_phone || this.record.phone;
    }

    async onClickViewEmployee(){
        const action = await this.orm.call('hr.employee', 'get_formview_action', [this.props.id]);//TODO: Open with user ID ????? (allow to not override in resource popover)
        this.actionService.doAction(action); 
    }

    onSendClick() {
        this.openChat(this.record.id);
    }
}

AvatarCardEmployeePopover.template = "hr.AvatarCardEmployeePopover";
AvatarCardEmployeePopover.props = {
    ...AvatarCardPopover.props,
    recordModel: {
        type: String,
        optional: true,
    },
};
AvatarCardEmployeePopover.defaultProps = {
    ...AvatarCardPopover.defaultProps,
    recordModel: "hr.employee",
};
