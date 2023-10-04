/** @odoo-module **/

import { AttendeeCalendarCommonRenderer } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_renderer"
import { patch } from "@web/core/utils/patch";
import { renderToString } from "@web/core/utils/render";

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
            work = Object.values(this.props.model.worklocations)
                         .filter((wl) => wl.display)
                         .map((wl) => this.convertWorkRecordToEvent(wl));
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
        if (this.props.model.scale === 'week' || this.props.model.scale === 'day'){
            var ParseDate = (date) => date.getFullYear() + "-" +(date.getMonth() <10 ? "0" + (date.getMonth() + 1) : (date.getMonth()+1)) + "-" + (date.getDate() <10 ?"0" + date.getDate() : date.getDate());
            let button = info.view.context.calendar.el.querySelector(".fc-day-header[data-date='" + ParseDate(info.date) + "']  .o_month")
            let line = info.view.context.calendar.el.querySelector(".fc-day-header[data-date='" + ParseDate(info.date) + "']  .line")
            if (!button || !line)
                return;
            info.homework = true;
            button.onclick = () =>this.onDateClick(info)
            line.onclick = () =>this.onDateClick(info)
        }
        if (this.props.model.scale === 'month'){
            var ParseDate = (date) => date.getFullYear() + "-" +(date.getMonth() <10 ? "0" + (date.getMonth() + 1) : (date.getMonth()+1)) + "-" + (date.getDate() <10 ?"0" + date.getDate() : date.getDate());
            let box = info.view.el.querySelector(".fc-day-top[data-date='" + ParseDate(info.date) + "']")
            if (!box)
                return;
            const content = renderToString(this.constructor.ButtonWorklocationTemplate, {})
            const {children } = new DOMParser().parseFromString(content, "text/html").body
            box.appendChild(...children)
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
                const records = this.props.model.worklocations[info.event.start][icon].filter((rec) => rec.title === event.title);
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
                const record = this.props.model.worklocations[info.event.id];
                if (record) {
                    injectedContentStr = renderToString(this.constructor.WorklocationTemplate, {...record});
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
            const day_elem = elems.find((elem) => elem.classList.contains("fc-day","fc-widget-content"))
            const day_elem_date = day_elem.getAttribute("data-date")
            let wl;
            if (this.props.model.multiCalendar) {
                const elem = elems.find((elem) => elem.classList.contains("o_homework_content"))
                if (!elem){
                    return;
                }
                const id = parseInt(elem.getAttribute("data-id"));
                const icon = info.event.extendedProps.icon;
                const date = new Date(day_elem_date + " ")  // the empty string set's the time to 0
                wl = this.props.model.worklocations[date][icon].find((location) => location.id === id);
            } else {
                for (const location of Object.values(this.props.model.worklocations)) {
                    if (location.start.toISODate() === day_elem_date) {
                        wl = location;
                        continue;
                    }
                }
            }
            this.openPopover(info.el, wl);
            this.highlightEvent(info.event, "o_cw_custom_highlight");
        } else {
            super.onClick(...arguments);
        }
    },
    onDateClick(info){
        if (info.jsEvent && info.jsEvent.target.tagName ==="BUTTON") {
            info.homework = true
            this.props.createRecord(this.fcEventToRecord(info));
        } else {
            super.onDateClick(...arguments)
        }
    }
});

AttendeeCalendarCommonRenderer.WorklocationTemplate = "hr.homeworking.CalendarCommonRenderer.worklocation";
AttendeeCalendarCommonRenderer.ButtonWorklocationTemplate = "hr.homeworking.CalendarCommonRenderer.buttonWorklocation";
