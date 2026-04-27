import { taskGanttView } from "@project_enterprise/views/task_gantt/task_gantt_view";
import { registry } from "@web/core/registry";

import { FsmTaskGanttController } from "./fsm_task_gantt_controller";
import { FsmTaskGanttRenderer } from "./fsm_task_gantt_renderer";

export const fsmTaskGantt = {
    ...taskGanttView,
    Controller: FsmTaskGanttController,
    Renderer: FsmTaskGanttRenderer,
};

registry.category("views").add("fsm_task_gantt", fsmTaskGantt);
