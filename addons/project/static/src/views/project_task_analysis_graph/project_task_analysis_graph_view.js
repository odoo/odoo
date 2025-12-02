import { registry } from "@web/core/registry";
import { graphView } from "@web/views/graph/graph_view";
import { ProjectTaskAnalysisGraphRenderer } from "./project_task_analysis_graph_renderer";
import { ProjectTaskAnalysisGraphModel } from "./project_task_analysis_graph_model";
import { ProjectTaskControlPanel } from "../project_task_control_panel/project_task_control_panel";

registry.category("views").add("project_task_analysis_graph", {
    ...graphView,
    ControlPanel: ProjectTaskControlPanel,
    Model: ProjectTaskAnalysisGraphModel,
    Renderer: ProjectTaskAnalysisGraphRenderer,
});
