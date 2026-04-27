import { ganttView } from "@web_gantt/gantt_view";
import { TaskGanttController } from "./task_gantt_controller";
import { registry } from "@web/core/registry";
import { TaskGanttArchParser } from "./task_gantt_arch_parser";
import { TaskGanttModel } from "./task_gantt_model";
import { TaskGanttRenderer } from "./task_gantt_renderer";
import { ProjectTaskSearchModel } from "../project_task_search_model";

const viewRegistry = registry.category("views");

export const taskGanttView = {
    ...ganttView,
    Controller: TaskGanttController,
    ArchParser: TaskGanttArchParser,
    Model: TaskGanttModel,
    Renderer: TaskGanttRenderer,
    SearchModel: ProjectTaskSearchModel,
};

viewRegistry.add("task_gantt", taskGanttView);
