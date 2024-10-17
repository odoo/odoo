import { useService } from "@web/core/utils/hooks";
import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";

export class ActivityCalendarCommonPopover extends CalendarCommonPopover {
    static subTemplates = {
        ...CalendarCommonPopover.subTemplates,
        footer: "mail.ActivityCalendarCommonPopover.footer",
    };
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
    }

    async openRecord() {
        const action = await this.orm.call("mail.activity", "action_open_document", [
            this.props.record.rawRecord.id,
        ]);
        this.actionService.doAction(action);
    }
}
