import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";

export class WorkEntryCalendarCommonPopover extends CalendarCommonPopover {
    static subTemplates = {
        ...CalendarCommonPopover.subTemplates,
        footer: "hr_work_entry.WorkEntryCalendarCommonPopover.footer",
    };
    static props = {
        ...CalendarCommonPopover.props,
        splitRecord: Function,
    };

    get isWorkEntryValidated() {
        return this.props.record.rawRecord.state === "validated";
    }

    get isSplittable() {
        return this.props.record.rawRecord.duration >= 1;
    }

    /**
     * @override
     */
    get isEventEditable() {
        return !this.isWorkEntryValidated && super.isEventEditable;
    }

    /**
     * @override
     */
    get isEventDeletable() {
        return !this.isWorkEntryValidated && super.isEventDeletable;
    }

    /**
     * @override
     */
    get isEventViewable() {
        return !this.isWorkEntryValidated && super.isEventViewable;
    }

    /**
     * @override
     */
    get hasFooter() {
        return this.isWorkEntryValidated || super.hasFooter;
    }

    onSplitEvent() {
        this.props.splitRecord(this.props.record);
        this.props.close();
    }
}
