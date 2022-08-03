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
        const hasAnyRecurrences = this._anyRecurrentTaskSelected();

        if (hasAnyRecurrences) {
            menuItems.archive.callback = () =>
                this.taskRecurrence.addressRecurrence(this.model.root.selection, "archive", () =>
                    this.toggleArchiveState(true)
                );
        }
        return menuItems;
    }

    onDeleteSelectedRecords() {
        return this.taskRecurrence.addressRecurrence(
            this.model.root.selection,
            'delete',
            () => this.model.root.deleteRecords(),
        );
    }

    _anyRecurrentTaskSelected() {
        return this.model.root.selection.some(task => task.data.recurrence_id);
    }
}
