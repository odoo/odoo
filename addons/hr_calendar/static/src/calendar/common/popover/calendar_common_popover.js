import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";
import { AttendeeCalendarCommonPopover } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_popover";
import { Field } from "@web/views/fields/field";

export const patchAttendeeCalendarCommonPopoverClass = {
    template: "hr_calendar.AttendeeCalendarCommonPopover",
    components: {
        ...AttendeeCalendarCommonPopover.components,
        Field,
    },
};

export const patchAttendeeCalendarCommonPopover = {
    setup() {
        this.fieldNames = ["work_location_id", "work_location_name", "work_location_type", "employee_id", "weekday", "weekly", "start_date", "employee_name"];
        super.setup(...arguments);
        this.values = {
            work_location_id: this.record?.work_location_id,
            work_location_name: this.record?.title,
            work_location_type: this.record?.icon,
            employee_id: this.record?.employeeId,
            weekday: false,
            weekly: false,
            date: this.record?.start,
            employee_name: this.record?.employeeName,
        };
        this.fields = {
            "work_location_id": { name: "Work Location", type: "many2one", relation: "hr.work.location" },
            "work_location_name": { name: "Work Location Name", type: "char" },
            "work_location_type": { name: "work location type", type: "selection" },
            "employee_id": { name: "employee id", type: "many2one", relation: "hr.employee" },
            "weekday": { name: "weekday", type: "integer" },
            "weekly": { name: "weekly", type: "boolean" },
            "date": { name: "date", type: "date" },
            "employee_name": { name: "employee name", type: "char" },
        };
    },
    isWorkLocationEvent() {
        return this.record?.resModel === "hr.employee.location";
    },
    get hasFooter() {
        return !this.isWorkLocationEvent() || this.record?.userId === user.userId;
    },
    isCurrentUserIsOwnerWorklocation() {
        return this.isWorkLocationEvent() && this.record?.userId === user.userId;
    },
    get isEventEditable() {
        return ("resModel" in (this.record || {})) || super.isEventEditable;
    },
    get isEventViewable() {
        return !("resModel" in (this.record || {})) || super.isEventViewable;
    },
    get displayAttendeeAnswerChoice() {
        return !("resModel" in (this.record || {})) && super.displayAttendeeAnswerChoice;
    },
    get isCurrentUserAttendee() {
        return !("resModel" in (this.record || {})) && super.isCurrentUserAttendee;
    },
};

export const unpatchAttendeeCalendarCommonPopoverClass = patch(AttendeeCalendarCommonPopover, patchAttendeeCalendarCommonPopoverClass);
export const unpatchAttendeeCalendarCommonPopover = patch(AttendeeCalendarCommonPopover.prototype, patchAttendeeCalendarCommonPopover);
