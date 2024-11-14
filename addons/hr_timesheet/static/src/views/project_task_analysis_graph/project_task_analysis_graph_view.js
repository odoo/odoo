import { registry } from "@web/core/registry";
import { hrTimesheetGraphView } from "../timesheet_graph/timesheet_graph_view";
import { ProjectTaskAnalysisGraphRenderer } from "@project/views/project_task_analysis_graph/project_task_analysis_graph_renderer";

registry.category("views").add("hr_timesheet_project_task_analysis_graph", {
    ...hrTimesheetGraphView,
    Renderer: ProjectTaskAnalysisGraphRenderer,
});
