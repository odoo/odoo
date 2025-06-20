import { KanbanHeader } from "@web/views/kanban/kanban_header";
import { ProjectTaskGroupConfigMenu } from "./project_task_group_config_menu";

export class ProjectTaskKanbanHeader extends KanbanHeader {
    static components = {
        ...KanbanHeader.components,
        GroupConfigMenu: ProjectTaskGroupConfigMenu,
    };
}
