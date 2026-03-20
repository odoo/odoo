import { RottingKanbanHeader } from "@mail/js/rotting_mixin/rotting_kanban_header";
import { ProjectTaskGroupConfigMenu } from "./project_task_group_config_menu";

export class ProjectTaskKanbanHeader extends RottingKanbanHeader {
    static components = {
        ...RottingKanbanHeader.components,
        GroupConfigMenu: ProjectTaskGroupConfigMenu,
    };
}
