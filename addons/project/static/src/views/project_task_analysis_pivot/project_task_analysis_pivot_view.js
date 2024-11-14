import { registry } from "@web/core/registry";
import { projectPivotView } from "../project_task_pivot/project_pivot_view";
import { ProjectTaskAnalysisPivotRenderer } from "./project_task_analysis_pivot_renderer";

registry.category("views").add("project_task_analysis_pivot", {
    ...projectPivotView,
    Renderer: ProjectTaskAnalysisPivotRenderer,
});
