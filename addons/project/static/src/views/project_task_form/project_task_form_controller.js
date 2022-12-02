/** @odoo-module */

import { useService } from '@web/core/utils/hooks';
import { FormController } from '@web/views/form/form_controller';

export class ProjectTaskFormController extends FormController {
    async setup() {
        this.orm = useService('orm');
        if (this.props.context.subtasks_context) {
            const a = await this.orm.call(
                'project.task',
                'get_pagination_details',
                [this.props.resId, 'subtasks']
            );
            this.props.resIds = a;
        }
        else if (this.props.context.dependencies_context) {
            this.props.resIds = [1, 5, 10, 8, this.props.resId];
        }
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
