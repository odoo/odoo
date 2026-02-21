import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { useService } from "@web/core/utils/hooks";
import { ResourceCalendarAttendancePopover } from "../../components/resource_calendar_attendance_popover/resource_calendar_attendance_popover";
import { serializeDate } from "@web/core/l10n/dates";
import { usePopover } from "@web/core/popover/popover_hook";

export class ResourceCalendarAttendanceCalendarCommonRenderer extends CalendarCommonRenderer {
    static components = {
        ...CalendarCommonRenderer,
    };

    setup() {
        super.setup();
        this.popover = usePopover(ResourceCalendarAttendancePopover, {
            position: "right",
            onClose: () => {
                this.fc.api.unselect();
            },
        });
        this.resourceCalendarAttendancePopoverService = useService(
            "resourceCalendarAttendancePopoverService"
        );
        this.resourceCalendarAttendancePopoverService.setup(
            this.props.model.meta,
            ResourceCalendarAttendancePopover.additionalFieldsToFetch
        );
    }

    get interactiveOptions() {
        return {
            ...super.interactiveOptions,
            selectable: this.props.model.canCreate,
            forceEventDuration: true,
        };
    }

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

    onEventResizeStart(info) {
        this.popover.close();
        super.onEventResizeStart(...arguments);
    }

    onEventDrop(info) {
        if (info.oldEvent.allDay) {
            info.view.calendar.setOption("defaultTimedEventDuration", "01:00");
        }
        super.onEventDrop(...arguments);
    }

    async onSelect(info) {
        info.jsEvent?.preventDefault();
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

    handleDateClick(info) {
        super.handleDateClick(info);
        if (this.props.model.hasMultiCreate) {
            this.onDateClick(info);
        }
    }

    onDateClick(info) {
        const date = luxon.DateTime.fromJSDate(info.date);
        info?.view?.calendar.select(date.toISO(), date.plus({ hours: 1 }).toISO());
    }

    convertRecordToEvent(record) {
        const res = super.convertRecordToEvent(...arguments);
        res.forcedDuration = record.duration;
        return res;
    }

    /**
     * @override
     */
    getPopoverProps(record) {
        record = record?.rawRecord;
        return {
            onReload: async () => await this.props.model.load(),
            originalRecord: record,
            recordProps: this.resourceCalendarAttendancePopoverService.recordProps,
            archInfo: this.resourceCalendarAttendancePopoverService.archInfo,
            context: this.props.model.meta.context,
        };
    }
}
