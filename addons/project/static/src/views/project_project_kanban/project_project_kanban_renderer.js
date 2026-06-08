import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { ProjectProjectKanbanHeader, ProjectProjectKanbanGroupStageHeader } from "./project_project_kanban_header";


export class ProjectProjectKanbanRenderer extends KanbanRenderer {
    static components = {
        ...KanbanRenderer.components,
        KanbanHeader: ProjectProjectKanbanHeader,
    };
}

export class ProjectProjectKanbanGroupStageRenderer extends KanbanRenderer {
    static components = {
        ...KanbanRenderer.components,
        KanbanHeader: ProjectProjectKanbanGroupStageHeader,
    };
}
