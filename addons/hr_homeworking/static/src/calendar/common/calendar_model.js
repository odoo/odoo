/** @odoo-module **/

import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { serializeDateTime, deserializeDate } from "@web/core/l10n/dates";
import { patch } from "@web/core/utils/patch";

patch(AttendeeCalendarModel.prototype, {
    fetchEventLocation(data) {
        let attendeeIds;
        const filters = data.filterSections.partner_ids.filters;
        if (filters[filters.length - 1].type === "all" && filters[filters.length - 1].active) {
            attendeeIds = Object.keys(this.partnerColorMap);
        } else {
            attendeeIds = data.filterSections.partner_ids.filters
                .filter(filter => filter.type !== "all" && filter.value && filter.active)
                .map(filter => filter.value)
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
        this.multiCalendar = Object.keys(res).length > 1;
        const merged = this.multiCalendar ? {} : [];
        let previousIcon;
        let previousTitle;
        let previous = 0;
        for (const key in res) {
            const rawRecords = res[key];
            for (const rawRecord of rawRecords) {
                const normalizedRecord = this.normalizeLocalisationRecord(rawRecord)
                if (this.multiCalendar) {
                    const startDate = normalizedRecord.start.toJSDate()
                    if (!merged[startDate]) {
                        merged[startDate] = {}
                    }
                    if (!merged[startDate][normalizedRecord.icon]) {
                        merged[startDate][normalizedRecord.icon] = []    
                    }
                    merged[startDate][normalizedRecord.icon].push(normalizedRecord);
                } else {
                    if (rawRecord.icon === previousIcon && rawRecord.title === previousTitle && normalizedRecord.start.diff(merged[previous].end, "days").days == 1) {
                        merged[previous].end = merged[previous].end.plus({days: 1});
                        normalizedRecord.display = false;
                    } else {
                        previousIcon = rawRecord.icon;
                        previousTitle = rawRecord.title;
                        previous = merged.length;
                    }
                    merged.push(normalizedRecord);
                }
            }
        }
        return this.multiCalendar ? merged : Object.assign({}, ...merged.map((x) => ({[x.id]: x})));
    },

    normalizeLocalisationRecord(rawRecord) {
        return {
            id : rawRecord['id'],
            title : rawRecord['title'],
            isAllDay: true,
            start : deserializeDate(rawRecord['date']),
            end : deserializeDate(rawRecord['date']),
            duration : 1,
            isHatched: false,
            isStriked: false,
            display: true,
            multiCalendar: this.multiCalendar,
            icon: rawRecord.icon,
            userId: rawRecord.userId,
            partner_id: rawRecord.partner_id[0],
            colorIndex: this.partnerColorMap[rawRecord.partner_id],
            rawRecord,
        };
    },

    get worklocations() {
        return this.data.worklocations;
    },
    mapPartnersToColor(data) {
        return data.filterSections.partner_ids.filters
            .filter(filter => filter.type !== "all" && filter.value)
            .reduce((map, partner) => ({ ...map, [partner.value]: partner.colorIndex}), {})
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
