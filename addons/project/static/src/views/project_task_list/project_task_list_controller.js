/** @odoo-module */

import { ListController } from "@web/views/list/list_controller";
import { subTaskDeleteConfirmationMessage } from "@project/views/project_task_form/project_task_form_controller";

export class ProjectTaskListController extends ListController {

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
}
