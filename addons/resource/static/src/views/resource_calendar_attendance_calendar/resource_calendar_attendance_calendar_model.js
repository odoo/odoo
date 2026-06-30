import { plugin, providePlugins, useScope } from "@odoo/owl";
import { CalendarModel } from "@web/views/calendar/calendar_model";
import { deserializeDate, serializeDate } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { ResourceCalendarPlugin } from "@resource/plugins/resource_calendar_plugin";

export class ResourceCalendarAttendanceCalendarModel extends CalendarModel {
    /**
     * @override
     */
    setup() {
        super.setup(...arguments);
        if (!useScope().pluginManager.getPluginById(ResourceCalendarPlugin.id)) {
            providePlugins([ResourceCalendarPlugin]);
        }
        this.resourceCalendarPlugin = plugin(ResourceCalendarPlugin);
    }

    _combineDate(date, floatTime) {
        const hours = Math.floor(floatTime);
        const minutes = Math.round((floatTime - hours) * 60);
        return date.set({
            hour: hours,
            minute: minutes,
        });
    }

    /**
     * @override
     */
    async fetchRecords(data) {
        await this.resourceCalendarPlugin.reload();
        const { context, fieldNames, domain } = this.meta;
        return this.orm.call(
            "resource.calendar",
            "get_attendances",
            [
                [this.meta.context.default_calendar_id],
                serializeDate(data.range.start),
                serializeDate(data.range.end),
                fieldNames,
                domain,
            ],
            { context }
        );
    }

    /**
     * @override
     */
    get hasMultiCreate() {
        return (
            !!this.meta.multiCreateView &&
            !this.env.isSmall &&
            ["week", "month"].includes(this.meta.scale)
        );
    }

    /**
     * @override
     */
    async updateRecord(record, options = {}) {
        try {
            this.resourceCalendarPlugin.newAttendances.set(true);
            return super.updateRecord(...arguments);
        } catch (error) {
            this.notification.add(_t(error.data?.message ?? error), { type: "danger" });
            await this.load();
        }
    }

    /**
     * @override
     */
    normalizeRecord(rawRecord) {
        // To adapt datetime with the date + hours or date + duration behavior.
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

    /**
     * @override
     */
    buildRawRecord(partialRecord, options = {}) {
        const data = super.buildRawRecord(...arguments);
        const start = partialRecord.start;
        const end = partialRecord.end;
        data[this.meta.fieldMapping.date_start] = serializeDate(start);
        if ((!partialRecord.isAllDay || !this.hasAllDaySlot) && end) {
            data["duration_based"] = false;
            data["hour_from"] = start.hour + start.minute / 60;
            data["hour_to"] = end.hour + end.minute / 60;
        } else {
            data["duration_based"] = true;
            data["duration_hours"] = (end - start) / 36e5;
            data["hour_from"] = 0;
            data["hour_to"] = 0;
        }
        delete data.name;
        return data;
    }

    async createRecord(record) {
        this.resourceCalendarPlugin.newAttendances.set(true);
        return super.createRecord(...arguments);
    }

    /**
     * @override
     */
    async multiCreateRecords(multiCreateData, dates) {
        // To let the recurrency_until be precomputed by the backend
        // In the case of forever/times end type.
        const record = multiCreateData.record;
        const originalGetChanges = record.getChanges.bind(record);
        record.getChanges = async () => {
            const values = await originalGetChanges();
            if (values.recurrency_end_type !== "date") {
                delete values.recurrency_until;
            }
            delete values[this.meta.fieldMapping.date_start];
            return values;
        };
        try {
            this.resourceCalendarPlugin.newAttendances.set(true);
            return super.multiCreateRecords(...arguments);
        } finally {
            record.getChanges = originalGetChanges;
        }
    }

    async unlinkRecord(recordId) {
        this.resourceCalendarPlugin.newAttendances.set(true);
        return super.createRecord(...arguments);
    }

    async unlinkRecords(recordIds) {
        this.resourceCalendarPlugin.newAttendances.set(true);
        return super.createRecord(...arguments);
    }

    async multiExcludeDates(ids, dates) {
        if (ids) {
            await this.orm.call(this.meta.resModel, "exclude_multiple_occurences", [
                [...new Set(ids)],
                dates.map((d) => serializeDate(d)),
            ]);
            this.resourceCalendarPlugin.newAttendances.set(true);
            await this.load();
        }
    }
}
