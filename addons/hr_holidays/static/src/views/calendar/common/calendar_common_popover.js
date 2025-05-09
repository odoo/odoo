import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";
import { useService } from "@web/core/utils/hooks";

export class TimeOffCalendarCommonPopover extends CalendarCommonPopover {
    static subTemplates = {
        ...CalendarCommonPopover.subTemplates,
        popover: "hr_holidays.TimeOffCalendarCommonPopover.popover",
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.viewType = "calendar";
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
<<<<<<< bd89035263fb501651a822d184e13558e9b05d30
||||||| cd428bd75b63f96c67942be5457d0afdb00d29b0

    get isEventDeletable() {
        return this.props.record.rawRecord.can_cancel || this.state && !['validate', 'refuse', 'cancel'].includes(this.state);
    }

    get isEventEditable() {
        return this.state !== undefined;
    }

    async onClickButton(ev) {
        const args = (ev.target.name === "action_approve") ? [this.record.id, false] : [this.record.id];
        await this.orm.call("hr.leave", ev.target.name, args);
        await this.props.model.load();
        this.props.close();
    }
=======

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
>>>>>>> a74f4b95666d0d9f12074c8c40aeaae7b435f0a9
}
