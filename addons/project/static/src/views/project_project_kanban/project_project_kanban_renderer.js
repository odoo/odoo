import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { ProjectProjectKanbanHeader, ProjectProjectKanbanGroupStageHeader } from "./project_project_kanban_header";
import { ProjectProjectKanbanRecord, ProjectProjectKanbanGroupStageRecord } from "./project_project_kanban_record";


export class ProjectProjectKanbanRenderer extends KanbanRenderer {
    static components = {
        ...KanbanRenderer.components,
        KanbanHeader: ProjectProjectKanbanHeader,
        KanbanRecord: ProjectProjectKanbanRecord,
    };
}

export class ProjectProjectKanbanGroupStageRenderer extends KanbanRenderer {
    static components = {
        ...KanbanRenderer.components,
        KanbanHeader: ProjectProjectKanbanGroupStageHeader,
        KanbanRecord: ProjectProjectKanbanGroupStageRecord,
    };
}
