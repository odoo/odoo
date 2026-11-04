import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";
import { onWillStart } from "@odoo/owl";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

export class TimeOffCalendarCommonPopover extends CalendarCommonPopover {
    static subTemplates = {
        ...CalendarCommonPopover.subTemplates,
        footer: "hr_holidays.TimeOffCalendarCommonPopover.footer",
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.viewType = "calendar";
        onWillStart(async () => {
            this.record = this.props.record.rawRecord;
            this.state = this.record.state;
            this.isManager = (await user.hasGroup("hr_holidays.group_hr_holidays_user")) || this.record.leave_manager_id?.[0] === user.userId;
        });
    }

    get isEventDeletable() {
        return this.props.record.rawRecord.can_cancel || this.state && !['validate', 'refuse', 'cancel'].includes(this.state);
    }

    get isEventEditable() {
        return this.state !== undefined;
    }

    get canCancel() {
        return this.record.can_cancel;
    }

    async onClickButton(ev) {
        const args = (ev.target.name === "action_approve") ? [this.record.id, false] : [this.record.id];
        await this.orm.call("hr.leave", ev.target.name, args);
        await this.props.model.load();
        this.props.close();
    }
}
