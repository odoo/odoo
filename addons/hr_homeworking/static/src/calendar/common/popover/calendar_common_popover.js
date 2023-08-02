/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { AttendeeCalendarCommonPopover } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_popover";
import { Field } from "@web/views/fields/field"

patch(AttendeeCalendarCommonPopover.prototype, {
    setup() {
        this.fieldNames = ["work_location_id", "work_location_name", "work_location_type", "employee_id", "weekday", "weekly", "start_date", "employee_name"];
        super.setup(...arguments)
    },
    isWorkLocationEvent(){
        return this.props.record.rawRecord['resModel'] === 'hr.employee.location';
    },
    get hasFooter() {
        return !this.isWorkLocationEvent() || this.props.record.userId === this.user.userId
    },
    isCurrentUserIsOwnerWorklocation(){
        return this.isWorkLocationEvent() && this.props.record.userId === this.slot.record.model.user.userId;
    },
    get isEventEditable() {
        return ('resModel' in this.props.record.rawRecord) || super.isEventEditable;
    },
    get isEventViewable() {
        return !('resModel' in this.props.record.rawRecord) || super.isEventViewable;
    },
    get isEventDeletable() {
        return ('resModel' in this.props.record.rawRecord) || super.isEventDeletable;
    },
    get displayAttendeeAnswerChoice() {
        return !('resModel' in this.props.record.rawRecord) && super.displayAttendeeAnswerChoice;
    },
    get isCurrentUserAttendee() {
        return !('resModel' in this.props.record.rawRecord) && super.isCurrentUserAttendee;
    }
})

AttendeeCalendarCommonPopover.template = "homework.AttendeeCalendarCommonPopover"


AttendeeCalendarCommonPopover.subTemplates = {
    ...AttendeeCalendarCommonPopover.subTemplates,
    body: "homework.AttendeeCalendarCommonPopover.body",
    footer: "homework.AttendeeCalendarCommonPopover.footer",
}

AttendeeCalendarCommonPopover.components = {
    ...AttendeeCalendarCommonPopover.components,
    Field
}
