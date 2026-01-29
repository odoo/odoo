/** @odoo-module */

import { FormController } from '@web/views/form/form_controller';
import { DeleteSubtasksConfirmationDialog } from "@project/components/delete_subtasks_confirmation_dialog/delete_subtasks_confirmation_dialog";

export class ProjectTaskFormController extends FormController {
    deleteRecord() {
        if (!this.model.root.data.subtask_count) {
            return super.deleteRecord();
        }
        this.dialogService.add(DeleteSubtasksConfirmationDialog, {
            confirm: async () => {
                await this.model.root.delete();
                if (!this.model.root.resId) {
                    this.env.config.historyBack();
                }
            },
        });
    }
}
