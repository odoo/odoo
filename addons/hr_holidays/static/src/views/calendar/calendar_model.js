/** @odoo-module */

import { CalendarModel } from '@web/views/calendar/calendar_model';
import { deserializeDateTime, serializeDate, serializeDateTime } from "@web/core/l10n/dates";

export class TimeOffCalendarModel extends CalendarModel {
    setup(params, services) {
        super.setup(params, services);

        this.data.mandatoryDays = {};
        if (this.env.isSmall) {
            this.meta.scale = 'month';
        }
    }

    /**
     * @override
     */
    normalizeRecord(rawRecord) {
        let result = super.normalizeRecord(...arguments);
        if (rawRecord.employee_id) {
            const employee = rawRecord.employee_id[1];
            result.title = [employee, result.title].join(' ');
        }
        return result;
    }

    makeContextDefaults(record) {
        const context = super.makeContextDefaults(record);
        if (this.employeeId) {
            context["default_employee_id"] = this.employeeId;
        }

        if ("default_date_from" in context) {
            context["default_date_from"] = serializeDateTime(
                deserializeDateTime(context["default_date_from"]).set({ hours: 7 })
            );
        }
        if ("default_date_to" in context) {
            context["default_date_to"] = serializeDateTime(
                deserializeDateTime(context["default_date_to"]).set({ hours: 19 })
            );
        }
        return context;
    }

    async updateData(data) {
        await super.updateData(data);

        data.mandatoryDays = await this.fetchMandatoryDays(data);
    }

    /**
     * @override
     */
    fetchUnusualDays(data) {
        return this.orm.call(this.meta.resModel, "get_unusual_days", [
            serializeDateTime(data.range.start),
            serializeDateTime(data.range.end),
        ],
        {
            context: {
                'employee_id': this.employeeId,
            }
        });
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
        return this.meta.context.employee_id && this.meta.context.employee_id[0] || null;
    }

    fetchRecords(data) {
        const { fieldNames, resModel } = this.meta;
        const context = {};
        if (!this.employeeId) {
            context['short_name'] = 1;
        }
        return this.orm.searchRead(resModel, this.computeDomain(data), fieldNames, { context });
    }
}
