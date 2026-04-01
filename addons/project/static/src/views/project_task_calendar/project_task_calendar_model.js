import { Domain } from "@web/core/domain";
import { serializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { CalendarModel } from '@web/views/calendar/calendar_model';
import { ProjectTaskModelMixin } from "../project_task_model_mixin";

export class ProjectTaskCalendarModel extends ProjectTaskModelMixin(CalendarModel) {
    get tasksToPlanDomain() {
        const projectId = this.meta.context.default_project_id;
        const domain = [['date_deadline', '=', false]];
        if (projectId) {
            domain.push(['project_id', '=', projectId]);
        }
        return domain;
    }

    /**
     * @override
     */
    get defaultFilterLabel() {
        this.isCheckProject = 'project_id' in this.meta.filtersInfo;
        if (this.isCheckProject) {
            return _t("Private");
        }
        return super.defaultFilterLabel;
    }

    get tasksToPlanSpecification() {
        return {
            name: {},
        };
    }

    async load(params = {}) {
        const domain = params.domain || this.meta.domain;
        params.domain = this._processSearchDomain(domain);
        return super.load({
            planTask: false,
            ...(params || {}),
        });
    }

    async loadRecords(data) {
        const [records] = await Promise.all([
            super.loadRecords(data),
            this.fetchTasksToPlan({ data }),
        ]);
        return records;
    }

    async fetchTasksToPlan(params) {
        if (this.meta.showTasksToPlan && !this.meta.planTask) {
            this.tasksToPlan = await this._fetchTasksToPlan(params);
        }
    }

    async loadMoreTasksToPlan() {
        const { records, length } = this.tasksToPlan;
        const offset = records.length;
        let limit = offset + 20;
        if (limit > length) {
            limit = length;
        }
        const { records: newRecords } = await this._fetchTasksToPlan({ limit, offset });
        this.tasksToPlan.records.push(...newRecords);
        this.notify();
    }

    async _fetchTasksToPlan({ data, limit, offset }) {
        const projectId = this.meta.context.default_project_id;
        if (!projectId) {
            return [];
        }
        const { date_start, date_stop } = this.meta.fieldMapping;
        const fieldsToRemove = [...new Set([date_start, date_stop, 'planned_date_begin', 'date_deadline'])]
        let domain = Domain.removeDomainLeaves(
            Domain.and([
                this.meta.domain,
                this.computeFiltersDomain(data || this.data),
            ]),
            fieldsToRemove
        );
        domain = Domain.and([
            domain,
            this.tasksToPlanDomain,
        ]);
        return await this.orm.webSearchRead(this.resModel, domain.toList(this.meta.context), {
            specification: this.tasksToPlanSpecification,
            limit: limit || 20,
            offset: offset || 0,
        });
    }

    _getPlanTaskVals(taskToPlan, date, timeSlotSelected = false) {
        const [, end] = this.getAllDayDates(date, date);
        return { date_deadline: serializeDateTime(end) };
    }

    _getPlanTaskContext(taskToPlan, timeSlotSelected) {
        return {
            ...this.meta.context,
            task_calendar_plan_full_day: ["day", "week"].includes(this.meta.scale) && !timeSlotSelected,
        };
    }

    async planTask(taskId, date, timeSlotSelected = false) {
        this.tasksToPlan.length -= 1;
        const taskToPlanIndex = this.tasksToPlan.records.findIndex((task) => task.id === taskId);
        if (taskToPlanIndex < 0) {
            return;
        }
        const [taskToPlan] = this.tasksToPlan.records.splice(taskToPlanIndex, 1);
        const context = this._getPlanTaskContext(taskToPlan, timeSlotSelected);
        await this.orm.call(this.meta.resModel, "plan_task_in_calendar", [[taskId], this._getPlanTaskVals(taskToPlan, date, timeSlotSelected)], {
            context,
        });
        await this.load({ planTask: true });
    }
}
