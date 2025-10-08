import { CalendarModel } from "@web/views/calendar/calendar_model";
import {
    deserializeDate,
    deserializeDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
import { Cache } from "@web/core/utils/cache";
import { parseFloatTime } from "@web/views/fields/parsers";
const { DateTime } = luxon;

export class TimeOffCalendarModel extends CalendarModel {
    setup(params, services) {
        super.setup(params, services);

        this.data.mandatoryDays = {};
        if (this.env.isSmall) {
            this.meta.scale = "month";
        }

        this._mandatoryDaysCache = new Cache(
            (data) => this.fetchMandatoryDays(data),
            (data) => `${serializeDateTime(data.range.start)},${serializeDateTime(data.range.end)}`
        );
    }

    /**
     * @override
     */
    get canEdit() {
        return this.meta.canEdit;
    }

    /**
     * @override
     */
    async updateRecord(record, options = {}) {
        const leaveRecord = this.data.records[record.id]?.rawRecord;
        const rawRecord = this.buildRawRecord(record, options);

        try {
            const [employee] = await this.orm.searchRead(
                "hr.employee",
                [["id", "=", leaveRecord.employee_id[0]]],
                ["tz"]
            );
            const tz = employee?.tz || this.env.user.tz || "UTC";
            const dateFrom = deserializeDateTime(rawRecord.date_from, { tz });
            const dateTo = deserializeDateTime(rawRecord.date_to, { tz });

            if(leaveRecord?.request_unit_hours){
                await this.orm.write(this.meta.resModel, [record.id], {
                    request_date_from: dateFrom.toISODate(),
                    request_date_to: dateTo.toISODate(),
                    request_hour_from: parseFloatTime(dateFrom.toFormat("HH:mm")),
                    request_hour_to: parseFloatTime(dateTo.toFormat("HH:mm")),
                }, { context: this.meta.context });
            }
            else {
                await this.orm.write(this.meta.resModel, [record.id], {
                    request_date_from: dateFrom.toISODate(),
                    request_date_to: dateTo.toISODate(),
                }, { context: this.meta.context } );
            }
        } finally {
            await this.load();
        }
    }

    /**
     * @override
     */
    normalizeRecord(rawRecord) {
        const result = super.normalizeRecord(...arguments);
        if (rawRecord.employee_id) {
            const employee = rawRecord.employee_id[1];
            // If the employee's name isn't already included at the start of the title
            if (!result.title.startsWith(employee)) {
                result.title = [employee, result.title].join(" ");
            }
        }
        if (rawRecord.date_from && rawRecord.date_to) {
            const dateFrom = DateTime.fromSQL(rawRecord.date_from);
            const dateTo = DateTime.fromSQL(rawRecord.date_to);
            result.sameDay = dateFrom.hasSame(dateTo, 'day');
        }
        if (rawRecord.request_unit_half) {
            result.requestDateFromPeriod = rawRecord.request_date_from_period;
            result.requestDateToPeriod = rawRecord.request_date_to_period;
        }
        return result;
    }

    makeContextDefaults(record) {
        const context = super.makeContextDefaults(record);
        let default_employee_id = this.employeeId;
        if(context['active_model'] === 'hr.employee') {
            default_employee_id = context.active_id
        }
        if (default_employee_id) {
            context["default_employee_id"] = default_employee_id
        }
        function deserialize(str) {
            // "YYYY-MM-DD".length == 10
            return str.length > 10 ? deserializeDateTime(str) : deserializeDate(str);
        }
        if (["week", "day"].includes(this.scale)) {
            context["default_request_unit_hours"] = true;
            const hour_from = deserialize(context['default_date_from']??this.date);
            const hour_to = deserialize(context['default_date_to']??this.date);
            context['default_request_hour_from'] = hour_from.hour + hour_from.minute / 60;
            context['default_request_hour_to'] = hour_to.hour + hour_to.minute / 60;
        }

        if ("default_date_from" in context) {
            context["default_date_from"] = serializeDateTime(
                deserialize(context["default_date_from"]).set({ hours: 7 })
            );
        }
        if ("default_date_to" in context) {
            context["default_date_to"] = serializeDateTime(
                deserialize(context["default_date_to"]).set({ hours: 19 })
            );
        }
        return context;
    }

    async updateData(data) {
        const prom = super.updateData(data);
        data.mandatoryDays = await this._mandatoryDaysCache.read(data);
        return prom;
    }

    /**
     * @override
     */
    fetchUnusualDays(data) {
        return this.orm.call(
            this.meta.resModel,
            "get_unusual_days",
            [serializeDateTime(data.range.start), serializeDateTime(data.range.end)],
            {
                context: {
                    employee_id: this.employeeId,
                },
            }
        );
    }

    async fetchMandatoryDays(data) {
        return this.orm.call("hr.employee", "get_mandatory_days", [
            this.employeeId,
            serializeDate(data.range.start, "datetime"),
            serializeDate(data.range.end, "datetime"),
        ]);
    }

    get mandatoryDays() {
        return this.data.mandatoryDays;
    }

    get employeeId() {
        return (
            (this.meta.context.employee_id && this.meta.context.employee_id[0]) ||
            (this.meta.context.active_model === "hr.employee" && this.meta.context.active_id) ||
            null
        );
    }

    fetchRecords(data) {
        const { fieldNames, resModel } = this.meta;
        const context = {};
        if (!this.employeeId) {
            context["short_name"] = 1;
        }
        const fieldNamesToAdd = resModel === "hr.leave" ? ["request_unit_half", "request_date_from_period", "request_date_to_period", "request_unit_hours", "employee_id"] : [];
        return this.orm.searchRead(resModel, this.computeDomain(data), [...fieldNames, ...fieldNamesToAdd], { context });
    }

    computeDomain(data) {
        return [...super.computeDomain(data), ["state", "!=", "cancel"]];
    }
}
