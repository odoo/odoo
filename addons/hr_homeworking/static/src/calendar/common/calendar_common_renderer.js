/** @odoo-module **/

import { AttendeeCalendarCommonRenderer } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_renderer";
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
    fcEventToRecord(event) {
        const res = super.fcEventToRecord(...arguments);
        res.homework = event.homework;
        return res;
    },
    filterWorkRecord(arr, modelUserId){
        let events = []
        if (arr.length === 1){
            events.push(this.convertWorkRecordToEvent(arr[0]))
            return events;
        }
        // sort ASC by title location. If it's equals put the event of the current user at first
        arr.sort((a,b)=> (a.title > b.title) ? 1 : (a.title < b.title) ? -1 : a.userId === modelUserId ? -1 : b.userId === modelUserId ? 1 : 0)
        let previous_title = "";
        for (const event of arr) {
            if (previous_title !== event.title) {
                events.push(this.convertWorkRecordToEvent(event))
                previous_title = event.title
            }
        }
        return events;
    },
    mapRecordsToEvents() {
        let event = super.mapRecordsToEvents(...arguments);
        let work = [];
        if (this.props.model.multiCalendar) {
            for (const day in this.props.model.worklocations) {
                let events = [];
                const home = this.props.model.worklocations[day].home;
                const office = this.props.model.worklocations[day].office;
                const other = this.props.model.worklocations[day].other;
                const modelUserId = this.env.searchModel.userService.userId;
                if (home && home.length > 0) {
                    events = events.concat(this.filterWorkRecord(home,modelUserId))
                }
                if (office && office.length > 0) {
                    events = events.concat(this.filterWorkRecord(office,modelUserId))
                }
                if (other && other.length > 0) {
                    events = events.concat(this.filterWorkRecord(other,modelUserId))
                }
                work.push(...events);
            }
        } else {
            work = Object.values(this.props.model.worklocations).reduce((wls, wl) => {
                if (wl.display) {
                    wls.push(this.convertWorkRecordToEvent(wl));
                }
                return wls;
            }, []);
        }
        return event.concat(work);
    },
    convertWorkRecordToEvent(record) {
        return {
            id: record.id,
            title: record.title,
            start: record.start.toISO(),
            end: record.end.plus({ days: 1}).toISO(),
            allDay: record.isAllDay,
            icon: record.icon,
            colorIndex: record.colorIndex,
            worklocation: true,
            // to avoid to drag location event
            editable: false,
        };
    },
    onDayRender(info){
        const parsedDate = DateTime.fromJSDate(info.date).toISODate();
        if (this.props.model.scale === 'week' || this.props.model.scale === 'day'){
            const button = info.view.context.calendar.el.querySelector(`.fc-day-header[data-date='${parsedDate}'] .o_worklocation_text`)
            const line = info.view.context.calendar.el.querySelector(`.fc-day-header[data-date='${parsedDate}'] .o_worklocation_line`)
            if (!button || !line)
                return;
            info.homework = true;
            button.onclick = () =>this.onDateClick(info)
            line.onclick = () =>this.onDateClick(info)
        }
        if (this.props.model.scale === 'month'){
            const box = info.view.el.querySelector(`.fc-day-top[data-date='${parsedDate}']`)
            if (!box)
                return;
            const content = renderToString(this.constructor.ButtonWorklocationTemplate, {})
            const {children } = new DOMParser().parseFromString(content, "text/html").body
            box.appendChild(...children);
            info.homework = true;
        }
        super.onDayRender(...arguments);
    },
    onEventRender(info) {
        const { el, event } = info;
        if (event.extendedProps.worklocation) {
            el.classList.add("o_homework_event");
            const multiCalendar = this.props.model.multiCalendar;
            let injectedContentStr = "";
            const icon = event.extendedProps.icon;
            if (multiCalendar) {
                const parsedDate = DateTime.fromJSDate(info.event.start).toISODate()
                const records = this.props.model.worklocations[parsedDate][icon].filter((rec) => rec.title === event.title);
                let iconStr;
                if (icon === "home") {
                    iconStr = "fa-home";
                }
                else if (icon === "office") {
                    iconStr = "fa-building";
                }
                else {
                    iconStr = "fa-map-marker";
                }
                if (records) {
                    const obj = {records: records, iconStr: iconStr, multiCalendar: multiCalendar};
                    injectedContentStr = renderToString(this.constructor.WorklocationTemplate, obj);
                }
            } else {
                const record = this.props.model.worklocations[DateTime.fromJSDate(info.event.start).toISODate()];
                if (record) {
                    injectedContentStr = renderToString(this.constructor.WorklocationTemplate, record);
                }
            }
            const domParser = new DOMParser();
            const { children } = domParser.parseFromString(injectedContentStr, "text/html").body;
            el.querySelector(".fc-content").replaceWith(...children);
        } else {
            super.onEventRender(...arguments);
        }
    },
    onDblClick(info) {
        if (info.event.extendedProps.worklocation) {
            this.onClick(info);
        } else {
            super.onDblClick(...arguments);
        }
    },
    onClick(info){
        if (info.event.extendedProps.worklocation){
            const elems = document.elementsFromPoint(info.jsEvent.x, info.jsEvent.y)
            const dayElement = elems.find((elem) => elem.classList.contains("fc-day","fc-widget-content"))
            const dayFromElement = dayElement.getAttribute("data-date")
            let workLocation;
            if (this.props.model.multiCalendar) {
                const elem = elems.find((elem) => elem.classList.contains("o_homework_content"))
                if (!elem){
                    return;
                }
                const id = elem.getAttribute("data-id");
                const icon = info.event.extendedProps.icon;
                workLocation = this.props.model.worklocations[dayFromElement][icon].find((wl) => wl.id === id);
            } else {
                workLocation = Object.values(this.props.model.worklocations).find(wl => wl.start.toISODate() === dayFromElement);
            }
            this.openPopover(info.el, workLocation);
            this.highlightEvent(info.event, "o_cw_custom_highlight");
        } else {
            super.onClick(...arguments);
        }
    },
    onDateClick(info){
        if (info.jsEvent && info.jsEvent.target.closest(".o_worklocation_btn")) {
            info.homework = true
            this.props.createRecord(this.fcEventToRecord(info));
        } else {
            super.onDateClick(...arguments)
        }
    }
});

AttendeeCalendarCommonRenderer.WorklocationTemplate = "hr.homeworking.CalendarCommonRenderer.worklocation";
AttendeeCalendarCommonRenderer.ButtonWorklocationTemplate = "hr.homeworking.CalendarCommonRenderer.buttonWorklocation";
AttendeeCalendarCommonRenderer.headerTemplate = "hr_homeworking.CalendarCommonRendererHeader";
