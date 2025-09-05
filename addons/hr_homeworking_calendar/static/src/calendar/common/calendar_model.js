import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { serializeDateTime } from "@web/core/l10n/dates";
import { user } from "@web/core/user";
import { getColor } from "@web/views/calendar/utils";
import { patch } from "@web/core/utils/patch";

const { Interval } = luxon;

patch(AttendeeCalendarModel.prototype, {
    fetchEventLocation(data) {
        let attendeeIds;
        const filters = data.filterSections.partner_ids?.filters;
        if (filters && filters[filters.length - 1].type === "all" && filters[filters.length - 1].active) {
            attendeeIds = Object.keys(this.partnerColorMap);
        } else {
            attendeeIds = (filters || [])
                .filter(filter => filter.type !== "all" && filter.value && filter.active)
                .map(filter => filter.value)
        }
        if (!attendeeIds.includes(user.partnerId)) {
            attendeeIds.push(user.partnerId);
        }
        return this.orm.call('res.partner', "get_worklocation", [
            attendeeIds,
            serializeDateTime(data.range.start),
            serializeDateTime(data.range.end),
        ]);
    },

    // returns a map of worklocations, display is used to mark the events that are to be shown in the view.
    async loadWorkLocations(data) {
        const res = await this.fetchEventLocation(data)
        this.multiCalendar = Object.values(res).some(location => location.user_id !== user.userId);
        const filters = data.filterSections.partner_ids?.filters;
        data.userFilterActive = filters && (
            filters.filter(filter => filter.value === user.partnerId)[0]?.active ||
            filters[filters.length - 1].type === "all" &&
            filters[filters.length - 1].active
        );
        const events = {};
        let previousDay;
        const rangeInterval = Interval.fromDateTimes(data.range.start.startOf("day"), data.range.end.endOf("day")).splitBy({day: 1});
        for (const day of rangeInterval) {
            const startDay = day.s;
            const dayISO = startDay.toISODate();
            const dayName = startDay.setLocale("en").weekdayLong.toLowerCase();
            for (const employeeId in res) {
                if (this.multiCalendar) {
                    if (!(dayISO in events)) {
                        events[dayISO] = {};
                    }
                    if (res[employeeId].exceptions && dayISO in res[employeeId].exceptions) {
                        // check if exception for that date
                        const { location_type } = res[employeeId].exceptions[dayISO];
                        if (location_type in events[dayISO]) {
                            events[dayISO][location_type].push(this.createHomeworkingRecordAt(res[employeeId], startDay, res[employeeId].exceptions[dayISO]));
                        } else {
                            events[dayISO][location_type] = [this.createHomeworkingRecordAt(res[employeeId], startDay, res[employeeId].exceptions[dayISO])];
                        }
                    }
                    else {
                        const locationKeyName = `${dayName}_location_id`;
                        if (!(locationKeyName in res[employeeId])) {
                            continue;
                        }
                        const {location_type} = res[employeeId][locationKeyName];
                        if (!location_type) {
                            continue;
                        }
                        if (location_type in events[dayISO]) {
                            events[dayISO][location_type].push(this.createHomeworkingRecordAt(res[employeeId], startDay, res[employeeId][locationKeyName]));
                        } else {
                            events[dayISO][location_type] = [this.createHomeworkingRecordAt(res[employeeId], startDay, res[employeeId][locationKeyName])];
                        }
                    }
                } else {
                    const hasException = res[employeeId].exceptions && dayISO in res[employeeId].exceptions;
                    const workLocationData = hasException ? res[employeeId].exceptions[dayISO] : res[employeeId][`${dayName}_location_id`];
                    const currentEvent = this.createHomeworkingRecordAt(res[employeeId], startDay, workLocationData);
                    const previousEvent = events[previousDay];
                    if (previousEvent && previousEvent.icon === currentEvent.icon && previousEvent.title === currentEvent.title) {
                        previousEvent.end = previousEvent.end.plus({days:1});
                        currentEvent.display = false;
                    } else {
                        previousDay = dayISO;
                    }
                    if (currentEvent.title) {
                        events[dayISO] = currentEvent;
                    }
                }
            }
        }
        return events;
    },

    createHomeworkingRecordAt(record, day, workLocationData) {
        const { location_type, location_name, work_location_id, hr_employee_location_id} = workLocationData;
        const ghostRecord = !Boolean(hr_employee_location_id);
        const id = ghostRecord ? `default-location-${record.employee_id}-${day.toMillis()}` : String(hr_employee_location_id);
        return {
            id,
            title: location_name,
            start: day,
            end: day.plus({days:1}),
            display: true,
            multiCalendar: this.multiCalendar,
            homeworking: true,
            employeeId: record.employee_id,
            employeeName: record.employee_name,
            icon: location_type,
            userId: record.user_id,
            partnerId: record.partner_id,
            colorIndex: this.partnerColorMap[record.partner_id],
            resModel: "hr.employee.location",
            work_location_id,
            ghostRecord,
            rawRecord: record,
        };
    },

    get worklocations() {
        return this.data.worklocations;
    },

    mapPartnersToColor(data) {
        return (data.filterSections.partner_ids?.filters || [])
            .filter(filter => filter.type !== "all" && filter.value)
            .reduce((map, partner) => ({ ...map, [partner.value]: getColor(partner.colorIndex)}), {})
    },

    /**
     * @override
     */
    async updateData(data){
        await super.updateData(...arguments)
        this.partnerColorMap = this.mapPartnersToColor(data);
        data.worklocations = await this.loadWorkLocations(data);
    }
})
