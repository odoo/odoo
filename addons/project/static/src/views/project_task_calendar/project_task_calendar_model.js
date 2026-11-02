import { serializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { CalendarModel } from "@web/views/calendar/calendar_model";
import { ProjectTaskModelMixin } from "../project_task_model_mixin";

export class ProjectTaskCalendarModel extends ProjectTaskModelMixin(CalendarModel) {
    /**
     * @override
     */
    get defaultFilterLabel() {
        this.isCheckProject = "project_id" in this.meta.filtersInfo;
        if (this.isCheckProject) {
            return _t("Private");
        }
        return super.defaultFilterLabel;
    }

    async load(params = {}) {
        const domain = params.domain || this.meta.domain;
        params.domain = this._processSearchDomain(domain);
        return super.load(params);
    }

    _getPlanTaskContext(taskToPlan) {
        return {
            ...this.meta.context,
            task_calendar_plan_full_day:
                ["day", "week"].includes(this.meta.scale) && !this.hasTimePrecision,
        };
    }

    async scheduleEvent(taskId, date) {
        const taskToPlanIndex = this.data.eventsToSchedule.records.findIndex(
            (task) => task.id === taskId
        );
        if (taskToPlanIndex < 0) {
            return;
        }
        const taskToPlan = this.data.eventsToSchedule.records[taskToPlanIndex];
        const context = this._getPlanTaskContext(taskToPlan);
        const [start, end] = this.hasTimePrecision
            ? [date, date.plus({ hours: 1 })]
            : this.getAllDayDates(date);
        const { date_start, date_stop } = this.meta.fieldMapping;
        await this.orm.call(
            this.meta.resModel,
            "plan_task_in_calendar",
            [
                [taskId],
                {
                    [date_stop]: serializeDateTime(end),
                    [date_start]: serializeDateTime(start),
                },
            ],
            {
                context,
            }
        );
        await this.load();
    }
}
