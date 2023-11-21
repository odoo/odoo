/** @odoo-module **/

import { AttendeeCalendarCommonRenderer } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_renderer";
import { AttendeeCalendarRenderer } from "@calendar/views/attendee_calendar/attendee_calendar_renderer";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";
import { renderToString } from "@web/core/utils/render";

const { DateTime } = luxon;

patch(AttendeeCalendarCommonRenderer.prototype, {
    get options(){
        return {
            ...super.options,
            eventOrder: function(event1, event2){
                if (event1.extendedProps.worklocation){
                    return -1;
                } else {
                    if(event2.extendedProps.worklocation){
                        return 1;
                    } else {
                        return event1.title.localeCompare(event2.title);
                    }
                }
            },
        };
    },
    handleWorkLocationClick(target, date) {
        let worklocations = this.props.model.worklocations[date.toISODate()];
        const worklocationSet = worklocations && Object.keys(worklocations).length > 0;
        const actionElement = target.closest('.wl_action');
        if (!actionElement) {
            return;
        }
        const { location, id, create } = actionElement.dataset;
        if (worklocationSet && !create) {
            if (!worklocations.id) {
                worklocations = worklocations[location] && worklocations[location].find(wl => wl.id == id);
            }
            if (worklocations) {
                return this.openPopover(target, worklocations);
            }
        }
        return this.props.openWorkLocationWizard(date);
    },
    onDayRender(info){
        const date = DateTime.fromJSDate(info.date);
        const parsedDate = date.toISODate();
        if (this.props.model.scale === 'week' || this.props.model.scale === 'day'){
            const header = info.view.context.calendar.el.querySelector(`.fc-day-header[data-date='${parsedDate}'] .o_worklocation_btn`);
            header.onclick = (e) => this.handleWorkLocationClick(e.target, date);
        }
        if (this.props.model.scale === 'month'){
            const box = info.view.el.querySelector(`.fc-day-top[data-date='${parsedDate}']`)
            if (!box)
                return;
            const content = renderToString(this.constructor.ButtonWorklocationTemplate, this.headerTemplateProps(info.date));
            box.insertAdjacentHTML("beforeend", content);
        }
        super.onDayRender(...arguments);
    },
    onDateClick(info){
        if (info.jsEvent && info.jsEvent.target.closest(".o_worklocation_btn")) {
            const date = DateTime.fromJSDate(info.date);
            this.handleWorkLocationClick(info.jsEvent.target, date);
        } else {
            super.onDateClick(...arguments)
        }
    },
    headerTemplateProps(date) {
        const parsedDate = DateTime.fromJSDate(date).toISODate();
        const multiCalendar = this.props.model.multiCalendar;
        const showLine = ["week", "month"].includes(this.props.model.scale);
        const worklocation = this.props.model.worklocations[parsedDate];
        const workLocationSetForCurrentUser = 
            multiCalendar ?
            Object.keys(worklocation).some(key => worklocation[key].some(wlItem => wlItem.userId === user.userId)
            ) : worklocation?.userId === user.userId;
        return {
            ...super.headerTemplateProps(date),
            worklocation,
            workLocationSetForCurrentUser,
            multiCalendar,
            showLine,
            iconMap: {
                "office": "fa-building",
                "home": "fa-home",
            },
        }
    }
});


AttendeeCalendarRenderer.props = {
    ...AttendeeCalendarRenderer.props,
    openWorkLocationWizard: { type: Function, optional: true },
}
AttendeeCalendarCommonRenderer.props = {
    ...AttendeeCalendarCommonRenderer.props,
    openWorkLocationWizard: { type: Function, optional: true }
};

AttendeeCalendarCommonRenderer.WorklocationTemplate = "hr.homeworking.CalendarCommonRenderer.worklocation";
AttendeeCalendarCommonRenderer.ButtonWorklocationTemplate = "hr.homeworking.CalendarCommonRenderer.buttonWorklocation";
AttendeeCalendarCommonRenderer.headerTemplate = "hr_homeworking.CalendarCommonRendererHeader";
