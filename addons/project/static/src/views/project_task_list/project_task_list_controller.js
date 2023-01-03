/** @odoo-module */

import { useService } from '@web/core/utils/hooks';
import { ListController } from '@web/views/list/list_controller';

export class ProjectTaskListController extends ListController {
    setup() {
        super.setup();
        this.taskRecurrence = useService('project_task_recurrence');
    }

    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems();
        const hasAnyRecurrences = this._anySelectedTasksWithRecurrence();

        if (hasAnyRecurrences) {
            menuItems.archive.callback = () =>
                this.taskRecurrence.stopRecurrence(this.model.root.selection, () =>
                    this.toggleArchiveState(true)
                );
        }
        return menuItems;
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
