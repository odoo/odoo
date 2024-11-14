import { registry } from "@web/core/registry";
import { pivotView } from "@web/views/pivot/pivot_view";
import { ProjectTaskAnalysisPivotRenderer } from "./project_task_analysis_pivot_renderer";

registry.category("views").add("project_task_analysis_pivot", {
    ...pivotView,
    Renderer: ProjectTaskAnalysisPivotRenderer,
});
