import { deserializeDate } from "@web/core/l10n/dates";
import { ProjectTaskCalendarModel } from "@project/views/project_task_calendar/project_task_calendar_model";
import { useProjectModelActions } from "../project_highlight_tasks";
export class ProjectEnterpriseTaskCalendarModel extends ProjectTaskCalendarModel {
    setup() {
        super.setup(...arguments);
        this.getHighlightIds = useProjectModelActions({
            getContext: () => this.env.searchModel._context,
            getHighlightPlannedIds: () => this.env.searchModel.highlightPlannedIds,
        }).getHighlightIds;
    }

    /**
     * @override
     */
    async loadRecords(data) {
        this.highlightIds = await this.getHighlightIds();
        return await super.loadRecords(data);
    }

    makeContextDefaults(record) {
        const { default_planned_date_start, ...context } = super.makeContextDefaults(record);
        if (
            ["day", "week"].includes(this.meta.scale) ||
            !deserializeDate(default_planned_date_start).hasSame(
                deserializeDate(context["default_date_deadline"]),
                "day"
            )
        ) {
            context.default_planned_date_begin = default_planned_date_start;
        }

        return { ...context, scale: this.meta.scale };
    }
}
