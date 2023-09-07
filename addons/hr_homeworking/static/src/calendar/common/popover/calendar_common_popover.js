/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { AttendeeCalendarCommonPopover } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_popover";
import { Field } from "@web/views/fields/field"
import { createRecordFields } from "@web/views/record";

patch(AttendeeCalendarCommonPopover.prototype, {
    setup() {
        const data = {
            work_location_id: { type: "many2one", relation: "hr.employee.location" },
            work_location_name: { type: "char" },
            work_location_type: { type: "selection" },
            employee_id: { type: "many2one", relation: "hr.employee" },
            employee_name: { type: "char" },
            weekday: { type: "integer" },
            weekly: { type: "boolean" },
            start_date: { type: "date" },
        };
        const { fields, activeFields } = createRecordFields(data);
        this.fields = fields;
        this._activeFields = activeFields;
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
