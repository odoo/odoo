import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { plugin, providePlugins, useScope } from "@odoo/owl";
import { serializeDate } from "@web/core/l10n/dates";
import { usePopover } from "@web/core/popover/popover_hook";
import { ResourceCalendarAttendancePopoverLoader } from "@resource/plugins/resource_calendar_attendance_popover_loader";
import { ResourceCalendarPlugin } from "@resource/plugins/resource_calendar_plugin";

export class ResourceCalendarAttendanceCalendarCommonRenderer extends CalendarCommonRenderer {
    /**
     * @override
     */
    setup() {
        super.setup();
        providePlugins([ResourceCalendarAttendancePopoverLoader], {
            meta: this.props.model.meta,
            env: this.env,
        });
        this.resourceCalendarAttendancePopoverLoader = plugin(
            ResourceCalendarAttendancePopoverLoader
        );
        if (!useScope().pluginManager.getPluginById(ResourceCalendarPlugin.id)) {
            providePlugins([ResourceCalendarPlugin]);
        }
        this.resourceCalendarPlugin = plugin(ResourceCalendarPlugin);
        this.popover = usePopover(this.resourceCalendarAttendancePopoverLoader.component, {
            position: "right",
            onClose: () => {
                this.fc.api.unselect();
                this.popoverPromise.resolve();
            },
        });
    }

    /**
     * @override
     */
    get interactiveOptions() {
        return {
            ...super.interactiveOptions,
            selectable: this.props.model.canCreate,
            forceEventDuration: true,
        };
    }

    /**
     * @override
     */
    eventClassNames({ el, event }) {
        const classes = super.eventClassNames({ el, event });
        const pastEventClass = classes.indexOf("o_past_event");
        if (pastEventClass != -1 && luxon.DateTime.now() <= event.end) {
            classes.splice(pastEventClass, 1);
        }
        return classes;
    }

    /**
     * @override
     */
    onEventDragStart(info) {
        this.popover.close();
        if (info.event.allDay) {
            const hours = Math.floor(info.event.extendedProps.forcedDuration);
            const minutes = Math.round((info.event.extendedProps.forcedDuration - hours) * 60);
            info.view.calendar.setOption(
                "defaultTimedEventDuration",
                `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`
            );
        }
        super.onEventDragStart(...arguments);
    }

    /**
     * @override
     */
    onEventResizeStart(info) {
        this.popover.close();
        super.onEventResizeStart(...arguments);
    }

    /**
     * @override
     */
    onEventResize(info) {
        const record = this.props.model.records[info.event.id];
        if (record.rawRecord.recurrency) {
            this.fc.api.unselect();
            const dropTarget = document.elementFromPoint(
                info.jsEvent.clientX,
                info.jsEvent.clientY
            );
            dropTarget.fcSeg = info.el.fcSeg;
            record.startDelta = info.startDelta;
            record.endDelta = info.endDelta;
            this.openPopover(dropTarget, record);
            this.highlightEvent(info.event, "fc-event-mirror");
            this.popoverPromise.promise.then(() => {
                this.props.model.load();
            });
        } else {
            super.onEventResize(...arguments);
        }
    }

    /**
     * @override
     */
    async onEventDrop(info) {
        if (info.oldEvent.allDay) {
            info.view.calendar.setOption("defaultTimedEventDuration", "01:00");
        }
        const record = this.props.model.records[info.event.id];
        if (record.rawRecord.recurrency) {
            this.fc.api.unselect();
            const dropTarget = document.elementFromPoint(
                info.jsEvent.clientX,
                info.jsEvent.clientY
            );
            dropTarget.fcSeg = info.el.fcSeg;
            record.delta = info.delta;
            record.isAllDay = info.event.allDay;
            this.openPopover(dropTarget, record);
            this.highlightEvent(info.event, "fc-event-mirror");
            this.popoverPromise.promise.then(() => {
                this.props.model.load();
            });
        } else {
            super.onEventDrop(...arguments);
        }
    }

    /**
     * @override
     */
    async onSelect(info) {
        info.jsEvent?.preventDefault();
        this.popoverPromise = Promise.withResolvers();
        const start = luxon.DateTime.fromJSDate(info.start);
        const end = luxon.DateTime.fromJSDate(info.end);
        this.popover.open(
            info.jsEvent?.toElement ?? info.view.calendar.el.querySelector(".fc-event-mirror"),
            {
                ...this.getPopoverProps(null),
                context: {
                    ...this.props.model.meta.context,
                    default_date: serializeDate(start),
                    default_hour_from: start.hour + start.minute / 60,
                    default_hour_to: end.hour + end.minute / 60,
                },
            },
            `o_cw_popover card o_calendar_color_0`
        );
    }

    /**
     * @override
     */
    handleDateClick(info) {
        super.handleDateClick(info);
        if (this.props.model.hasMultiCreate) {
            this.onDateClick(info);
        }
    }

    /**
     * @override
     */
    onDateClick(info) {
        const date = luxon.DateTime.fromJSDate(info.date);
        info?.view?.calendar.select(date.toISO(), date.plus({ hours: 1 }).toISO());
    }

    /**
     * @override
     */
    mapRecordsToEvents() {
        const { records } = this.props.model.data;
        const events = [];
        Object.values(records).forEach((r) => {
            if (r.rawRecord.other_dates.length) {
                r.rawRecord.other_dates.forEach((date) => {
                    const temp_record = this.props.model.normalizeRecord({
                        ...r.rawRecord,
                        date: date,
                    });
                    events.push(this.convertRecordToEvent(temp_record));
                });
            }
            events.push(this.convertRecordToEvent(r));
        });
        return events;
    }

    /**
     * @override
     */
    convertRecordToEvent(record) {
        const res = super.convertRecordToEvent(...arguments);
        res.forcedDuration = record.duration;
        return res;
    }

    /**
     * @override
     */
    fcEventToRecord(event) {
        const { allDay, extendedProps } = event;
        const res = super.fcEventToRecord(...arguments);
        if (allDay) {
            res.isAllDay = allDay;
            res.end = res.start.plus({ hour: extendedProps.forcedDuration });
        }
        return res;
    }

    /**
     * @override
     */
    getPopoverProps(record) {
        return {
            onReload: async () => await this.props.model.load(),
            recordProps: this.resourceCalendarAttendancePopoverLoader.recordProps,
            archInfo: this.resourceCalendarAttendancePopoverLoader.archInfo,
            context: this.props.model.meta.context,
            resourceCalendarPlugin: this.resourceCalendarPlugin,
            startOcurrenceDateTime: record?.startOcurrenceDateTime,
            endOcurrenceDateTime: record?.endOcurrenceDateTime,
            originalRecord: record?.rawRecord,
            delta: record?.delta,
            startDelta: record?.startDelta,
            endDelta: record?.endDelta,
            isAllDay: record?.isAllDay,
        };
    }

    /**
     * @override
     */
    openPopover(target, record) {
        this.popoverPromise = Promise.withResolvers();
        const start = new luxon.DateTime.fromJSDate(target.fcSeg.eventRange.range.start);
        const end = new luxon.DateTime.fromJSDate(target.fcSeg.eventRange.range.end);
        record.startOcurrenceDateTime = start.set({
            hour: record.start.hour,
            minute: record.start.minute,
        });
        record.endOcurrenceDateTime = end.set({
            hour: record.end.hour,
            minute: record.end.minute,
        });
        return super.openPopover(...arguments);
    }
}
