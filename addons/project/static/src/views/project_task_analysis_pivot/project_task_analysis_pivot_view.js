import { registry } from "@web/core/registry";
import { pivotView } from "@web/views/pivot/pivot_view";
import { ProjectTaskAnalysisPivotRenderer } from "./project_task_analysis_pivot_renderer";
import { ProjectTaskControlPanel } from "../project_task_control_panel/project_task_control_panel";
import { ProjectTaskAnalysisPivotModel } from "./project_task_analysis_pivot_model";

registry.category("views").add("project_task_analysis_pivot", {
    ...pivotView,
    ControlPanel: ProjectTaskControlPanel,
    Model: ProjectTaskAnalysisPivotModel,
    Renderer: ProjectTaskAnalysisPivotRenderer,
});
