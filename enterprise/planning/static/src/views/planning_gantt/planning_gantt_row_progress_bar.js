import { GanttRowProgressBar } from "@web_gantt/gantt_row_progress_bar";

export class PlanningGanttRowProgressBar extends GanttRowProgressBar {
    static template = "planning.PlanningGanttRowProgressBar";
    static props = {
        ...GanttRowProgressBar.props,
        progressBar: {
            ...GanttRowProgressBar.props.progressBar,
            shape: {
                ...GanttRowProgressBar.props.progressBar.shape,
                is_flexible_hours: { type: Boolean, optional: true },
                is_fully_flexible_hours: { type: Boolean, optional: true },
            },
        },
    };
}
