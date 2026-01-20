import { CalendarModel } from "@web/views/calendar/calendar_model";
import { deserializeDate, serializeDate } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";

export class ResourceCalendarAttendanceCalendarModel extends CalendarModel {
    _combineDate(date, floatTime) {
        const hours = Math.floor(floatTime);
        const minutes = Math.round((floatTime - hours) * 60);
        return date.set({
            hour: hours,
            minute: minutes,
        });
    }

    get hasMultiCreate() {
        return (
            !!this.meta.multiCreateView &&
            !this.env.isSmall &&
            ["week", "month"].includes(this.meta.scale)
        );
    }

    async updateRecord(record, options = {}) {
        try {
            await super.updateRecord(...arguments);
        } catch (error) {
            this.notification.add(_t(error.data.message), { type: "danger" });
            await this.load();
        }
    }

    /**
     * @override
     */
    normalizeRecord(rawRecord) {
        const res = super.normalizeRecord(rawRecord);
        const { fieldMapping } = this.meta;

        const isAllDay = (fieldMapping.all_day && rawRecord[fieldMapping.all_day]) || false;

        const start = this._combineDate(
            deserializeDate(rawRecord[fieldMapping.date_start]),
            rawRecord.hour_from
        );
        let end = deserializeDate(rawRecord[fieldMapping.date_start]);
        if (rawRecord.hour_to === 0) {
            end = this._combineDate(end, rawRecord.duration_hours);
        } else {
            end = this._combineDate(end, rawRecord.hour_to);
        }
        const duration = end.diff(start, "hours").hours;

        return {
            ...res,
            isAllDay,
            start,
            startType: "datetime",
            end,
            endType: "datetime",
            duration,
            showTime: true,
        };
    }

    buildRawRecord(partialRecord, options = {}) {
        const data = super.buildRawRecord(...arguments);
        const start = partialRecord.start;
        const end = partialRecord.end;
        data[this.meta.fieldMapping.date_start] = serializeDate(start);
        if ((!partialRecord.isAllDay || !this.hasAllDaySlot) && end) {
            data["duration_based"] = false;
            data["hour_from"] = start?.hour + start?.minute / 60;
            data["hour_to"] = end?.hour + end?.minute / 60;
        } else {
            data["duration_based"] = true;
            data["hour_from"] = 0;
            data["hour_to"] = 0;
        }
        return data;
    }
}
