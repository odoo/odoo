import { GanttRendererControls } from "@web_gantt/gantt_renderer_controls";

export class PlanningGanttRendererControls extends GanttRendererControls {
    static props = [...GanttRendererControls.props, "duplicateToolHelperReactive"];
    static toolbarContentTemplate = "planning.PlanningGanttRendererControls.ToolbarContent";
}
