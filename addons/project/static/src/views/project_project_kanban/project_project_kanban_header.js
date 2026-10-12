import { KanbanHeader } from "@web/views/kanban/kanban_header";
import { RottingKanbanHeader } from "@mail/js/rotting_mixin/rotting_kanban_header";
import { ProjectProjectGroupConfigMenu } from "./project_project_group_config_menu";

export class ProjectProjectKanbanHeader extends KanbanHeader {
    static components = {
        ...KanbanHeader.components,
        GroupConfigMenu: ProjectProjectGroupConfigMenu,
    };
}

export class ProjectProjectKanbanGroupStageHeader extends RottingKanbanHeader {
    static components = {
        ...RottingKanbanHeader.components,
        GroupConfigMenu: ProjectProjectGroupConfigMenu,
    };
}
