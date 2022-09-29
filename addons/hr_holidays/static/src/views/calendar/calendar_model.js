/** @odoo-module */

import { CalendarModel } from '@web/views/calendar/calendar_model';
import { serializeDate } from "@web/core/l10n/dates";

export class TimeOffCalendarModel extends CalendarModel {
    setup(params, services) {
        super.setup(params, services);

        this.data.stressDays = {};
        if (this.env.isSmall) {
            this.meta.scale = 'month';
        }
    }

    makeContextDefaults(record) {
        const context = super.makeContextDefaults(record);
        if (this.employeeId) {
            context['default_employee_id'] = this.employeeId;
        }
        return context;
    }

    async updateData(data) {
        await super.updateData(data);
        data.stressDays = await this.fetchStressDays(data);
    }

    async fetchStressDays(data) {
        return this.orm.call("hr.employee", "get_stress_days", [
            this.employeeId,
            serializeDate(data.range.start, "datetime"),
            serializeDate(data.range.end, "datetime"),
        ]);
    }

    get stressDays() {
        return this.data.stressDays;
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
