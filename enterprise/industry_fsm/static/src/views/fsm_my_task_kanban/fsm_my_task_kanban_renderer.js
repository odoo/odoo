import { ProjectTaskKanbanRenderer } from "@project/views/project_task_kanban/project_task_kanban_renderer";

import { FsmMyTaskKanbanRecord } from "./fsm_my_task_kanban_record";

export class FsmMyTaskKanbanRenderer extends ProjectTaskKanbanRenderer {
    static components = {
        ...ProjectTaskKanbanRenderer.components,
        KanbanRecord: FsmMyTaskKanbanRecord,
    };
}
