import { onWillStart } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";
import { subTaskDeleteConfirmationMessage } from "@project/views/project_task_form/project_task_form_controller";

export class ProjectTaskListController extends ListController {
    static template = "project.ProjectTaskListView";

    setup() {
        super.setup();
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

    get deleteConfirmationDialogProps() {
        const deleteConfirmationDialogProps = super.deleteConfirmationDialogProps;
        const hasSubtasks = this.model.root.selection.some(task => task.data.subtask_count > 0)
        if (!hasSubtasks) {
            return deleteConfirmationDialogProps;
        }
        return {
            ...deleteConfirmationDialogProps,
            confirm: async () => {
                await this.model.root.deleteRecords();
                // A re-load is needed to remove deleted sub-tasks from the view
                await this.model.load();
            },
            body: subTaskDeleteConfirmationMessage,
        }
    }

    async createTaskFromTemplate(templateId) {
        this.taskTemplateService.templateId = templateId;
        await this.createRecord();
    }
}
