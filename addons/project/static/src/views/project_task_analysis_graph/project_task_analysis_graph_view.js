import { registry } from "@web/core/registry";
import { projectTaskGraphView } from "../project_task_graph/project_task_graph_view";
import { ProjectTaskAnalysisGraphRenderer } from "./project_task_analysis_graph_renderer";

registry.category("views").add("project_task_analysis_graph", {
    ...projectTaskGraphView,
    Renderer: ProjectTaskAnalysisGraphRenderer,
});
