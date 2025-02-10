import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";
import { onWillStart } from "@odoo/owl";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

export class TimeOffCalendarCommonPopover extends CalendarCommonPopover {
    static subTemplates = {
        ...CalendarCommonPopover.subTemplates,
        footer: "hr_holidays.TimeOffCalendarCommonPopover.footer",
        popover: "hr_holidays.TimeOffCalendarCommonPopover.popover",
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.viewType = "calendar";
        onWillStart(async () => {
            this.record = this.props.record.rawRecord;
            this.state = this.record.state;
            this.isManager = (await user.hasGroup("hr_holidays.group_hr_holidays_responsible")) || this.record.leave_manager_id?.[0] === user.userId;
        });
    }

    get isEventDeletable() {
        return this.isManager && this.state === 'confirm';
    }

    get isEventEditable() {
        return this.isManager && this.state;
    }

    get canBeApproved() {
        return this.isManager && ['confirm', 'refuse'].includes(this.state);
    }

    get canBeValidated() {
        return this.isManager && this.state === 'validate1';
    }

    get canBeRefused() {
        return this.isManager && this.state !== 'refuse';
    }

    onEditEvent() {
        this.props.close()
        this.actionService.doAction({
            name: this.record.display_name,
            type: "ir.actions.act_window",
            res_model: this.props.model.resModel,
            res_id: this.record.id,
            views: [[false, "form"]],
        });
    }

    async onClickApproveEvent(ev) {
        debugger
    }

    async onClickValidateEvent(ev) {
        debugger
    }

    async onClickRefuseEvent(ev) {
        debugger
    }
}
