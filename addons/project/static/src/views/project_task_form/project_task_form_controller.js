/** @odoo-module */

import { useService } from '@web/core/utils/hooks';
import { FormController } from '@web/views/form/form_controller';
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ProjectDeleteSubtasksConfirmationDialog } from "../../components/project_delete_subtasks_confirmation_dialog/project_delete_subtasks_confirmation_dialog";


export class ProjectTaskFormController extends FormController {
    setup() {
        super.setup();
        this.taskRecurrence = useService('project_task_recurrence');
    }

    getActionMenuItems() {
        if (!(this.archiveEnabled && this.model.root.isActive) || !this.model.root.data.recurrence_id) {
            return super.getActionMenuItems();
        }
        this.archiveEnabled = false;
        const actionMenuItems = super.getActionMenuItems();
        this.archiveEnabled = true;
        if (actionMenuItems) {
            actionMenuItems.other.unshift({
                description: this.env._t('Archive'),
                callback: () => this.taskRecurrence.stopRecurrence(
                    [this.model.root],
                    () => this.model.root.archive(),
                ),
            });
        }
        return actionMenuItems;
    }

    proceedDeleteRecord() {
        if (!this.model.root.data.recurrence_id) {
            return super.deleteRecord();
        }
        this.taskRecurrence.stopRecurrence(
            [this.model.root],
            () => {
                this.model.root.delete();
                if (!this.model.root.resId) {
                    this.env.config.historyBack();
                }
            }
        );
    }

    deleteRecord() {
        if (this.model.root.data.subtask_count > 0) {
            const dialogProps = {
        		body: this.env._t("This task have sub-tasks linked to it. Do you want to delete them as well?"),
            	confirm: () => {
                	this.model.root.delete();
                	if (!this.model.root.resId) {
                    	this.env.config.historyBack();
                	}
            	},
                confirmWithSubtasks: () => {
                    /*alert(this.model.root.data.child_ids.length);*/
                    console.log(JSON.stringify(this.model.root.data, null, 4));
                    for (let i = 0; i < this.model.root.data.subtask_count; i++) {
                        alert(typeof this.model.root.data.child_ids[i]);
                    }
                },
          		cancel: () => {},
            	};
        	this.dialogService.add(ProjectDeleteSubtasksConfirmationDialog, dialogProps);
        } else {
            return this.proceedDeleteRecord();
        }
    }
}
