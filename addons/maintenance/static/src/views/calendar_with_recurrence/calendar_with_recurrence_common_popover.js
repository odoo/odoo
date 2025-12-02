import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";

export class CalendarWithRecurrenceCommonPopover extends CalendarCommonPopover {
    onEditEvent() {
        this.props.record.id = this.props.record.rawRecord.id;
        super.onEditEvent();
    }
    onDeleteEvent() {
        this.props.record.id = this.props.record.rawRecord.id;
        super.onDeleteEvent();
    }
}
