import { ProjectTaskTemplateDropdown } from "../components/project_task_template_dropdown";
import { RottingKanbanController } from "@mail/js/rotting_mixin/rotting_kanban_controller";


export class ProjectTaskKanbanController extends RottingKanbanController {
    static template = "project.ProjectTaskKanbanView";
    static components = {
        ...RottingKanbanController.components,
        ProjectTaskTemplateDropdown,
    };

    setup() {
        super.setup();
        this.hideKanbanStagesNocontent = this.props.context.hide_kanban_stages_nocontent;
    }
}
