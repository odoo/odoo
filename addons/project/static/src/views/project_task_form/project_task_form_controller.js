/** @odoo-module */

import { useService } from '@web/core/utils/hooks';
import { FormController } from '@web/views/form/form_controller';

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

    deleteRecord() {
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
}
