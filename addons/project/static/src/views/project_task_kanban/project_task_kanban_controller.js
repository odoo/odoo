import { onWillStart } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { KanbanController } from "@web/views/kanban/kanban_controller";

export class ProjectTaskKanbanController extends KanbanController {
    static template = "project.ProjectTaskKanbanView";

    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.taskTemplateService = useService("project_task_template");
        onWillStart(this.onWillStart);
        this.taskTemplates = [];
    }

    async onWillStart() {
        const context = this.props.context;
        if (context.default_project_id) {
            this.taskTemplates = await this.orm.call("project.project", "get_template_tasks", [
                context.default_project_id,
            ]);
        }
    }

    async createTaskFromTemplate(templateId) {
        this.taskTemplateService.templateId = templateId;
        await this.createRecord();
    }
}
