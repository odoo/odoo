/** @odoo-module */

import { ListController } from "@web/views/list/list_controller";
import { DeleteSubtasksConfirmationDialog } from "@project/components/delete_subtasks_confirmation_dialog/delete_subtasks_confirmation_dialog";

export class ProjectTaskListController extends ListController {
    async onDeleteSelectedRecords() {
        if (!Math.max(...this.model.root.selection.map((record) => record.data.subtask_count ))) {
            return super.onDeleteSelectedRecords();
        }
        this.dialogService.add(DeleteSubtasksConfirmationDialog, {
            confirm: async () => {
                await this.model.root.deleteRecords();
                // A re-load is needed to remove deleted sub-tasks from the view
                await this.model.load();
            },
        });
    }
}
