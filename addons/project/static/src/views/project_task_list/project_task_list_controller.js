/** @odoo-module */

import { useService } from '@web/core/utils/hooks';
import { ListController } from '@web/views/list/list_controller';

export class ProjectTaskListController extends ListController {
    setup() {
        super.setup();
        this.taskRecurrence = useService('project_task_recurrence');
    }

    getActionMenuItems() {
        if (!this.archiveEnabled || this.model.root.isM2MGrouped) {
            return super.getActionMenuItems();
        }
        const hasAnyRecurrences = this._anySelectedTasksWithRecurrence();
        this.archiveEnabled = !hasAnyRecurrences;
        const actionMenuItems = super.getActionMenuItems();
        this.archiveEnabled = true;
        if (actionMenuItems && hasAnyRecurrences) {
            actionMenuItems.other.splice(
                this.isExportEnable ? 1 : 0,
                0,
                {
                    description: this.env._t('Archive'),
                    callback: () => this.taskRecurrence.stopRecurrence(
                        this.model.root.selection,
                        () => this.toggleArchiveState(true),
                    ),
                },
                {
                    description: this.env._t('Unarchive'),
                    callback: () => this.toggleArchiveState(false),
                },
            );
        }
        return actionMenuItems;
    }

    onDeleteSelectedRecords() {
        if (this._anySelectedTasksWithRecurrence()) {
            return this.taskRecurrence.stopRecurrence(
                this.model.root.selection,
                () => this.model.root.deleteRecords(),
            );
        }
        return super.onDeleteSelectedRecords();
    }

    _anySelectedTasksWithRecurrence() {
        for (const selectedTask of this.model.root.selection) {
            if (selectedTask.data.recurrence_id) {
                return true;
            }
        }
        return false;
    }
}
