import { registry } from "@web/core/registry";
import { graphView } from "@web/views/graph/graph_view";
import { ProjectTaskAnalysisGraphRenderer } from "./project_task_analysis_graph_renderer";

registry.category("views").add("project_task_analysis_graph", {
    ...graphView,
    Renderer: ProjectTaskAnalysisGraphRenderer,
});
