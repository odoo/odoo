import { KanbanController } from "@web/views/kanban/kanban_controller";

import { ProjectTaskTemplateDropdown } from "../components/project_task_template_dropdown";

export class ProjectTaskKanbanController extends KanbanController {
    static template = "project.ProjectTaskKanbanView";
    static components = {
        ...KanbanController.components,
        ProjectTaskTemplateDropdown,
    };

    setup() {
        super.setup();
        this.hideKanbanStagesNocontent = this.props.context.hide_kanban_stages_nocontent;
    }
}
